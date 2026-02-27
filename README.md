# Promo Tool - Telegram Automation

A Flask-based web application for managing Telegram accounts and automating messaging tasks.

## Features

- 🌐 Web-based interface (no desktop app required)
- 📱 Multi-account Telegram management
- 📤 Broadcast messages to multiple groups
- 👥 Mass join groups
- 🔐 License key validation
- ☁️ Serverless deployment on Vercel

## Prerequisites

- Python 3.9+
- Flask and dependencies (see `requirements.txt`)
- A Vercel account for deployment
- Telegram API credentials

## Installation (Local Development)

1. Clone the repository:
   ```bash
   git clone https://github.com/roryxx/Promo-tool.git
   cd Promo-tool
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file from `.env.example`:
   ```bash
   cp .env.example .env
   ```

5. Run the application locally:
   ```bash
   python app.py
   ```

6. Open your browser and go to `http://localhost:5000`

## Deployment on Vercel

### Prerequisites
- Vercel account (free at https://vercel.com)
- GitHub account with the repository pushed

### Steps

1. **Connect your GitHub repository to Vercel:**
   - Go to https://vercel.com/new
   - Click "Import Git Repository"
   - Select your GitHub repo (roryxx/Promo-tool)
   - Click "Import"

2. **Configure project settings:**
   - Framework Preset: **Python**
   - Root Directory: `.`
   - Build Command: (leave default)
   - Output Directory: (leave default)

3. **Add Environment Variables:**
   - Click "Environment Variables"
   - Add the following variables:
     ```
     ADMIN_SERVER_URL=https://promoserver.vercel.app
     HWID=VERCEL-DEFAULT
     PORT=5000
     ```

4. **Deploy:**
   - Click "Deploy"
   - Wait for deployment to complete
   - Your app will be accessible at `https://your-project.vercel.app`

## API Endpoints

### License Management
- `POST /api/validate_key` - Validate license key

### Account Management
- `POST /api/send_otp` - Send OTP to phone number
- `POST /api/verify_otp` - Verify OTP code
- `POST /api/verify_2fa` - Verify 2FA password
- `GET /api/accounts` - Get list of logged-in accounts
- `POST /api/delete_account` - Delete an account session

### Groups
- `POST /api/fetch_groups` - Fetch groups from account
- `POST /api/join_groups` - Join target groups

### Broadcasting
- `POST /api/broadcast` - Start broadcast to groups
- `POST /api/broadcast/stop` - Stop active broadcast

### Misc
- `GET /api/data` - Fetch categories and settings from admin server
- `GET /health` - Health check endpoint

## Configuration

Update the `ADMIN_SERVER_URL` in `app.py` or set it as an environment variable:

```python
ADMIN_SERVER_URL = os.environ.get("ADMIN_SERVER_URL", "https://promoserver.vercel.app")
```

## Project Structure

```
.
├── app.py                 # Flask application
├── telegram_manager.py   # Telegram API wrapper
├── requirements.txt      # Python dependencies
├── vercel.json          # Vercel configuration
├── .env.example         # Environment variables template
├── .gitignore          # Git ignore rules
├── ui/
│   ├── index.html      # Web interface
│   └── logo.ico        # Logo
└── sessions/           # Telegram session files (local only)
```

## Important Notes

### For Vercel Deployment
- **Session Storage**: Telegram session files are stored locally. On Vercel (serverless), these won't persist between function calls. Consider:
  - Using a database (PostgreSQL, MongoDB) to store encrypted sessions
  - Using Vercel's KV Store for Redis-like storage
  - Keeping a persistent VPS for background tasks

- **Timeout Limits**: Vercel functions have a max timeout (depends on plan). Long-running broadcasts might timeout.
  
- **Background Jobs**: For continuous operation (auto-broadcast), consider:
  - Railway.app (better for persistent bots)
  - AWS Lambda with Step Functions
  - A dedicated VPS (recommended for production)

### For Local/VPS Deployment
- Works as-is on local machines or standard VPS
- No timeout or persistence concerns
- Can run 24/7 without issues

## Alternative Hosting Recommendations

| Platform | Cost | Best For |
|----------|------|----------|
| **Vercel** | Free/Paid | Serverless APIs, one-time tasks |
| **Railway** | Free/Paid | Python apps, persistent bots |
| **Render** | Free/Paid | Flask apps, simple bots |
| **Heroku** | Paid | Reliable deployment (no free tier) |
| **VPS (AWS, DigitalOcean)** | $5+/mo | Production, 24/7 operation |

## Troubleshooting

### ImportError for Telethon
```bash
pip install telethon==1.35.0
```

### Session not loading on startup
- Check that sessions folder exists
- Ensure session files have correct permissions

### License validation fails
- Check internet connection
- Verify `ADMIN_SERVER_URL` is correct and accessible
- Check license key format

## License

This project is provided as-is. Ensure you comply with Telegram's Terms of Service when using.

## Support

For issues, create a GitHub issue or contact the maintainer.
