import os
import zipfile
import tempfile
import json
import datetime
import logging
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

# /get +country_code - Download all sessions for a country in zip file
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
            bot.reply_to(message, "Usage: /get +country_code\nExample: /get +1")
            return
        country_code = args[1]
        sessions = session_manager.list_country_sessions(country_code)
        logging.info(f"Sessions found for {country_code}: {sessions}")
        if not sessions or country_code not in sessions or not sessions[country_code]:
            bot.reply_to(message, f"❌ No sessions found for {country_code}")
            return
        # Gather stats
        file_count = len(sessions[country_code])
        total_size = sum(session.get('size', 0) for session in sessions[country_code])
        created = min((session.get('created', 0) for session in sessions[country_code] if session.get('created')), default=None)
        created_str = format_datetime(created) if created else get_now_str()
        # Create zip file with requested name
        zip_name = f"sessions_{country_code}_{get_now_str()}.zip"
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zipf:
                for session in sessions[country_code]:
                    path = session['session_path']
                    phone = session.get('phone_number') or os.path.splitext(os.path.basename(path))[0]
                    if os.path.exists(path):
                        arcname = os.path.join(country_code.lstrip('+'), f"{phone}.session")
                        zipf.write(path, arcname)
            tmp_zip_path = tmp_zip.name
        summary = (
            f"\ud83d\udce6 Session Files for {country_code}\n\n"
            f"\ud83d\udcc1 Files: {file_count}\n"
            f"\ud83d\udce4 Size: {format_size(total_size)}\n"
            f"\ud83d\udcc5 Created: {created_str}\n\n"
            f"\u2705 All session files for {country_code} have been downloaded."
        )
        bot.send_message(message.chat.id, summary)
        with open(tmp_zip_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=zip_name, visible_file_name=zip_name)
        os.unlink(tmp_zip_path)
    except Exception as e:
        logging.exception("Error in /get command handler:")
        bot.reply_to(message, f"❌ Internal error: {e}")

# /getall - Download all sessions from all countries in zip file
@bot.message_handler(commands=['getall'])
@require_channel_membership
def handle_get_all_sessions(message):
    try:
        logging.info(f"/getall command triggered by user {message.from_user.id} with text: {message.text}")
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            bot.reply_to(message, "❌ You are not authorized to use this command.")
            return
        sessions = session_manager.list_country_sessions()
        all_sessions = [s for sess_list in sessions.values() for s in sess_list]
        file_count = len(all_sessions)
        total_size = sum(session.get('size', 0) for session in all_sessions)
        created = min((session.get('created', 0) for session in all_sessions if session.get('created')), default=None)
        created_str = format_datetime(created) if created else get_now_str()
        zip_name = f"all_sessions_{get_now_str()}.zip"
        found = False
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zipf:
                for country, sess_list in sessions.items():
                    for session in sess_list:
                        path = session['session_path']
                        phone = session.get('phone_number') or os.path.splitext(os.path.basename(path))[0]
                        if os.path.exists(path):
                            arcname = os.path.join(country.lstrip('+'), f"{phone}.session")
                            zipf.write(path, arcname)
                            found = True
            tmp_zip_path = tmp_zip.name
        if not found:
            bot.reply_to(message, "❌ No sessions found in any country.")
            os.unlink(tmp_zip_path)
            return
        summary = (
            f"\ud83d\udce6 All Session Files\n\n"
            f"\ud83d\udcc1 Files: {file_count}\n"
            f"\ud83d\udce4 Size: {format_size(total_size)}\n"
            f"\ud83d\udcc5 Created: {created_str}\n\n"
            f"\u2705 All session files have been downloaded."
        )
        bot.send_message(message.chat.id, summary)
        with open(tmp_zip_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=zip_name, visible_file_name=zip_name)
        os.unlink(tmp_zip_path)
    except Exception as e:
        logging.exception("Error in /getall command handler:")
        bot.reply_to(message, f"❌ Internal error: {e}")

# /getinfo +country_code - Get detailed info about sessions for a country
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
            bot.reply_to(message, "Usage: /getinfo +country_code\nExample: /getinfo +1")
            return
        country_code = args[1]
        sessions = session_manager.list_country_sessions(country_code)
        logging.info(f"Sessions found for {country_code}: {sessions}")
        if not sessions or country_code not in sessions or not sessions[country_code]:
            bot.reply_to(message, f"❌ No sessions found for {country_code}")
            return
        file_count = len(sessions[country_code])
        total_size = sum(session.get('size', 0) for session in sessions[country_code])
        created = min((session.get('created', 0) for session in sessions[country_code] if session.get('created')), default=None)
        created_str = format_datetime(created) if created else get_now_str()
        zip_name = f"all_sessions_{get_now_str()}.json"
        # Create a zip with one JSON file per session, named as country_code/phone_number.json
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w+b') as tmp_json:
            info_list = []
            for session in sessions[country_code]:
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
            f"\ud83d\udce6 Session Info for {country_code}\n\n"
            f"\ud83d\udcc1 Files: {file_count}\n"
            f"\ud83d\udce4 Size: {format_size(total_size)}\n"
            f"\ud83d\udcc5 Created: {created_str}\n\n"
            f"\u2705 All session info for {country_code} has been downloaded."
        )
        bot.send_message(message.chat.id, summary)
        with open(tmp_json_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=zip_name, visible_file_name=zip_name)
        os.unlink(tmp_json_path)
    except Exception as e:
        logging.exception("Error in /getinfo command handler:")
        bot.reply_to(message, f"❌ Internal error: {e}")