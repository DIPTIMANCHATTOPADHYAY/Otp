from config import REQUESTED_CHANNEL
from bot_init import bot
from utils import require_channel_membership
from db import get_user, update_user

@bot.message_handler(commands=['start'])
@require_channel_membership
def handle_start(message):
    user_id = message.from_user.id
    user = get_user(user_id) or {}
    verify_msg_id = user.get("verify_msg_id")
    if verify_msg_id:
        try:
            bot.delete_message(message.chat.id, verify_msg_id)
        except Exception:
            pass
        update_user(user_id, {"verify_msg_id": None})
    text = (
            "🎉 *Welcome to TG VIP RECEIVER* 🎉\n\n"
            "📊 We're glad you're here! Please send your phone number starting with the country code.\n"
            "Example: +20xxxxxxxxxx\n"
        )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")