from db import get_withdrawals
from utils import require_channel_membership
from bot_init import bot

@bot.message_handler(commands=['withdrawhistory'])
@require_channel_membership
def handle_withdrawhistory(message):
    user_id = message.from_user.id
    withdrawals = get_withdrawals(user_id)
    text = "🏛️ *Your withdrawals requests:*\n"
    if not withdrawals:
        text += "No withdrawals yet."
    else:
        for w in withdrawals:
            text += f"- {w['amount']}$ | {w['status']} | {w['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
