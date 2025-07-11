from bot_init import bot
from config import ADMIN_IDS
from db import get_card_withdrawal_stats
from utils import require_channel_membership

@bot.message_handler(commands=['cardw'])
@require_channel_membership
def handle_cardw(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /cardw <card_name>")
        return

    card_name = parts[1].strip()
    stats = get_card_withdrawal_stats(card_name)
    if stats["pending"] == 0 and stats["approved"] == 0:
        bot.reply_to(message, f"❌ No withdrawals found for card '{card_name}'.")
        return

    text = (
        f"💳 *Leader Card Withdrawal Stats*\n"
        f"Card: `{card_name}`\n\n"
        f"🟡 Pending withdrawals: {stats['pending']} (Total pending: {stats['total_pending_balance']}$)\n"
        f"🟢 Approved withdrawals: {stats['approved']} (Total approved: {stats['total_approved_balance']}$)\n"
    )
    bot.reply_to(message, text, parse_mode="Markdown")
