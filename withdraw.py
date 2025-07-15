from bot_init import bot
from db import (
    get_user,
    log_withdrawal,
    check_leader_card,
    get_pending_withdrawal,
    update_user
)
from utils import require_channel_membership
from config import WITHDRAWAL_LOG_CHAT_ID
import telebot

# In-memory state to track users waiting for card input
user_withdraw_state = {}

def check_withdraw_conditions(user_id, balance):
    """Shared function to check withdrawal conditions"""
    if balance < 1.0:
        return "Minimum withdrawal is 1$"
    if get_pending_withdrawal(user_id):
        return "You already have a pending withdrawal"
    return None

@bot.message_handler(commands=['withdraw'])
@require_channel_membership
def handle_withdraw(message):
    user_id = message.from_user.id
    user = get_user(user_id) or {}
    balance = user.get('balance', 0.0)
    lang = user.get('language', 'English')
    # Check conditions first
    error_msg = check_withdraw_conditions(user_id, balance)
    if error_msg:
        texts = {
            'English': f"❌ {error_msg}",
            'Arabic': f"❌ {error_msg}",
            'Chinese': f"❌ {error_msg}"
        }
        bot.send_message(message.chat.id, texts.get(lang, texts['English']))
        return
    texts = {
        'English': "💳 Please enter your leader card name to proceed with withdrawal:",
        'Arabic': "💳 يرجى إدخال اسم بطاقة القائد للمتابعة في السحب:",
        'Chinese': "💳 请输入您的领队卡名称以继续提现："
    }
    bot.send_message(message.chat.id, texts.get(lang, texts['English']))
    user_withdraw_state[user_id] = {"awaiting_card": True, "balance": balance}

@bot.message_handler(func=lambda m: m.from_user.id in user_withdraw_state and user_withdraw_state[m.from_user.id].get("awaiting_card"))
@require_channel_membership
def handle_leader_card_input(message):
    user_id = message.from_user.id
    card_name = message.text.strip()
    user = get_user(user_id) or {}
    lang = user.get('language', 'English')
    if not check_leader_card(card_name):
        texts = {
            'English': "❌ Incorrect leader card. Please ask admin or try again.",
            'Arabic': "❌ بطاقة القائد غير صحيحة. يرجى سؤال المشرف أو المحاولة مرة أخرى.",
            'Chinese': "❌ 领队卡不正确。请联系管理员或重试。"
        }
        bot.send_message(message.chat.id, texts.get(lang, texts['English']))
        return
    balance = user_withdraw_state[user_id]["balance"]
    # Log the withdrawal as pending
    log_withdrawal(user_id, balance, card_name)
    texts = {
        'English': f"✅ Withdrawal request for {balance}$ submitted with leader card: {card_name}. Please wait for admin approval.",
        'Arabic': f"✅ تم تقديم طلب السحب بمبلغ {balance}$ باستخدام بطاقة القائد: {card_name}. يرجى انتظار موافقة المشرف.",
        'Chinese': f"✅ 提现请求 {balance}$ 已提交，领队卡：{card_name}。请等待管理员批准。"
    }
    bot.send_message(
        message.chat.id, 
        texts.get(lang, texts['English'])
    )
    # Notify admin channel
    admin_texts = {
        'English': f"💸 New withdrawal request:\nUser ID: {user_id}\nAmount: {balance}$\nCard: {card_name}\nApprove with /pay {user_id}\nApprove with /paycard {card_name}",
        'Arabic': f"💸 طلب سحب جديد:\nمعرف المستخدم: {user_id}\nالمبلغ: {balance}$\nالبطاقة: {card_name}\nالموافقة مع /pay {user_id}\nالموافقة مع /paycard {card_name}",
        'Chinese': f"💸 新提现请求：\n用户ID: {user_id}\n金额: {balance}$\n卡：{card_name}\n通过 /pay {user_id} 批准\n通过 /paycard {card_name} 批准"
    }
    bot.send_message(
        WITHDRAWAL_LOG_CHAT_ID,
        admin_texts.get(lang, admin_texts['English'])
    )
    # Clear user state
    user_withdraw_state.pop(user_id, None)