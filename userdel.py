from bot_init import bot
from config import ADMIN_IDS
from db import db
from utils import require_channel_membership

@bot.message_handler(commands=['userdel'])
@require_channel_membership
def handle_userdel(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return

    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /userdel <telegram_user_id>")
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "User ID must be a number.")
        return

    user_result = db.users.delete_one({"user_id": target_id})
    withdraw_result = db.withdrawals.delete_many({"user_id": target_id})
    pending_result = db.pending_numbers.delete_many({"user_id": target_id})

    msg = (
        f"🗑️ User `{target_id}` deleted.\n"
        f"• Users: {user_result.deleted_count}\n"
        f"• Withdrawals: {withdraw_result.deleted_count}\n"
        f"• Pending Numbers: {pending_result.deleted_count}\n"
        "If this user starts again, a new account will be created."
    )
    bot.reply_to(message, msg, parse_mode="Markdown")
