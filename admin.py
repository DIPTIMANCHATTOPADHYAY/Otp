from bot_init import bot
from db import get_user, update_user, get_user, update_user, db
from config import ADMIN_IDS
from telegram_otp import session_manager
from utils import require_channel_membership
import os

BOT_LANG_FILE = 'bot_lang.txt'
BOT_LANGUAGES = ['English', 'Arabic', 'Chinese']

def get_bot_default_language():
    if os.path.exists(BOT_LANG_FILE):
        with open(BOT_LANG_FILE, 'r') as f:
            lang = f.read().strip()
            if lang in BOT_LANGUAGES:
                return lang
    return 'English'

def set_bot_default_language(lang):
    with open(BOT_LANG_FILE, 'w') as f:
        f.write(lang)
    # Update in database as well
    try:
        db.settings.update_one({'key': 'default_language'}, {'$set': {'value': lang}}, upsert=True)
    except Exception as e:
        print(f"Failed to update default language in DB: {e}")

def is_admin(user_id):
    return user_id in ADMIN_IDS

@bot.message_handler(commands=['admin'])
@require_channel_membership
def handle_admin(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return

    admin_commands = [
        ("/admin", "Show this admin command list"),
        ("/add <code> <qty> <price> <sec> [name] [flag]", "Add/update country with all parameters"),
        ("/countries", "List all configured countries"),
        ("/pay <user_id>", "Approve withdrawal for specific user"),
        ("/paycard <card_name>", "Approve all withdrawals for a leader card"),
        ("/rejectpayment <user_id|card:name> [reason]", "Reject withdrawals with optional reason"),
        ("/cardw <card_name>", "Check withdrawal stats for a leader card"),
        ("/userdel <user_id>", "Delete user and all their data"),
        ("/cun <country_code> <quantity>", "Set country number capacity (legacy)"),
        ("/setprice <country_code> <price>", "Set price for a country (legacy)"),
        ("/settime <country_code> <seconds>", "Set claim time for a country (legacy)"),
        ("/numberd <country_code>", "Delete a country from the system"),
        ("/card <card_name>", "Add a new leader card"),
        ("/notice ", "Reply text All User Notification"),
        ("/sessions", "View session overview by country"),
        ("/sessionstats", "Detailed statistics for each country"),
        ("/migratesessions", "Migrate legacy sessions to country folders"),
        ("/cleanupsessions", "Remove empty country folders"),
        ("/exportsessions", "Export session information to JSON"),
        ("/get +country_code [YYYYMMDD]", "Download all sessions for a country (optionally by date) in zip file"),
        ("/getall [+country_code] [YYYYMMDD]", "Download all sessions from all countries or a specific country/date in zip file"),
        ("/getinfo +country_code [YYYYMMDD]", "Get detailed info about sessions for a country (optionally by date)"),
        ("/deletesessions +country_code [YYYYMMDD]", "Delete all sessions for a country (optionally by date)"),
        ("/cleansessionsall", "Delete all session files in all countries (global cleanup)"),
        ("/checkdevices +number", "Check device count for a phone number"),
        ("/testdevicereward +number", "Test reward eligibility for a phone number"),
        ("/devicestatus", "Show device security status report"),
        ("/testfailmessage <language> +number", "Test verification failure message in different languages"),
        ("/cleanusers", "Check for users who blocked the bot or have issues"),
        ("/removeblocked", "Remove users who blocked the bot from database")
    ]

    response = "🔧 *Admin Command List* 🔧\n\n"
    for cmd, desc in admin_commands:
        response += f"• `{cmd}` - {desc}\n"

    bot.reply_to(message, response, parse_mode="Markdown")

@bot.message_handler(commands=['sessions'])
def handle_sessions_command(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        sessions_by_country = session_manager.list_country_sessions()
        
        if not sessions_by_country:
            bot.reply_to(message, "📁 No sessions found")
            return
        
        response = "📊 **Session Overview by Country:**\n\n"
        total_sessions = 0
        
        for country_code, sessions in sessions_by_country.items():
            response += f"🌍 **{country_code}**: {len(sessions)} sessions\n"
            total_sessions += len(sessions)
        
        response += f"\n📈 **Total Sessions**: {total_sessions}"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['sessionstats'])
def handle_session_stats(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        sessions_by_country = session_manager.list_country_sessions()
        
        if not sessions_by_country:
            bot.reply_to(message, "📁 No sessions found")
            return
        
        response = "📊 **Session Statistics:**\n\n"
        
        for country_code, sessions in sessions_by_country.items():
            total_size = sum(session.get('size', 0) for session in sessions)
            avg_size = total_size / len(sessions) if sessions else 0
            
            response += f"🌍 **{country_code}**:\n"
            response += f"   📱 Sessions: {len(sessions)}\n"
            response += f"   💾 Total Size: {total_size:,} bytes\n"
            response += f"   📊 Average: {avg_size:.0f} bytes\n\n"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['migratesessions'])
def handle_migrate_sessions(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Import the migration function
        from session_manager import migrate_legacy_sessions
        
        bot.reply_to(message, "🔄 Starting session migration...")
        
        # Run migration
        migrate_legacy_sessions()
        
        bot.reply_to(message, "✅ Session migration completed!")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['cleanupsessions'])
def handle_cleanup_sessions(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Import the cleanup function
        from session_manager import cleanup_empty_folders
        
        bot.reply_to(message, "🧹 Starting session cleanup...")
        
        # Run cleanup
        cleanup_empty_folders()
        
        bot.reply_to(message, "✅ Session cleanup completed!")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['exportsessions'])
def handle_export_sessions(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Import the export function
        from session_manager import export_session_info
        
        bot.reply_to(message, "📄 Exporting session information...")
        
        # Run export
        export_session_info()
        
        bot.reply_to(message, "✅ Session export completed! Check the generated JSON file.")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['setbotlang'])
@require_channel_membership
def handle_set_bot_lang(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    args = message.text.split()
    if len(args) < 2 or args[1] not in BOT_LANGUAGES:
        bot.reply_to(message, f"Usage: /setbotlang <language>\nAvailable: {', '.join(BOT_LANGUAGES)}")
        return
    lang = args[1]
    set_bot_default_language(lang)
    bot.reply_to(message, f"✅ Bot default language set to {lang}")