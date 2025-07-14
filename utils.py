from datetime import datetime
from db import get_user, update_user
from bot_init import bot
from config import REQUESTED_CHANNEL

# Translation dictionary for all user-facing messages
TRANSLATIONS = {
    'channel_verification': {
        'English': "⚠️ *Channel Verification Required*\n\nTo use this bot, you must join our channel first:\n{url}\n\nAfter joining, send /start again.",
        'Arabic': "⚠️ *مطلوب التحقق من القناة*\n\nلاستخدام هذا البوت، يجب عليك الانضمام إلى قناتنا أولاً:\n{url}\n\nبعد الانضمام، أرسل /start مرة أخرى.",
        'Chinese': "⚠️ *需要频道验证*\n\n要使用此机器人，您必须先加入我们的频道：\n{url}\n\n加入后，请再次发送 /start。"
    }
}

def get_user_language(user_id):
    user = get_user(user_id)
    if user and user.get('language'):
        return user['language']
    return 'English'

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
                lang = get_user_language(user_id)
                url = f"https://t.me/{REQUESTED_CHANNEL.lstrip('@')}"
                text = TRANSLATIONS['channel_verification'][lang].format(url=url)
                bot.send_message(
                    message.chat.id,
                    text,
                    parse_mode="Markdown"
                )
                return
        except Exception as e:
            print(f"Error checking channel membership: {e}")
            lang = get_user_language(user_id)
            url = f"https://t.me/{REQUESTED_CHANNEL.lstrip('@')}"
            text = TRANSLATIONS['channel_verification'][lang].format(url=url)
            bot.send_message(
                message.chat.id,
                text,
                parse_mode="Markdown"
            )
            return
        
        return func(message, *args, **kwargs)
    return wrapped