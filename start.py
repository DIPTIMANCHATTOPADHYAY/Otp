from config import REQUESTED_CHANNEL
from bot_init import bot
from utils import require_channel_membership
from db import get_user, update_user
from translations import get_text
import telebot.types

# Import withdrawal state to check for active withdrawals
from withdraw import user_withdraw_state, clear_withdraw_state

@bot.message_handler(commands=['start'])
@require_channel_membership
def handle_start(message):
    user_id = message.from_user.id
    
    # Check if user is in withdrawal state and cancel it
    if user_id in user_withdraw_state:
        clear_withdraw_state(user_id)
        user = get_user(user_id) or {}
        user_language = user.get('language', 'English')
        bot.send_message(message.chat.id, get_text('withdrawal_cancelled', user_language))
    
    user = get_user(user_id) or {}
    if not user.get('language'):
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add('English', 'Arabic', 'Chinese')
        bot.send_message(
            message.chat.id,
            get_text('language_selection'),
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
    bot.send_message(message.chat.id, get_text('welcome_message', lang), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text in ['English', 'Arabic', 'Chinese'])
def handle_language_select(message):
    user_id = message.from_user.id
    lang = message.text
    update_user(user_id, {"language": lang, "language_selecting": False})
    # Remove keyboard
    markup = telebot.types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, get_text('language_changed', lang), reply_markup=markup)

@bot.message_handler(commands=['language'])
def handle_language_command(message):
    user_id = message.from_user.id
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('English', 'Arabic', 'Chinese')
    bot.send_message(
        message.chat.id,
        get_text('language_selection'),
        reply_markup=markup
    )
    update_user(user_id, {"language_selecting": True})