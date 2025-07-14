from config import REQUESTED_CHANNEL
from bot_init import bot
from utils import require_channel_membership
from db import get_user, update_user
import telebot.types

@bot.message_handler(commands=['start'])
@require_channel_membership
def handle_start(message):
    user_id = message.from_user.id
    user = get_user(user_id) or {}
    if not user.get('language'):
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add('English', 'Arabic', 'Chinese')
        bot.send_message(
            message.chat.id,
            "Please select your language:\nيرجى اختيار لغتك:\n请选择你的语言:",
            reply_markup=markup
        )
        update_user(user_id, {"language_selecting": True})
        return
    verify_msg_id = user.get("verify_msg_id")
    if verify_msg_id:
        try:
            bot.delete_message(message.chat.id, verify_msg_id)
        except Exception:
            pass
        update_user(user_id, {"verify_msg_id": None})
    lang = user.get('language', 'English')
    texts = {
        'English': (
            "🎉 *Welcome to TG VIP RECEIVER* 🎉\n\n"
            "📊 We're glad you're here! Please send your phone number starting with the country code.\n"
            "Example: +20xxxxxxxxxx\n"
        ),
        'Arabic': (
            "🎉 *مرحبًا بك في TG VIP RECEIVER* 🎉\n\n"
            "📊 نحن سعداء بوجودك هنا! يرجى إرسال رقم هاتفك بدءًا برمز الدولة.\n"
            "مثال: +20xxxxxxxxxx\n"
        ),
        'Chinese': (
            "🎉 *欢迎来到 TG VIP RECEIVER* 🎉\n\n"
            "📊 很高兴见到你！请发送以国家代码开头的电话号码。\n"
            "例如: +20xxxxxxxxxx\n"
        )
    }
    text = texts.get(lang, texts['English'])
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text in ['English', 'Arabic', 'Chinese'])
def handle_language_select(message):
    user_id = message.from_user.id
    lang = message.text
    update_user(user_id, {"language": lang, "language_selecting": False})
    # Remove keyboard
    markup = telebot.types.ReplyKeyboardRemove()
    texts = {
        'English': "Language set to English. Please send /start again.",
        'Arabic': "تم تعيين اللغة إلى العربية. يرجى إرسال /start مرة أخرى.",
        'Chinese': "语言已设置为中文。请再次发送 /start。"
    }
    bot.send_message(message.chat.id, texts[lang], reply_markup=markup)