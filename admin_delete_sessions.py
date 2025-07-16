import os
import datetime
import re
import logging
from bot_init import bot
from config import ADMIN_IDS, SESSIONS_DIR
from telegram_otp import session_manager
from utils import require_channel_membership

logging.basicConfig(level=logging.INFO)

def parse_date_arg(arg):
    if re.match(r'^\d{8}$', arg):
        return arg[:4] + '-' + arg[4:6] + '-' + arg[6:]
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', arg):
        return arg
    return None

def session_matches_date(session, date_str):
    if not date_str:
        return True
    created = session.get('created')
    if not created:
        return False
    session_date = datetime.datetime.fromtimestamp(created).strftime('%Y-%m-%d')
    return session_date == date_str

def format_size(size):
    return f"{size:,} bytes"

def format_datetime(ts):
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

# /deletesessions +country_code [date]
@bot.message_handler(commands=['deletesessions'])
@require_channel_membership
def handle_delete_sessions(message):
    try:
        logging.info(f"/deletesessions command triggered by user {message.from_user.id} with text: {message.text}")
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            bot.reply_to(message, "❌ You are not authorized to use this command.")
            return
        args = message.text.split()
        if len(args) < 2 or not args[1].startswith('+'):
            bot.reply_to(message, "Usage: /deletesessions +country_code [YYYYMMDD]\nExample: /deletesessions +1 20250712")
            return
        country_code = args[1]
        date_str = parse_date_arg(args[2]) if len(args) > 2 else None
        sessions = session_manager.list_country_sessions(country_code)
        if not sessions or country_code not in sessions or not sessions[country_code]:
            bot.reply_to(message, f"❌ No sessions found for {country_code}")
            return
        filtered_sessions = [s for s in sessions[country_code] if session_matches_date(s, date_str)]
        if not filtered_sessions:
            bot.reply_to(message, f"❌ No sessions found for {country_code} on {date_str if date_str else 'any date'}.")
            return
        deleted_count = 0
        deleted_size = 0
        for session in filtered_sessions:
            path = session['session_path']
            if os.path.exists(path):
                try:
                    deleted_size += os.path.getsize(path)
                    os.remove(path)
                    deleted_count += 1
                except Exception as e:
                    logging.error(f"Failed to delete {path}: {e}")
        summary = (
            f"🗑️ Deleted Sessions for {country_code}{' on ' + date_str if date_str else ''}\n\n"
            f"📁 Files deleted: {deleted_count}\n"
            f"💾 Total size: {format_size(deleted_size)}\n"
            f"✅ Session cleanup complete."
        )
        bot.send_message(message.chat.id, summary)
    except Exception as e:
        logging.exception("Error in /deletesessions command handler:")
        bot.reply_to(message, f"❌ Internal error: {e}")