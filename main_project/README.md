# RG Assistant - WhatsApp Bot Server

This is the Python backend server for RG Assistant WhatsApp bot using Twilio.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd main_project
pip install -e .
```

Or install directly:
```bash
pip install flask twilio requests python-dotenv
```

### 2. Configure Environment

```bash
# Copy the example environment file
copy .env.example .env

# Edit .env and add your Twilio credentials:
# TWILIO_ACCOUNT_SID=AC...
# TWILIO_AUTH_TOKEN=...
# TWILIO_PHONE_NUMBER=whatsapp:+14155238886
```

### 3. Set Up Twilio

1. Sign up at [twilio.com](https://twilio.com)
2. Go to Console → Messaging → Settings → WhatsApp Sandbox
3. Join sandbox by sending `join <your-code>` to +14155238886
4. Copy your Account SID and Auth Token

### 4. Run the Server

```bash
# Option 1: Run directly
python -m main.twilio_server

# Option 2: Run with Python
python main/main/__main__.py
```

### 5. Expose to Internet (for testing)

```bash
# Install ngrok
npm install -g ngrok

# Expose your local server
ngrok http 5000
```

### 6. Configure Twilio Webhook

1. Go to Twilio Console → Messaging → Settings → WhatsApp Sandbox
2. Set "When a message comes in" to:
   ```
   https://your-ngrok-url/whatsapp
   ```

### 7. Test

Send a WhatsApp message to your sandbox number!

## 📱 Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/whatsapp` | POST | Twilio webhook (receives messages) |
| `/whatsapp/status` | GET | Check Twilio connection |
| `/test/ai` | GET/POST | Test AI response |
| `/send` | POST | Send WhatsApp message |

## 🔧 Configuration

All settings are in `.env` file:

```env
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=whatsapp:+14155238886
COHERE_API_KEY=rr1AlC5J2MKJe5rgAwOE5h7Rtx6rRO7qjPZ7E8pH
PORT=5000
DEBUG=True
```

## 📁 Project Structure

```
main_project/
├── main/
│   ├── __init__.py
│   ├── __main__.py       # Entry point
│   ├── twilio_server.py  # WhatsApp server
│   └── telegram_server.py # Telegram bot
├── pyproject.toml
├── .env.example
└── README.md
```

## ⚠️ Production Notes

- Never commit `.env` file to GitHub
- Use environment variables in production
- Set `DEBUG=False` in production
- Use a proper web server (gunicorn, uwsgi)
- Enable HTTPS for webhook

## 💰 Costs

- Twilio WhatsApp: $0.005-0.02 per message
- Your trial credit: ~$15.50
- Cohere API: Check your plan
