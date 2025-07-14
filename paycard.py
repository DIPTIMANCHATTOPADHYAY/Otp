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
        lang = user.get('language', 'English')
        try:
            texts = {
                'English': f"✅ Your withdrawal of {amount}$ with leader card '{card_name}' has been approved and completed. Thank you!",
                'Arabic': f"✅ تم الموافقة على سحبك بمبلغ {amount}$ باستخدام بطاقة القائد '{card_name}' وتمت العملية بنجاح. شكرًا لك!",
                'Chinese': f"✅ 您使用领队卡 '{card_name}' 的 {amount}$ 提现已批准并完成。谢谢！"
            }
            bot.send_message(user_id, texts.get(lang, texts['English']))
        except Exception:
            pass  # User may have blocked the bot, ignore errors

    # Approve all in the database
    approve_withdrawals_by_card(card_name)
    admin_texts = {
        'English': f"✅ All pending withdrawals for card '{card_name}' have been approved and users notified.",
        'Arabic': f"✅ تم الموافقة على جميع طلبات السحب المعلقة لبطاقة '{card_name}' وتم إخطار المستخدمين.",
        'Chinese': f"✅ 领队卡 '{card_name}' 的所有待处理提现已批准并通知用户。"
    }
    bot.reply_to(message, admin_texts.get('English', admin_texts['English']))
