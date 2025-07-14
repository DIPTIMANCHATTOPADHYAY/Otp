from datetime import datetime
from db import get_user, update_user
from bot_init import bot
from config import REQUESTED_CHANNEL

def require_channel_membership(func):
    def wrapped(message, *args, **kwargs):
        user_id = message.from_user.id
        
        if not get_user(user_id):
            update_user(user_id, {
                'name': message.from_user.first_name,
                'username': message.from_user.username,
                'balance': 0.0,
                'sent_accounts': 0,
                'registered_at': datetime.utcnow()
            })
        
        try:
            chat_member = bot.get_chat_member(REQUESTED_CHANNEL, user_id)
            if chat_member.status not in ['member', 'administrator', 'creator']:
                bot.send_message(
                    message.chat.id,
                    "⚠️ *Channel Verification Required*\n\n"
                    "To use this bot, you must join our channel first:\n"
                    f"https://t.me/{REQUESTED_CHANNEL.lstrip('@')}\n\n"
                    "After joining, send /start again.",
                    parse_mode="Markdown"
                )
                return
        except Exception as e:
            print(f"Error checking channel membership: {e}")
            bot.send_message(
                message.chat.id,
                "⚠️ *Channel Verification Required*\n\n"
                "To use this bot, you must join our channel first:\n"
                f"https://t.me/{REQUESTED_CHANNEL.lstrip('@')}\n\n"
                "After joining, send /start again.",
                parse_mode="Markdown"
            )
            return
        
        return func(message, *args, **kwargs)
    return wrapped