import os
import zipfile
import tempfile
import json
import datetime
import logging
import re
from bot_init import bot
from config import ADMIN_IDS, SESSIONS_DIR
from telegram_otp import session_manager
from utils import require_channel_membership

logging.basicConfig(level=logging.INFO)

def get_now_str():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

def format_size(size):
    return f"{size:,} bytes"

def format_datetime(ts):
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def parse_date_arg(arg):
    # Accept YYYYMMDD or YYYY-MM-DD
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

# /get +country_code [date]
@bot.message_handler(commands=['get'])
@require_channel_membership
def handle_get_country_sessions(message):
    try:
        logging.info(f"/get command triggered by user {message.from_user.id} with text: {message.text}")
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            bot.reply_to(message, "❌ You are not authorized to use this command.")
            return
        args = message.text.split()
        if len(args) < 2 or not args[1].startswith('+'):
            bot.reply_to(message, "Usage: /get +country_code [YYYYMMDD]\nExample: /get +1 20250712")
            return
        country_code = args[1]
        date_str = parse_date_arg(args[2]) if len(args) > 2 else None
        sessions = session_manager.list_country_sessions(country_code)
        logging.info(f"Sessions found for {country_code}: {sessions}")
        if not sessions or country_code not in sessions or not sessions[country_code]:
            bot.reply_to(message, f"❌ No sessions found for {country_code}")
            return
        filtered_sessions = [s for s in sessions[country_code] if session_matches_date(s, date_str)]
        if not filtered_sessions:
            bot.reply_to(message, f"❌ No sessions found for {country_code} on {date_str if date_str else 'any date'}.")
            return
        file_count = len(filtered_sessions)
        total_size = sum(session.get('size', 0) for session in filtered_sessions)
        created = min((session.get('created', 0) for session in filtered_sessions if session.get('created')), default=None)
        created_str = format_datetime(created) if created else get_now_str()
        zip_name = f"sessions_{country_code}_{get_now_str()}.zip"
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zipf:
                for session in filtered_sessions:
                    path = session['session_path']
                    phone = session.get('phone_number') or os.path.splitext(os.path.basename(path))[0]
                    if os.path.exists(path):
                        arcname = os.path.join(country_code.lstrip('+'), f"{phone}.session")
                        zipf.write(path, arcname)
            tmp_zip_path = tmp_zip.name
        summary = (
            f"📦 Session Files for {country_code}{' on ' + date_str if date_str else ''}\n\n"
            f"📁 Files: {file_count}\n"
            f"💾 Size: {format_size(total_size)}\n"
            f"📅 Created: {created_str}\n\n"
            f"✅ All session files for {country_code}{' on ' + date_str if date_str else ''} have been downloaded."
        )
        bot.send_message(message.chat.id, summary)
        with open(tmp_zip_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=zip_name, visible_file_name=zip_name)
        os.unlink(tmp_zip_path)
    except Exception as e:
        logging.exception("Error in /get command handler:")
        bot.reply_to(message, f"❌ Internal error: {e}")

# /getall [country_code] [date]
@bot.message_handler(commands=['getall'])
@require_channel_membership
def handle_get_all_sessions(message):
    try:
        logging.info(f"/getall command triggered by user {message.from_user.id} with text: {message.text}")
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            bot.reply_to(message, "❌ You are not authorized to use this command.")
            return
        args = message.text.split()
        country_code = args[1] if len(args) > 1 and args[1].startswith('+') else None
        date_str = parse_date_arg(args[2]) if len(args) > 2 else (parse_date_arg(args[1]) if len(args) > 1 and not args[1].startswith('+') else None)
        sessions = session_manager.list_country_sessions(country_code)
        all_sessions = []
        for country, sess_list in sessions.items():
            all_sessions.extend([s for s in sess_list if session_matches_date(s, date_str)])
        file_count = len(all_sessions)
        total_size = sum(session.get('size', 0) for session in all_sessions)
        created = min((session.get('created', 0) for session in all_sessions if session.get('created')), default=None)
        created_str = format_datetime(created) if created else get_now_str()
        zip_name = f"all_sessions_{get_now_str()}.zip"
        found = file_count > 0
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zipf:
                for session in all_sessions:
                    country = session.get('country_code', '')
                    path = session['session_path']
                    phone = session.get('phone_number') or os.path.splitext(os.path.basename(path))[0]
                    if os.path.exists(path):
                        arcname = os.path.join(country.lstrip('+'), f"{phone}.session")
                        zipf.write(path, arcname)
            tmp_zip_path = tmp_zip.name
        if not found:
            bot.reply_to(message, f"❌ No sessions found{f' for {country_code}' if country_code else ''}{f' on {date_str}' if date_str else ''}.")
            os.unlink(tmp_zip_path)
            return
        summary = (
            f"📦 All Session Files{f' for {country_code}' if country_code else ''}{f' on {date_str}' if date_str else ''}\n\n"
            f"📁 Files: {file_count}\n"
            f"💾 Size: {format_size(total_size)}\n"
            f"📅 Created: {created_str}\n\n"
            f"✅ All session files{f' for {country_code}' if country_code else ''}{f' on {date_str}' if date_str else ''} have been downloaded."
        )
        bot.send_message(message.chat.id, summary)
        with open(tmp_zip_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=zip_name, visible_file_name=zip_name)
        os.unlink(tmp_zip_path)
    except Exception as e:
        logging.exception("Error in /getall command handler:")
        bot.reply_to(message, f"❌ Internal error: {e}")

# /getinfo +country_code [date]
@bot.message_handler(commands=['getinfo'])
@require_channel_membership
def handle_getinfo_country_sessions(message):
    try:
        logging.info(f"/getinfo command triggered by user {message.from_user.id} with text: {message.text}")
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            bot.reply_to(message, "❌ You are not authorized to use this command.")
            return
        args = message.text.split()
        if len(args) < 2 or not args[1].startswith('+'):
            bot.reply_to(message, "Usage: /getinfo +country_code [YYYYMMDD]\nExample: /getinfo +1 20250712")
            return
        country_code = args[1]
        date_str = parse_date_arg(args[2]) if len(args) > 2 else None
        sessions = session_manager.list_country_sessions(country_code)
        logging.info(f"Sessions found for {country_code}: {sessions}")
        if not sessions or country_code not in sessions or not sessions[country_code]:
            bot.reply_to(message, f"❌ No sessions found for {country_code}")
            return
        filtered_sessions = [s for s in sessions[country_code] if session_matches_date(s, date_str)]
        if not filtered_sessions:
            bot.reply_to(message, f"❌ No sessions found for {country_code} on {date_str if date_str else 'any date'}.")
            return
        file_count = len(filtered_sessions)
        total_size = sum(session.get('size', 0) for session in filtered_sessions)
        created = min((session.get('created', 0) for session in filtered_sessions if session.get('created')), default=None)
        created_str = format_datetime(created) if created else get_now_str()
        zip_name = f"all_sessions_{get_now_str()}.json"
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w+b') as tmp_json:
            info_list = []
            for session in filtered_sessions:
                info = {
                    'phone_number': session.get('phone_number'),
                    'size': session.get('size'),
                    'modified': session.get('modified'),
                    'created': session.get('created'),
                    'session_path': session.get('session_path')
                }
                info_list.append(info)
            tmp_json.write(json.dumps(info_list, indent=2).encode('utf-8'))
            tmp_json_path = tmp_json.name
        summary = (
            f"📦 Session Info for {country_code}{' on ' + date_str if date_str else ''}\n\n"
            f"📁 Files: {file_count}\n"
            f"💾 Size: {format_size(total_size)}\n"
            f"📅 Created: {created_str}\n\n"
            f"✅ All session info for {country_code}{' on ' + date_str if date_str else ''} have been downloaded."
        )
        bot.send_message(message.chat.id, summary)
        with open(tmp_json_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=zip_name, visible_file_name=zip_name)
        os.unlink(tmp_json_path)
    except Exception as e:
        logging.exception("Error in /getinfo command handler:")
        bot.reply_to(message, f"❌ Internal error: {e}")