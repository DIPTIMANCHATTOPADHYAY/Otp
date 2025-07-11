import os
import asyncio
import threading
from db import get_user, update_user, unmark_number_used, delete_pending_numbers
from utils import require_channel_membership
from bot_init import bot
from telegram_otp import session_manager
from config import SESSIONS_DIR

# Use the same async loop as otp.py
def run_async(coro):
    """Run async function in the background thread"""
    try:
        # Try to get the existing event loop from otp.py
        from otp import otp_loop
        future = asyncio.run_coroutine_threadsafe(coro, otp_loop)
        return future.result(timeout=10)  # 10 second timeout
    except Exception as e:
        print(f"Error running async in cancel: {e}")
        return False

@bot.message_handler(commands=['cancel'])
@require_channel_membership
def handle_cancel(message):
    try:
        user_id = message.from_user.id
        user = get_user(user_id) or {}
        
        if not user.get("pending_phone"):
            bot.reply_to(message, "❌ You have no pending phone verification to cancel.")
            return

        phone_number = user["pending_phone"]
        print(f"🗑️ Cancelling verification for {phone_number} (User: {user_id})")

        # 1. Remove number from used_numbers (so it can be used again)
        unmark_success = unmark_number_used(phone_number)
        if unmark_success:
            print(f"✅ Number {phone_number} unmarked (can be used again)")
        else:
            print(f"⚠️ Number {phone_number} was not marked as used or failed to unmark")

        # 2. Clean up session files from server
        session_path = os.path.join(SESSIONS_DIR, f"{phone_number}.session")
        temp_session_path = session_manager.user_states.get(user_id, {}).get("session_path")

        removed_files = 0
        for path in [session_path, temp_session_path]:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
                    removed_files += 1
                    print(f"✅ Removed session file: {path}")
            except Exception as e:
                print(f"Error removing session file {path}: {e}")

        # 3. Clean up the session manager state and disconnect client
        cleanup_success = run_async(session_manager.cleanup_session(user_id))
        
        # 4. Delete any pending numbers for this user
        deleted_pending = delete_pending_numbers(user_id)
        if deleted_pending > 0:
            print(f"✅ Deleted {deleted_pending} pending number records for user {user_id}")

        # 5. Update user in database (clear all verification data)
        update_success = update_user(user_id, {
            "pending_phone": None,
            "otp_msg_id": None,
            "country_code": None
        })

        if update_success:
            print(f"✅ User {user_id} verification data cleared")

        # Send confirmation message
        bot.reply_to(
            message, 
            f"✅ *Verification Cancelled*\n\n"
            f"📞 Number: `{phone_number}`\n"
            f"🔄 This number can now be used again\n"
            f"🗑️ All verification data cleared",
            parse_mode="Markdown"
        )
        
        print(f"✅ Successfully cancelled verification for {phone_number}")
        
    except Exception as e:
        bot.reply_to(message, "⚠️ An error occurred while cancelling. Please try again.")
        print(f"❌ Cancel error for user {user_id}: {e}")