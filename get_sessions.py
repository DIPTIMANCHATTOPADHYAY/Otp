import os
import zipfile
import tempfile
import shutil
from datetime import datetime
from bot_init import bot
from config import ADMIN_IDS, SESSIONS_DIR
from telegram_otp import session_manager
from utils import require_channel_membership
import re

def is_admin(user_id):
    return user_id in ADMIN_IDS

@bot.message_handler(commands=['get'])
@require_channel_membership
def handle_get_sessions(message):
    """Download all session files for a specific country code in a zip file"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        # Parse the command: /get +country_code
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) != 2:
            bot.reply_to(
                message,
                "❌ **Usage:** `/get +country_code`\n\n"
                "**Examples:**\n"
                "• `/get +1` - Download all US/Canada sessions\n"
                "• `/get +44` - Download all UK sessions\n"
                "• `/get +91` - Download all India sessions\n"
                "• `/get +86` - Download all China sessions",
                parse_mode="Markdown"
            )
            return
        
        country_code = parts[1].strip()
        
        # Validate country code format
        if not re.match(r'^\+\d{1,4}$', country_code):
            bot.reply_to(
                message,
                "❌ **Invalid country code format!**\n\n"
                "Use format like: `+1`, `+44`, `+91`, `+86`",
                parse_mode="Markdown"
            )
            return
        
        # Check if country directory exists
        country_dir = os.path.join(SESSIONS_DIR, country_code)
        if not os.path.exists(country_dir):
            bot.reply_to(
                message,
                f"📁 **No sessions found for {country_code}**\n\n"
                "This country has no session files yet.",
                parse_mode="Markdown"
            )
            return
        
        # Get all session files in the country directory
        session_files = []
        for file in os.listdir(country_dir):
            if file.endswith('.session'):
                session_files.append(os.path.join(country_dir, file))
        
        if not session_files:
            bot.reply_to(
                message,
                f"📁 **No session files found for {country_code}**\n\n"
                "The country directory exists but contains no .session files.",
                parse_mode="Markdown"
            )
            return
        
        # Create a temporary directory for the zip file
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_filename = f"sessions_{country_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            # Create the zip file
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for session_file in session_files:
                    # Get just the filename (without path)
                    filename = os.path.basename(session_file)
                    
                    # Add file to zip with country code as subfolder
                    zipf.write(session_file, f"{country_code}/{filename}")
            
            # Check zip file size
            zip_size = os.path.getsize(zip_path)
            
            # Send the zip file
            with open(zip_path, 'rb') as zip_file:
                bot.send_document(
                    chat_id=user_id,
                    document=zip_file,
                    caption=f"📦 **Session Files for {country_code}**\n\n"
                           f"📁 **Files:** {len(session_files)}\n"
                           f"💾 **Size:** {zip_size:,} bytes\n"
                           f"📅 **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                           f"✅ All session files for {country_code} have been downloaded.",
                    parse_mode="Markdown"
                )
            
            print(f"✅ Admin {user_id} downloaded {len(session_files)} sessions for {country_code}")
            
    except Exception as e:
        error_msg = f"❌ **Error downloading sessions:** {str(e)}"
        bot.reply_to(message, error_msg, parse_mode="Markdown")
        print(f"❌ Error in get_sessions for user {user_id}: {e}")

@bot.message_handler(commands=['getall'])
@require_channel_membership
def handle_get_all_sessions(message):
    """Download all session files from all countries in a zip file"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        # Get all sessions by country
        sessions_by_country = session_manager.list_country_sessions()
        
        if not sessions_by_country:
            bot.reply_to(message, "📁 **No sessions found**\n\nNo session files exist in any country directory.", parse_mode="Markdown")
            return
        
        total_files = sum(len(sessions) for sessions in sessions_by_country.values())
        
        # Create a temporary directory for the zip file
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_filename = f"all_sessions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            # Create the zip file
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for country_code, sessions in sessions_by_country.items():
                    for session in sessions:
                        session_path = session['session_path']
                        if os.path.exists(session_path):
                            # Get just the filename (without path)
                            filename = os.path.basename(session_path)
                            
                            # Add file to zip with country code as subfolder
                            zipf.write(session_path, f"{country_code}/{filename}")
            
            # Check zip file size
            zip_size = os.path.getsize(zip_path)
            
            # Create summary
            summary = f"📦 **All Session Files**\n\n"
            summary += f"🌍 **Countries:** {len(sessions_by_country)}\n"
            summary += f"📁 **Total Files:** {total_files}\n"
            summary += f"💾 **Size:** {zip_size:,} bytes\n"
            summary += f"📅 **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Add country breakdown
            summary += "**Country Breakdown:**\n"
            for country_code, sessions in sessions_by_country.items():
                summary += f"• {country_code}: {len(sessions)} sessions\n"
            
            # Send the zip file
            with open(zip_path, 'rb') as zip_file:
                bot.send_document(
                    chat_id=user_id,
                    document=zip_file,
                    caption=summary,
                    parse_mode="Markdown"
                )
            
            print(f"✅ Admin {user_id} downloaded all sessions ({total_files} files from {len(sessions_by_country)} countries)")
            
    except Exception as e:
        error_msg = f"❌ **Error downloading all sessions:** {str(e)}"
        bot.reply_to(message, error_msg, parse_mode="Markdown")
        print(f"❌ Error in get_all_sessions for user {user_id}: {e}")

@bot.message_handler(commands=['getinfo'])
@require_channel_membership
def handle_get_session_info(message):
    """Get detailed information about sessions for a specific country"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        # Parse the command: /getinfo +country_code
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) != 2:
            bot.reply_to(
                message,
                "❌ **Usage:** `/getinfo +country_code`\n\n"
                "**Examples:**\n"
                "• `/getinfo +1` - Get info about US/Canada sessions\n"
                "• `/getinfo +44` - Get info about UK sessions",
                parse_mode="Markdown"
            )
            return
        
        country_code = parts[1].strip()
        
        # Validate country code format
        if not re.match(r'^\+\d{1,4}$', country_code):
            bot.reply_to(
                message,
                "❌ **Invalid country code format!**\n\n"
                "Use format like: `+1`, `+44`, `+91`, `+86`",
                parse_mode="Markdown"
            )
            return
        
        # Get sessions for this country
        sessions_by_country = session_manager.list_country_sessions(country_code)
        
        if country_code not in sessions_by_country or not sessions_by_country[country_code]:
            bot.reply_to(
                message,
                f"📁 **No sessions found for {country_code}**\n\n"
                "This country has no session files.",
                parse_mode="Markdown"
            )
            return
        
        sessions = sessions_by_country[country_code]
        
        # Calculate statistics
        total_size = sum(session.get('size', 0) for session in sessions)
        avg_size = total_size / len(sessions) if sessions else 0
        
        # Get file details
        file_details = []
        for session in sessions:
            phone = session['phone_number']
            size = session.get('size', 0)
            modified = session.get('modified', 0)
            
            if modified:
                mod_time = datetime.fromtimestamp(modified).strftime('%Y-%m-%d %H:%M')
            else:
                mod_time = "Unknown"
            
            file_details.append(f"• `{phone}` ({size:,} bytes, {mod_time})")
        
        # Create response
        response = f"📊 **Session Information for {country_code}**\n\n"
        response += f"📁 **Total Files:** {len(sessions)}\n"
        response += f"💾 **Total Size:** {total_size:,} bytes\n"
        response += f"📊 **Average Size:** {avg_size:.0f} bytes\n\n"
        response += "**Files:**\n"
        response += "\n".join(file_details[:10])  # Show first 10 files
        
        if len(file_details) > 10:
            response += f"\n... and {len(file_details) - 10} more files"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        error_msg = f"❌ **Error getting session info:** {str(e)}"
        bot.reply_to(message, error_msg, parse_mode="Markdown")
        print(f"❌ Error in get_session_info for user {user_id}: {e}")