from bot_init import bot
from config import ADMIN_IDS
from db import (
    reject_withdrawals_by_user,
    reject_withdrawals_by_card,
    get_user
)
from utils import require_channel_membership
import re

def notify_user_rejection(user_id, withdrawals):
    """Send rejection notification to user"""
    total_amount = sum(w['amount'] for w in withdrawals)
    try:
        bot.send_message(
            user_id,
            f"❌ Your withdrawal request(s) totaling {total_amount}$ have been rejected.\n\n"
            "Reason: Admin rejected the request\n"
            "Contact support if you have questions.",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Could not notify user {user_id}: {str(e)}")

@bot.message_handler(commands=['rejectpayment'])
@require_channel_membership
def handle_reject_payment(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, 
            "Usage:\n"
            "/rejectpayment <user_id> [reason]\n"
            "/rejectpayment card:<card_name> [reason]\n"
            "Example: /rejectpayment 12345 Invalid card\n"
            "Example: /rejectpayment card:john_doe Verification failed")
        return

    target = parts[1].strip()
    reason = ' '.join(parts[2:]) if len(parts) > 2 else "No reason provided"

    # Check if rejecting by card
    if target.startswith("card:"):
        card_name = target[5:]  # Remove 'card:' prefix
        count, withdrawals = reject_withdrawals_by_card(card_name)
        if count > 0:
            # Notify each affected user
            user_notified = set()
            for w in withdrawals:
                if w['user_id'] not in user_notified:
                    notify_user_rejection(w['user_id'], [w for w in withdrawals if w['user_id'] == w['user_id']])
                    user_notified.add(w['user_id'])
            
            bot.reply_to(message, f"✅ Rejected {count} pending withdrawals for card: {card_name}")
        else:
            bot.reply_to(message, f"❌ No pending withdrawals found for card: {card_name}")
        return

    # Otherwise treat as user ID
    try:
        user_id = int(target)
        user = get_user(user_id)
        if not user:
            bot.reply_to(message, f"❌ User {user_id} not found")
            return

        count, withdrawals = reject_withdrawals_by_user(user_id)
        if count > 0:
            notify_user_rejection(user_id, withdrawals)
            bot.reply_to(message, f"✅ Rejected {count} pending withdrawals for user {user_id}")
        else:
            bot.reply_to(message, f"❌ No pending withdrawals found for user {user_id}")
    except ValueError:
        bot.reply_to(message, "❌ User ID must be a number or use card:<name> format")