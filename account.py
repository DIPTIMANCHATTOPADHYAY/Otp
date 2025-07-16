from datetime import datetime
from utils import require_channel_membership
from db import get_user
from bot_init import bot
from translations import get_text
import telebot

# Import withdrawal state to check for active withdrawals
from withdraw import user_withdraw_state, clear_withdraw_state

@bot.message_handler(commands=['account'])
@require_channel_membership
def handle_account(message):
    user_id = message.from_user.id
    
    # Check if user is in withdrawal state and cancel it
    if user_id in user_withdraw_state:
        clear_withdraw_state(user_id)
        user = get_user(user_id) or {}
        user_language = user.get('language', 'English')
        bot.send_message(message.chat.id, get_text('withdrawal_cancelled', user_language))
    
    user = get_user(user_id) or {}
    name = user.get('name', message.from_user.first_name)
    sent_accounts = user.get('sent_accounts', 0)
    balance = user.get('balance', 0.0)
    registered_at = user.get('registered_at', datetime.utcnow())
    lang = user.get('language', 'English')
    registered_date = registered_at.strftime('%Y-%m-%d %H:%M:%S')

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(
        text={
            'English': 'Withdraw',
            'Arabic': 'سحب',
            'Chinese': '提现'
        }.get(lang, 'Withdraw'),
        callback_data='account_withdraw')
    )

    # Clean account info without device status
    account_text = get_text(
        'account_info', lang, 
        name=name, 
        balance=balance, 
        sent_accounts=sent_accounts, 
        registered_date=registered_date
    )

    bot.send_message(
        message.chat.id, 
        account_text,
        parse_mode="Markdown", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == 'account_withdraw')
def handle_account_withdraw_callback(call):
    # Simulate /withdraw command trigger
    from withdraw import handle_withdraw
    class DummyMessage:
        def __init__(self, call):
            self.from_user = call.from_user
            self.chat = call.message.chat
            self.message_id = call.message.message_id
            self.text = '/withdraw'
    handle_withdraw(DummyMessage(call))
    bot.answer_callback_query(call.id)