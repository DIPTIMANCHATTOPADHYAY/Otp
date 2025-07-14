from bot_init import bot
from config import ADMIN_IDS
from db import (
    get_pending_withdrawals_by_card,
    approve_withdrawals_by_card,
    get_user,
    update_user,
)
from utils import require_channel_membership

@bot.message_handler(commands=['paycard'])
@require_channel_membership
def handle_paycard(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /paycard <card_name>")
        return

    card_name = parts[1].strip()
    pending_withdrawals = get_pending_withdrawals_by_card(card_name)
    if not pending_withdrawals:
        bot.reply_to(message, f"❌ No pending withdrawals found for card '{card_name}'.")
        return

    # Process each withdrawal
    for w in pending_withdrawals:
        user_id = w["user_id"]
        amount = w["amount"]
        user = get_user(user_id) or {}
        current_balance = user.get("balance", 0.0)
        # Deduct the amount (set to zero or subtract, as per your logic)
        new_balance = max(0.0, current_balance - amount)
        update_user(user_id, {"balance": new_balance})
        # Notify the user
        try:
            bot.send_message(user_id, f"✅ Your withdrawal of {amount}$ with leader card '{card_name}' has been approved and completed. Thank you!")
        except Exception:
            pass  # User may have blocked the bot, ignore errors

    # Approve all in the database
    approve_withdrawals_by_card(card_name)

    bot.reply_to(message, f"✅ All pending withdrawals for card '{card_name}' have been approved and users notified.")
