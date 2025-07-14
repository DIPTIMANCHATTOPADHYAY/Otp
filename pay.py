from bot_init import bot
from config import ADMIN_IDS
from db import approve_withdrawal, get_user, update_user, get_pending_withdrawal
from utils import require_channel_membership

@bot.message_handler(commands=['pay'])
@require_channel_membership
def handle_pay(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /pay <user_id>")
        return
    try:
        user_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "User ID must be a number.")
        return

    # Get the pending withdrawal and amount
    withdrawal = get_pending_withdrawal(user_id)
    if not withdrawal:
        bot.reply_to(message, "❌ No pending withdrawal found for that user.")
        return

    amount = withdrawal.get("amount", 0.0)
    # Deduct the amount from the user's balance
    user = get_user(user_id) or {}
    current_balance = user.get("balance", 0.0)
    new_balance = max(0.0, current_balance - amount)
    update_user(user_id, {"balance": new_balance})

    modified = approve_withdrawal(user_id)
    lang = user.get('language', 'English')
    if modified:
        texts = {
            'English': "✅ Your withdrawal has been approved and completed. Thank you!",
            'Arabic': "✅ تم الموافقة على سحبك وتمت العملية بنجاح. شكرًا لك!",
            'Chinese': "✅ 您的提现已批准并完成。谢谢！"
        }
        bot.send_message(user_id, texts.get(lang, texts['English']))
        admin_texts = {
            'English': f"✅ Withdrawal for user {user_id} marked as complete and balance updated.",
            'Arabic': f"✅ تم تحديث رصيد المستخدم {user_id} وتأكيد السحب.",
            'Chinese': f"✅ 用户 {user_id} 的提现已完成并更新余额。"
        }
        bot.reply_to(message, admin_texts.get(lang, admin_texts['English']))
    else:
        bot.reply_to(message, "❌ No pending withdrawal found for that user.")
