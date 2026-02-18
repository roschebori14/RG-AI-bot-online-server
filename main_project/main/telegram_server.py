
import os
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (in parent directory)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Telegram Bot Configuration
# Get token from @BotFather
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Cohere AI Configuration (from your existing script.js)
COHERE_API_KEY = os.environ.get("COHERE_API_KEY", "rr1AlC5J2MKJe5rgAwOE5h7Rtx6rRO7qjPZ7E8pH")
COHERE_MODEL = os.environ.get("COHERE_MODEL", "command-a-03-2025")

# ============================================================================
# CUSTOM BOT IDENTITY
# ============================================================================

BOT_NAME = "RG Assistant"
COMPANY_NAME = "RG-TECH"
CREATOR_NAME = "Rosch Ebori"
CREATOR_INFO = """
I was created by RG-TECH, a technology company founded and owned by Rosch Ebori.

RG-TECH is an innovative tech company specializing in:
• AI-powered solutions
• Custom software development
• Mobile and web applications
• Digital transformation services

The company is based in Cameroon and serves clients globally.

Rosch Ebori is the visionary founder who developed this AI assistant to help people with various tasks including coding, writing, analysis, research, and general questions.

This bot is powered by advanced AI technology from Cohere, customized with RG-TECH's unique personality and capabilities.
"""

# Custom responses for specific questions
CUSTOM_RESPONSES = {
    "who created you": BOT_NAME + " was created by " + CREATOR_NAME + ", the founder of " + COMPANY_NAME + ". " + CREATOR_INFO,
    "who made you": BOT_NAME + " was created by " + CREATOR_NAME + ", the founder of " + COMPANY_NAME + ". " + CREATOR_INFO,
    "who is your creator": BOT_NAME + " was created by " + CREATOR_NAME + ", the founder of " + COMPANY_NAME + ". " + CREATOR_INFO,
    "what company": COMPANY_NAME + " is a technology company founded by " + CREATOR_NAME + ". " + CREATOR_INFO,
    "what is rg-tech": COMPANY_NAME + " is a technology company founded by " + CREATOR_NAME + ". " + CREATOR_INFO,
    "who is rosch": CREATOR_NAME + " is the founder and owner of " + COMPANY_NAME + ". He is a tech entrepreneur and developer who created this AI assistant.",
    "about yourself": BOT_NAME + " - Your AI Assistant\n\n" + CREATOR_INFO,
}

# ============================================================================
# MONETIZATION SETTINGS
# ============================================================================

# Telegram BotAds Configuration
# To enable BotAds:
# 1. Your bot needs 1,000+ subscribers
# 2. Apply at https://telegram.org/botads
# 3. Use @BotFather to enable ads for your bot
BOTADS_ENABLED = os.environ.get("BOTADS_ENABLED", "false").lower() == "true"
BOTADS_TOKEN = os.environ.get("BOTADS_TOKEN", "")  # Your BotAds token after approval

# Affiliate Programs Configuration
AFFILIATE_LINKS = {
    "crypto": {
        "name": "Crypto Trading",
        "links": [
            "https://binance.com/ref/YOUR_REF_CODE",
            "https://bybit.com/invite?ref=YOUR_CODE",
        ]
    },
    "shopping": {
        "name": "Online Shopping",
        "links": [
            "https://amazon.com/ref=tag_adbot-20",
        ]
    },
    "services": {
        "name": "VPN & Services",
        "links": [
            "https://nordvpn.com/special/partner",
        ]
    }
}

# Ad display settings
ADS_FREQUENCY = int(os.environ.get("ADS_FREQUENCY", "5"))  # Show ads every N messages

def get_ad_message() -> str:
    """Generate advertisement message"""
    import random
    
    ads = [
        "📢 **Promote Your Bot!**\n\n"
        "Want to reach more users? Use @BotFather to make your bot public and grow your audience!\n\n"
        "Once you have 1,000 subscribers, apply for Telegram BotAds to monetize!",
        
        "💰 **Earn with RG Assistant!**\n\n"
        "Share RG Assistant with friends and family!\n"
        "The more users, the faster we can enable BotAds and generate income!\n\n"
        "Use /refer to get your referral link!",
        
        "🚀 **Grow Your Business**\n\n"
        "Need a custom Telegram bot for your business?\n"
        "Contact @RoschEbori for professional bot development services!",
    ]
    
    return random.choice(ads)


# ============================================================================
# USER SETTINGS & STATE
# ============================================================================

# Store user settings (in memory - use database for production)
user_settings = {}
user_conversations = {}
user_message_counts = {}  # Track message count for ad frequency

# Usage limits
FREE_DAILY_LIMIT = 10
PREMIUM_DURATION_DAYS = 14  # 2 weeks

def get_user_settings(user_id):
    """Get user settings, create default if not exists"""
    if user_id not in user_settings:
        user_settings[user_id] = {
            "tone": "friendly",
            "language": "en",
            "notifications": True,
            "usage": {"date": None, "used": 0, "unlimited_until": None}
        }
    return user_settings[user_id]

def set_user_tone(user_id, tone):
    """Set user's response tone"""
    settings = get_user_settings(user_id)
    settings["tone"] = tone
    return tone

def get_today():
    """Get today's date string"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")

def is_premium_active(user_id):
    """Check if user has premium"""
    settings = get_user_settings(user_id)
    usage = settings.get("usage", {})
    unlimited_until = usage.get("unlimited_until")
    if not unlimited_until:
        return False
    return unlimited_until >= get_today()

def check_and_consume_prompt(user_id):
    """Check if user can send a message, consume 1 if allowed"""
    settings = get_user_settings(user_id)
    usage = settings["usage"]
    today = get_today()
    
    # Reset daily usage if new day
    if usage.get("date") != today:
        usage["date"] = today
        usage["used"] = 0
    
    # Check if premium
    if is_premium_active(user_id):
        return True, None
    
    # Check if under limit
    if usage.get("used", 0) < FREE_DAILY_LIMIT:
        usage["used"] = usage.get("used", 0) + 1
        remaining = FREE_DAILY_LIMIT - usage["used"]
        return True, remaining
    
    # Limit reached
    return False, 0

def apply_coupon_code(user_id, coupon_code):
    """Apply a coupon code for premium"""
    coupon_code = coupon_code.upper().strip()
    
    # Valid coupon codes - only give these to customers who pay!
    valid_coupons = {
        "RG100": 14,   # 14 days - paid customer
        "TEST1": 1,     # 1 day - testing
    }
    
    if coupon_code in valid_coupons:
        from datetime import datetime, timedelta
        expiry_date = datetime.now() + timedelta(days=valid_coupons[coupon_code])
        expiry_str = expiry_date.strftime("%Y-%m-%d")
        
        settings = get_user_settings(user_id)
        settings["usage"]["unlimited_until"] = expiry_str
        
        return True, valid_coupons[coupon_code]
    
    return False, 0

def get_usage_info(user_id):
    """Get user's usage information"""
    settings = get_user_settings(user_id)
    usage = settings.get("usage", {})
    today = get_today()
    
    # Reset if new day
    if usage.get("date") != today:
        usage["date"] = today
        usage["used"] = 0
    
    if is_premium_active(user_id):
        return {
            "type": "premium",
            "remaining": "Unlimited",
            "expires": usage.get("unlimited_until", "N/A")
        }
    else:
        remaining = FREE_DAILY_LIMIT - usage.get("used", 0)
        return {
            "type": "free",
            "remaining": remaining,
            "limit": FREE_DAILY_LIMIT,
            "reset": "Tomorrow"
        }

# ============================================================================
# AI RESPONSE FUNCTION
# ============================================================================

def get_ai_response(prompt: str, user_id: int, conversation_history: list = None) -> str:
    """
    Call Cohere API to generate AI response.
    Uses the new Chat API with conversation history for context.
    
    Args:
        prompt: The user's message
        user_id: The user's Telegram ID (used to track conversation)
        conversation_history: List of previous message dicts with 'role' and 'message' keys
    """
    if conversation_history is None:
        conversation_history = []
    
    # Check for custom responses first
    prompt_lower = prompt.lower().strip()
    
    for key, response in CUSTOM_RESPONSES.items():
        if key in prompt_lower:
            return response
    
    # Also check if asking about the bot itself
    if any(phrase in prompt_lower for phrase in ["who are you", "what are you", "tell me about yourself", "about you"]):
        return BOT_NAME + " - Your AI Assistant\n\n" + CREATOR_INFO
    
    try:
        url = "https://api.cohere.ai/v1/chat"
        headers = {
            "Authorization": f"Bearer {COHERE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Build messages for chat API with conversation history
        data = {
            "model": COHERE_MODEL,
            "message": prompt,
            "chat_history": conversation_history,
            "max_tokens": 2048,
            "temperature": 0.3
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("text", "").strip()
        
        logger.error(f"Cohere API error: {response.status_code} - {response.text}")
        return "Sorry, I encountered an error. Please try again."
        
    except requests.exceptions.Timeout:
        logger.error("Cohere API timeout")
        return "Sorry, the request took too long. Please try again."
    except Exception as e:
        logger.error(f"Error getting AI response: {e}")
        return "Sorry, something went wrong. Please try again."

# ============================================================================
# TELEGRAM BOT HANDLERS
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_message = """👋 Welcome to RG Assistant!

I'm an AI-powered assistant that can help you with:
• 💻 Coding and programming questions
• 📝 Writing and editing
• 🔍 Research and analysis
• 💡 General questions

Just send me a message and I'll respond!

Use /help to see available commands."""
    
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_message = """📚 Available Commands:

/start - Start the bot
/help - Show this help message
/settings - Configure your preferences
/about - About RG Assistant

💬 Just send me a message and I'll respond!
"""
    await update.message.reply_text(help_message)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /about command"""
    about_message = """🤖 RG Assistant - Your AI Companion

━━━━━━━━━━━━━━━━━━━━━━

📌 ABOUT:
RG Assistant is an advanced AI chatbot developed by RG-TECH, a innovative technology company based in Cameroon.

👨‍💼 CREATOR:
Founded by Rosch Ebori, a passionate tech entrepreneur dedicated to bringing AI solutions to Africa and beyond.

🔧 WHAT I CAN DO:
• 💻 Coding & Programming
• 📝 Content Writing & Editing  
• 🔍 Research & Analysis
• 💡 Problem Solving
• 📊 Data Interpretation
• 🌐 Language Translation
• 🎓 Tutoring & Learning

💡 FEATURES:
• Fast AI-powered responses
• Available 24/7
• Multi-topic assistance
• Friendly & Professional tone

━━━━━━━━━━━━━━━━━━━━━━

🏢 RG-TECH - Innovating the Future with AI

💬 Send me a message to get started!"""
    
    await update.message.reply_text(about_message)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    
    settings_message = f"""⚙️ Your Settings

━━━━━━━━━━━━━━━━━━━━━━

🎭 Response Tone: {settings['tone'].capitalize()}
🌐 Language: {settings['language'].upper()}
🔔 Notifications: {'On' if settings['notifications'] else 'Off'}

━━━━━━━━━━━━━━━━━━━━━━

📝 Available Tones:
• Friendly - Warm and casual
• Professional - Business-like
• Casual - Relaxed chat
• Formal - Strict and proper

💡 To change tone, use:
/tone friendly
/tone professional
/tone casual
/tone formal

🔔 Toggle notifications:
/notifications on
/notifications off"""
    
    await update.message.reply_text(settings_message)


async def tone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tone command - Set response tone"""
    user_id = update.effective_user.id
    
    if context.args:
        tone = context.args[0].lower()
        valid_tones = ["friendly", "professional", "casual", "formal"]
        
        if tone in valid_tones:
            set_user_tone(user_id, tone)
            await update.message.reply_text(f"✅ Tone set to: {tone.capitalize()}!")
        else:
            await update.message.reply_text(
                f"❌ Invalid tone. Choose from: {', '.join(valid_tones)}\n\n"
                f"Example: /tone friendly"
            )
    else:
        await update.message.reply_text(
            "🎭 Set your response tone!\n\n"
            "Available tones:\n"
            "• friendly\n"
            "• professional\n"
            "• casual\n"
            "• formal\n\n"
            "Example: /tone friendly"
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - Bot status"""
    import datetime
    
    status_message = f"""📊 {BOT_NAME} Status

━━━━━━━━━━━━━━━━━━━━━━

✅ Status: Online & Running
🟢 AI Engine: Cohere
📅 Date: {datetime.datetime.now().strftime('%Y-%m-%d')}
⏰ Time: {datetime.datetime.now().strftime('%H:%M:%S')} UTC

🔧 Version: 2.0
💻 Platform: Telegram Bot API

━━━━━━━━━━━━━━━━━━━━━━

🏢 {COMPANY_NAME}
© 2026 All Rights Reserved"""
    
    await update.message.reply_text(status_message)


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ping command"""
    import datetime
    
    await update.message.reply_text(
        f"🏓 Pong!\n\n"
        f"⏱️ Response time: < 100ms\n"
        f"✅ Bot is running smoothly!"
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command - Clear chat"""
    user_id = update.effective_user.id
    
    # Clear conversation history for this user
    if user_id in user_conversations:
        user_conversations[user_id] = []
    
    await update.message.reply_text(
        "🗑️ Chat cleared!\n\n"
        "Starting fresh conversation..."
    )


async def refer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /refer command - Get referral link"""
    user_id = update.effective_user.id
    
    # Generate referral code (simple user_id based)
    referral_code = f"RG{user_id}"
    bot_username = context.bot.username
    
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    await update.message.reply_text(
        f"📤 **Your Referral Link**\n\n"
        f"Share this link to earn rewards:\n\n"
        f"`{referral_link}`\n\n"
        f"💡 **How it works:**\n"
        f"• Each friend who joins using your link\n"
        f"• You get +5 free messages per referral\n"
        f"• They also get +10 free messages!\n\n"
        f"🔗 Copy and share your link!"
    )


async def ads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ads command - Show monetization info"""
    msg = """💰 **Monetization Info**\n\n"
"━━━━━━━━━━━━━━━━━━━━━━\n\n"
"📢 **Telegram BotAds**\n"
"To enable ads and earn:\n"
"• Your bot needs 1,000+ subscribers\n"
"• Apply at telegram.org/botads\n"
"• Telegram pays per ad impression/click\n\n"
"━━━━━━━━━━━━━━━━━━━━━━\n\n"
"🔗 **Affiliate Income**\n"
"We partner with various services.\n"
"Use /offers to see current deals!\n\n"
"━━━━━━━━━━━━━━━━━━━━━━\n\n"
"🚀 **Grow With Us**\n"
"Share RG Assistant to help us\n"
"reach 1,000 users faster!\n\n"
"Use /refer to get your link!"""
    
    await update.message.reply_text(msg)


async def offers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /offers command - Show affiliate offers"""
    import random
    
    offers = [
        """🔥 **Hot Offers!**\n\n"
"━━━━━━━━━━━━━━━━━━━━━━\n\n"
"💳 **Crypto Exchanges**\n"
"• Binance - Low fees trading\n"
"• Bybit - Bonus on signup\n"
"• OKX - 20% rebate\n\n"
"━━━━━━━━━━━━━━━━━━━━━━\n\n"
"🔐 **VPN Services**\n"
"• NordVPN - 68% OFF\n"
"• Surfshark - 80% OFF\n\n"
"━━━━━━━━━━━━━━━━━━━━━━\n\n"
"🛒 **Shopping**\n"
"• Amazon - Global shopping\n"
"• AliExpress - Cheap deals\n\n"
"💬 Ask for specific links!""",
        
        """💎 **Premium Deals**\n\n"
"━━━━━━━━━━━━━━━━━━━━━━\n\n"
"📺 **Streaming**\n"
"• Netflix - Get 50% OFF\n"
"• Spotify - 3 months FREE\n\n"
"━━━━━━━━━━━━━━━━━━━━━━\n\n"
"🎮 **Gaming**\n"
"• Steam - Weekly deals\n"
"• Epic Games - Free games\n\n"
"━━━━━━━━━━━━━━━━━━━━━━\n\n"
"💼 **Services**\n"
"• Cloud hosting\n"
"• Domain names\n"
"• VPN services\n\n"
"🔗 DM @RoschEbori for links!"""
    ]
    
    await update.message.reply_text(random.choice(offers))


async def promote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /promote command - Promote the bot"""
    bot_username = context.bot.username
    
    promo_texts = [
        f"🤖 Try RG Assistant - Your AI Buddy!\n\n"
        f"👉 t.me/{bot_username}\n\n"
        f"It's free and awesome! 🚀",
        
        f"💡 Need help? Ask RG Assistant!\n\n"
        f"👉 t.me/{bot_username}\n\n"
        f"AI-powered, fast, helpful! ✨",
        
        f"🔥 Check out RG Assistant!\n\n"
        f"👉 t.me/{bot_username}\n\n"
        f"Your personal AI assistant 🎯"
    ]
    
    import random
    await update.message.reply_text(random.choice(promo_texts))


async def usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /usage command - Check message usage"""
    user_id = update.effective_user.id
    usage = get_usage_info(user_id)
    
    if usage["type"] == "premium":
        msg = f"""💎 Premium Member

━━━━━━━━━━━━━━━━━━━━━━

✅ Status: Premium (Unlimited)
📅 Expires: {usage['expires']}

🎉 You have unlimited messages!"""
    else:
        msg = f"""📊 Message Usage

━━━━━━━━━━━━━━━━━━━━━━

� free Tier: {usage['remaining']}/{usage['limit']} messages remaining
⏰ Resets: Tomorrow

━━━━━━━━━━━━━━━━━━━━━━

💡 Upgrade to Premium:
• Unlimited messages
• Priority support
• All features unlocked

Use /upgrade for info!"""
    
    await update.message.reply_text(msg)


async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /upgrade command - Show upgrade info"""
    msg = f"""💎 Upgrade to Premium

━━━━━━━━━━━━━━━━━━━━━━

📦 Premium Benefits:
✅ Unlimited messages
✅ No daily limits
✅ Priority AI responses
✅ All features unlocked

💰 Price: 1500 XAF (2 weeks)

━━━━━━━━━━━━━━━━━━━━━━

💳 Payment Methods:

📱 MTN MOMO USSD:
Dial: *126*9*650674817*1500#

🏦 Orange Money:
Account: +237-659188549

━━━━━━━━━━━━━━━━━━━━━━

⚠️ After payment:
Contact @rosch_ebori on Telegram
OR WhatsApp: +237-650674817

They will give you a coupon code.

🔖 Then use: /coupon YOUR_CODE"""
    
    await update.message.reply_text(msg)


async def coupon_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /coupon command - Apply coupon code"""
    user_id = update.effective_user.id
    
    if context.args:
        coupon_code = context.args[0]
        success, days = apply_coupon_code(user_id, coupon_code)
        
        if success:
            await update.message.reply_text(
                f"🎉 Coupon Applied!\n\n"
                f"✅ You now have {days} days of premium!\n"
                f"📅 Expires in {days} days\n\n"
                f"Enjoy unlimited messages!"
            )
        else:
            await update.message.reply_text(
                "❌ Invalid coupon code.\n\n"
                "Contact @rosch_ebori for valid codes."
            )
    else:
        await update.message.reply_text(
            "🔖 Enter coupon code:\n\n"
            "Example: /coupon TEST4"
        )


async def help2_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help2 - Detailed help"""
    help_message = f"""📖 {BOT_NAME} - Complete Guide

━━━━━━━━━━━━━━━━━━━━━━

🔧 CORE COMMANDS:
━━━━━━━━━━━━━━━━━━━━━━

/start - Welcome message
/help - Quick help
/help2 - This detailed guide
/about - About RG-TECH
/status - Bot status
/ping - Test bot
/settings - Your preferences
/clear - Clear chat

🎭 TONE COMMANDS:
━━━━━━━━━━━━━━━━━━━━━━

/tone friendly - Friendly responses
/tone professional - Work-like
/tone casual - Relaxed
/tone formal - Very proper

💬 USAGE:
━━━━━━━━━━━━━━━━━━━━━━

Just send any message and I'll respond!

Examples:
• "Hello!" - Greet me
• "Write a poem" - Creative writing
• "Explain AI" - Educational
• "Write code" - Programming help

━━━━━━━━━━━━━━━━━━━━━━

🏢 {COMPANY_NAME} - {CREATOR_NAME}"""
    
    await update.message.reply_text(help_message)


async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages - main AI handler"""
    try:
        # Get user's message
        user_message = update.message.text
        user_id = update.effective_user.id
        
        # Get user info for logging
        user = update.effective_user
        logger.info(f"Message from {user.first_name} ({user_id}): {user_message[:50]}...")
        
        # Check usage limits first
        can_send, remaining = check_and_consume_prompt(user_id)
        
        if not can_send:
            # User reached limit
            limit_message = f"""🚫 Daily Limit Reached!

━━━━━━━━━━━━━━━━━━━━━━

You have used all {FREE_DAILY_LIMIT} free messages today.

💎 Upgrade to Premium for unlimited messages!

Use /upgrade to see pricing or
/coupon to enter your code.

⏰ Resets: Tomorrow at midnight"""
            await update.message.reply_text(limit_message)
            return
        
        # Show remaining if not premium
        if remaining is not None and remaining <= 3:
            await update.message.reply_text(
                f"⚠️ You have only {remaining} free messages left today!\n"
                f"Use /upgrade for unlimited!"
            )
        
        # Show typing indicator
        await update.message.chat.send_action("typing")
        
        # Get conversation history for this user
        conversation_history = user_conversations.get(user_id, [])
        
        # Get AI response with conversation history
        ai_response = get_ai_response(user_message, user_id, conversation_history)
        
        # Save conversation to history (for next message)
        if user_id not in user_conversations:
            user_conversations[user_id] = []
        
        # Add user message and bot response to history
        user_conversations[user_id].append({"role": "user", "message": user_message})
        user_conversations[user_id].append({"role": "chatbot", "message": ai_response})
        
        # Limit history to last 10 exchanges (20 messages) to keep context manageable
        if len(user_conversations[user_id]) > 20:
            user_conversations[user_id] = user_conversations[user_id][-20:]
        
        # Send response (Telegram max message length is 4096)
        if len(ai_response) > 4096:
            # Split into chunks if too long
            chunks = [ai_response[i:i+4096] for i in range(0, len(ai_response), 4096)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(ai_response)
        
        logger.info(f"Response sent to {user_id} (conversation history: {len(user_conversations.get(user_id, []))} messages)")
        
        # Show ads periodically (every N messages)
        if user_id not in user_message_counts:
            user_message_counts[user_id] = 0
        
        user_message_counts[user_id] += 1
        
        # Show ad every 10 messages (can be changed with ADS_FREQUENCY)
        if user_message_counts[user_id] % ADS_FREQUENCY == 0:
            import random
            import asyncio
            # Small delay so ad doesn't feel spammy
            await asyncio.sleep(1)
            ad_msg = get_ad_message()
            await update.message.reply_text(ad_msg)
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text("Sorry, something went wrong. Please try again.")


async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos"""
    await update.message.reply_text(
        "📷 Thanks for the image! Image analysis is coming soon.\n\n"
        "For now, please send me text messages."
    )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    await update.message.reply_text(
        "🎤 Thanks for the voice message! Voice transcription is coming soon.\n\n"
        "For now, please send me text messages."
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Run the Telegram bot"""
    logger.info("=" * 50)
    logger.info("RG Assistant Telegram Bot")
    logger.info("=" * 50)
    
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ Please set your TELEGRAM_BOT_TOKEN!")
        logger.error("Edit .env file or set environment variable")
        return
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("help2", help2_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("tone", tone_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("usage", usage_command))
    application.add_handler(CommandHandler("upgrade", upgrade_command))
    application.add_handler(CommandHandler("coupon", coupon_command))
    
    # Monetization commands
    application.add_handler(CommandHandler("refer", refer_command))
    application.add_handler(CommandHandler("ads", ads_command))
    application.add_handler(CommandHandler("offers", offers_command))
    application.add_handler(CommandHandler("promote", promote_command))
    
    # Add message handlers
    # Text messages (except commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))
    
    # Photo messages
    application.add_handler(MessageHandler(filters.PHOTO, handle_photos))
    
    # Voice messages
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start polling
    logger.info("🤖 Bot is running...")
    logger.info("Send a message to your bot on Telegram!")
    
    # Run the bot until Ctrl+C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
