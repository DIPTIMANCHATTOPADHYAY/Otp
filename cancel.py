import os
from db import get_user, update_user
from utils import require_channel_membership
from bot_init import bot
from telegram_otp import session_manager
from config import SESSIONS_DIR

@bot.message_handler(commands=['cancel'])
@require_channel_membership
def handle_cancel(message):
    try:
        user_id = message.from_user.id
        user = get_user(user_id) or {}
        
        if not user.get("pending_phone"):
            bot.reply_to(message, "❌ You have no pending phone verification to cancel.")
            return

        # Clean up the session file from server
        phone_number = user["pending_phone"]
        session_path = os.path.join(SESSIONS_DIR, f"{phone_number}.session")
        temp_session_path = session_manager.user_states.get(user_id, {}).get("session_path")

        # Remove both final and temporary session files if they exist
        for path in [session_path, temp_session_path]:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Error removing session file {path}: {e}")

        # Clean up the session manager state
        run_async(session_manager.cleanup_session(user_id))

        # Update user in database
        update_user(user_id, {
            "pending_phone": None,
            "otp_msg_id": None,
            "country_code": None
        })

        bot.reply_to(message, "✅ Your pending phone verification has been cancelled and all data cleared.")
        
    except Exception as e:
        bot.reply_to(message, "⚠️ An error occurred while cancelling. Please try again.")
        print(f"Cancel error for user {user_id}: {e}")