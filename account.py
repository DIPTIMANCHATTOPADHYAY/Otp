from datetime import datetime
from utils import require_channel_membership
from db import get_user
from bot_init import bot
import telebot

@bot.message_handler(commands=['account'])
@require_channel_membership
def handle_account(message):
    user_id = message.from_user.id
    user = get_user(user_id) or {}
    name = user.get('name', message.from_user.first_name)
    sent_accounts = user.get('sent_accounts', 0)
    balance = user.get('balance', 0.0)
    registered_at = user.get('registered_at', datetime.utcnow())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    text = (
        "🌟 *Account Information* 🌟\n\n"
        f"👤 *Name*: {name}\n"
        f"🆔 *User ID*: {user_id}\n"
        f"📅 *Registered*: {registered_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"📊 Number of sent accounts: {sent_accounts}\n"
        f"💰 Balance that can be settled: {balance} $\n\n"
        f"⏰ *Time Now*: {now}\n\n"
        f"Withdraw: /withdraw\n"
        f"Withdraw history: /withdrawhistory"
    )
    
    # Send message with clickable /withdraw command
    bot.send_message(message.chat.id, text, parse_mode="Markdown")