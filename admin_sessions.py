import os
import zipfile
import tempfile
import json
from bot_init import bot
from config import ADMIN_IDS, SESSIONS_DIR
from telegram_otp import session_manager
from utils import require_channel_membership

# /get +country_code - Download all sessions for a country in zip file
@bot.message_handler(commands=['get'])
@require_channel_membership
def handle_get_country_sessions(message):
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
    if not sessions or country_code not in sessions or not sessions[country_code]:
        bot.reply_to(message, f"❌ No sessions found for {country_code}")
        return
    # Create zip file
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
        with zipfile.ZipFile(tmp_zip, 'w') as zipf:
            for session in sessions[country_code]:
                path = session['session_path']
                phone = session.get('phone_number') or os.path.splitext(os.path.basename(path))[0]
                if os.path.exists(path):
                    arcname = os.path.join(country_code.lstrip('+'), f"{phone}.session")
                    zipf.write(path, arcname)
        tmp_zip_path = tmp_zip.name
    with open(tmp_zip_path, 'rb') as f:
        bot.send_document(message.chat.id, f, caption=f"Sessions for {country_code}")
    os.unlink(tmp_zip_path)

# /getall - Download all sessions from all countries in zip file
@bot.message_handler(commands=['getall'])
@require_channel_membership
def handle_get_all_sessions(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    sessions = session_manager.list_country_sessions()
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
    with open(tmp_zip_path, 'rb') as f:
        bot.send_document(message.chat.id, f, caption="All sessions (all countries)")
    os.unlink(tmp_zip_path)

# /getinfo +country_code - Get detailed info about sessions for a country
@bot.message_handler(commands=['getinfo'])
@require_channel_membership
def handle_getinfo_country_sessions(message):
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
    if not sessions or country_code not in sessions or not sessions[country_code]:
        bot.reply_to(message, f"❌ No sessions found for {country_code}")
        return
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
    # Send as JSON file
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as tmp_json:
        json.dump(info_list, tmp_json, indent=2)
        tmp_json_path = tmp_json.name
    with open(tmp_json_path, 'rb') as f:
        bot.send_document(message.chat.id, f, caption=f"Session info for {country_code}")
    os.unlink(tmp_json_path)