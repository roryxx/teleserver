import os
import time
import asyncio
import threading
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError

class TelegramManager:
    def __init__(self):
        self.api_id = 2040
        self.api_hash = 'b18441a1ff607e10a989891a5462e627'
        self.sessions_dir = "sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)
        
        self.clients = {}  # phone_number -> TelegramClient
        self.login_client = None
        self.login_phone = None
        self.is_broadcasting = False
        
        # Start permanent background thread for Telethon operations
        self.loop = asyncio.new_event_loop()
        self.tg_thread = threading.Thread(target=self._start_loop, daemon=True)
        self.tg_thread.start()
        
        self.run_sync(self.load_existing_sessions())

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        
    def run_sync(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()

    async def load_existing_sessions(self):
        for file in os.listdir(self.sessions_dir):
            if file.endswith(".session"):
                phone = file.replace(".session", "")
                session_path = os.path.join(self.sessions_dir, phone)
                client = TelegramClient(session_path, self.api_id, self.api_hash, loop=self.loop)
                try:
                    await client.connect()
                    if await client.is_user_authorized():
                        self.clients[phone] = client
                        print(f"[SESSION] Auto-connected: {phone}")
                    else:
                        print(f"[SESSION] Expired session: {phone}")
                        await client.disconnect()
                except Exception as e:
                    print(f"[SESSION] Failed to connect {phone}: {e}")
                
    def get_session_list(self):
        return list(self.clients.keys())

    async def send_otp(self, phone_number):
        try:
            clean_phone = phone_number.replace("+", "").strip()
            self.login_phone = clean_phone
            
            if clean_phone in self.clients:
                return {"success": False, "message": "Account already logged in."}

            session_path = os.path.join(self.sessions_dir, clean_phone)
            self.login_client = TelegramClient(session_path, self.api_id, self.api_hash, loop=self.loop)
            
            await self.login_client.connect()
            await self.login_client.send_code_request(phone_number)
            
            return {"success": True, "message": "OTP Sent", "phone": clean_phone}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def verify_otp(self, phone_number, otp):
        try:
            await self.login_client.sign_in(phone_number, otp)
            user_info = await self.login_client.get_me()
            self.clients[self.login_phone] = self.login_client
            return {"success": True, "message": "Login Successful!", "user": user_info.first_name, "phone": self.login_phone}
        except SessionPasswordNeededError:
            return {"success": False, "needs_2fa": True, "message": "2FA Required"}
        except (PhoneCodeInvalidError, PhoneCodeExpiredError):
            return {"success": False, "message": "Invalid or expired OTP"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def verify_2fa(self, phone_number, password):
        try:
            await self.login_client.sign_in(password=password)
            user_info = await self.login_client.get_me()
            self.clients[self.login_phone] = self.login_client
            return {"success": True, "message": "Login Successful!", "user": user_info.first_name, "phone": self.login_phone}
        except Exception as e:
             return {"success": False, "message": str(e)}

    async def _delete_session_async(self, phone_number):
        if phone_number in self.clients:
            await self.clients[phone_number].disconnect()
            del self.clients[phone_number]
            
        session_file = os.path.join(self.sessions_dir, f"{phone_number}.session")
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
            except Exception:
                pass

    def delete_session(self, phone_number):
        self.run_sync(self._delete_session_async(phone_number))
        return {"success": True, "message": "Account removed"}

    async def get_dialogs(self, phone_number):
        if phone_number not in self.clients: return []
        client = self.clients[phone_number]
        if not client.is_connected(): await client.connect()
            
        dialogs = []
        try:
            async for dialog in client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    dialogs.append({"id": str(dialog.id), "title": dialog.title, "type": "Group" if dialog.is_group else "Channel"})
        except Exception as e:
            pass
        return dialogs
        

    async def _broadcast_async(self, target_group_ids, message_text, delay_seconds, auto_repeat=False, repeat_interval=300):
        self.is_broadcasting = True
        connected_clients = []
        for phone, client in self.clients.items():
            if not client.is_connected(): await client.connect()
            connected_clients.append({"phone": phone, "client": client})
            
        if not connected_clients:
            print("Error: No connected accounts.")
            self.is_broadcasting = False
            return
            
        client_count = len(connected_clients)
        cycle = 0
        
        while self.is_broadcasting:
            cycle += 1
            if auto_repeat:
                print(f"\n=== CYCLE {cycle} START ===")
            
            client_index = 0
            for group_id in target_group_ids:
                if not self.is_broadcasting:
                    print("Broadcasting stopped by user.")
                    break
                    
                current_worker = connected_clients[client_index]
                client = current_worker["client"]
                phone = current_worker["phone"]
                try:
                    entity = await client.get_entity(int(group_id))
                    await client.send_message(entity, message_text)
                    print(f"[SUCCESS] Sent to {group_id} using {phone}")
                except Exception as e:
                    print(f"[ERROR] Failed to send to {group_id} using {phone} ({str(e)})")
                    
                client_index = (client_index + 1) % client_count
                if self.is_broadcasting:
                    print(f"Waiting {delay_seconds} seconds before next send...")
                    await asyncio.sleep(delay_seconds)
            
            if not auto_repeat:
                break
            
            if self.is_broadcasting:
                print(f"=== CYCLE {cycle} COMPLETE ===")
                print(f"Next cycle in {repeat_interval} seconds... (press ABORT to stop)")
                await asyncio.sleep(repeat_interval)
                
        print("\n=== Broadcast Finish ===")
        self.is_broadcasting = False

    def run_broadcast_sync(self, target_group_ids, message_text, delay_seconds, auto_repeat=False, repeat_interval=300):
        self.run_sync(self._broadcast_async(target_group_ids, message_text, delay_seconds, auto_repeat, repeat_interval))
        
    def stop_broadcast(self):
        self.is_broadcasting = False

    async def _join_groups_async(self, links, join_count):
        connected_clients = []
        for phone, client in self.clients.items():
            if not client.is_connected(): await client.connect()
            connected_clients.append({"phone": phone, "client": client})

        if not connected_clients:
            print("Error: No connected accounts.")
            return
            
        # Target only `join_count` links from the array
        targets = links[:int(join_count)]
        
        print(f"Initiating mass join on {len(connected_clients)} nodes for {len(targets)} targets...")
        
        for acc in connected_clients:
            client = acc["client"]
            phone = acc["phone"]
            joined = 0
            print(f"\n--- Node: {phone} ---")
            
            for link in targets:
                try:
                    # Clean the link
                    target_url = link.replace("https://t.me/", "").replace("t.me/", "").strip()
                    if "/" in target_url and not target_url.startswith("joinchat"):
                        # E.g. chat_3/20162324 => we just need the username 'chat_3' to join the group
                        target_url = target_url.split("/")[0]
                        
                    if target_url.startswith("+") or target_url.startswith("joinchat/"):
                        # Invite link hash
                        hash_val = target_url.replace("joinchat/", "").replace("+", "")
                        await client(ImportChatInviteRequest(hash_val))
                    else:
                        # Public username
                        entity = await client.get_entity(target_url)
                        await client(JoinChannelRequest(entity))
                    
                    joined += 1
                    print(f"[+] Joined {target_url} successfully.")
                except Exception as e:
                    print(f"[-] Failed to join {link} - {str(e)}")
                    
                await asyncio.sleep(2) # Prevent flood waits

        print("\n=== Mass Join Complete ===")

    def run_join_groups(self, links, join_count):
        self.run_sync(self._join_groups_async(links, join_count))

