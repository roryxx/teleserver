from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import requests
from telegram_manager import TelegramManager
import threading

app = Flask(__name__, template_folder='ui', static_folder='ui')
CORS(app)

ADMIN_SERVER_URL = "https://promoserver.vercel.app"  # TODO: Change to real server IP if needed

# Global Telegram Manager
tg_manager = TelegramManager()

# Store license validation state
license_validated = {}

def get_hwid():
    """Generates a Hardware ID (simplified for Vercel)"""
    try:
        # For Vercel, use environment variable or a static ID
        return os.environ.get("HWID", "VERCEL-DEFAULT")
    except Exception:
        return "VERCEL-DEFAULT"


@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')


@app.route('/api/validate_key', methods=['POST'])
def validate_license():
    """Validate license key with admin server"""
    key = request.form.get('key')
    hwid = request.form.get('hwid', get_hwid())
    
    try:
        response = requests.post(f"{ADMIN_SERVER_URL}/api/validate_key", data={
            "key": key,
            "hwid": hwid
        }, timeout=5)
        
        data = response.json()
        
        if response.status_code == 200 and data.get("status") == "success":
            license_validated[hwid] = True
            return jsonify({
                "success": True,
                "message": data.get("message"),
                "expires_in": data.get("expires_in_days")
            })
        else:
            return jsonify({
                "success": False,
                "message": data.get("detail", "Invalid Key")
            }), 400
            
    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": False,
            "message": "Could not connect to Admin Server. Check your internet."
        }), 500


@app.route('/api/send_otp', methods=['POST'])
def send_otp():
    """Start login process for a new account"""
    phone_number = request.json.get('phone_number')
    
    def _run():
        result = tg_manager.run_sync(tg_manager.send_otp(phone_number))
    
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"success": True, "message": "OTP request sent"})


@app.route('/api/verify_otp', methods=['POST'])
def verify_otp():
    """Verify OTP for the account"""
    phone_number = request.json.get('phone_number')
    otp = request.json.get('otp')
    
    try:
        result = tg_manager.run_sync(tg_manager.verify_otp(phone_number, otp))
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/verify_2fa', methods=['POST'])
def verify_2fa():
    """Verify 2FA password"""
    phone_number = request.json.get('phone_number')
    password = request.json.get('password')
    
    try:
        result = tg_manager.run_sync(tg_manager.verify_2fa(phone_number, password))
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/accounts', methods=['GET'])
def get_logged_in_accounts():
    """Return a list of all active sessions"""
    accounts = tg_manager.get_session_list()
    return jsonify({"accounts": accounts})


@app.route('/api/delete_account', methods=['POST'])
def delete_account():
    """Delete a session"""
    phone_number = request.json.get('phone_number')
    result = tg_manager.delete_session(phone_number)
    return jsonify(result)


@app.route('/api/fetch_groups', methods=['POST'])
def fetch_groups_from_account():
    """Fetch all groups/chats from a specific account"""
    phone_number = request.json.get('phone_number')
    
    try:
        result = tg_manager.run_sync(tg_manager.get_dialogs(phone_number))
        return jsonify({"success": True, "groups": result})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/broadcast', methods=['POST'])
def start_broadcast():
    """Start the broadcast to groups"""
    data = request.json
    target_group_ids = data.get('target_group_ids', [])
    message_text = data.get('message_text', '')
    delay_seconds = data.get('delay_seconds', 10)
    auto_repeat = data.get('auto_repeat', False)
    repeat_interval = data.get('repeat_interval', 300)
    
    if not tg_manager.clients:
        return jsonify({"success": False, "message": "No active accounts to send from."}), 400
    
    # Broadcast runs in a background thread
    threading.Thread(
        target=tg_manager.run_broadcast_sync,
        args=(target_group_ids, message_text, int(delay_seconds), auto_repeat, int(repeat_interval)),
        daemon=True
    ).start()
    
    return jsonify({"success": True, "message": "Broadcast started."})


@app.route('/api/broadcast/stop', methods=['POST'])
def stop_broadcast():
    """Stop the broadcast"""
    tg_manager.stop_broadcast()
    return jsonify({"success": True, "message": "Stopping broadcast..."})


@app.route('/api/data', methods=['GET'])
def fetch_app_data():
    """Fetch Categories, Links, and Settings from Admin Server"""
    try:
        response = requests.get(f"{ADMIN_SERVER_URL}/api/data", timeout=5)
        if response.status_code == 200:
            return jsonify({"success": True, "data": response.json()})
        else:
            return jsonify({"success": False, "message": "Admin server responded with error."}), 400
    except requests.exceptions.RequestException:
        return jsonify({"success": False, "message": "Could not fetch data from Admin Server."}), 500


@app.route('/api/join_groups', methods=['POST'])
def join_target_groups():
    """Join target groups using active accounts"""
    data = request.json
    links_array = data.get('links', [])
    join_count = data.get('join_count', len(links_array))
    
    if not tg_manager.clients:
        return jsonify({"success": False, "message": "No active accounts to join from."}), 400
    
    threading.Thread(
        target=tg_manager.run_join_groups,
        args=(links_array, join_count),
        daemon=True
    ).start()
    
    return jsonify({"success": True, "message": "Mass Join started."})


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Vercel"""
    return jsonify({"status": "healthy", "accounts": tg_manager.get_session_list()})


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    # For local testing
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
