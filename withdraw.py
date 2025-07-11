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
    
    # Check conditions first
    error_msg = check_withdraw_conditions(user_id, balance)
    if error_msg:
        bot.send_message(message.chat.id, f"❌ {error_msg}")
        return
        
    bot.send_message(message.chat.id, "💳 Please enter your leader card name to proceed with withdrawal:")
    user_withdraw_state[user_id] = {"awaiting_card": True, "balance": balance}

@bot.message_handler(func=lambda m: m.from_user.id in user_withdraw_state and user_withdraw_state[m.from_user.id].get("awaiting_card"))
@require_channel_membership
def handle_leader_card_input(message):
    user_id = message.from_user.id
    card_name = message.text.strip()
    
    if not check_leader_card(card_name):
        bot.send_message(message.chat.id, "❌ Incorrect leader card. Please ask admin or try again.")
        return
        
    balance = user_withdraw_state[user_id]["balance"]
    
    # Log the withdrawal as pending
    log_withdrawal(user_id, balance, card_name)
    bot.send_message(
        message.chat.id, 
        f"✅ Withdrawal request for {balance}$ submitted with leader card: {card_name}. Please wait for admin approval."
    )
    
    # Notify admin channel
    bot.send_message(
        WITHDRAWAL_LOG_CHAT_ID,
        f"💸 New withdrawal request:\nUser ID: {user_id}\nAmount: {balance}$\nCard: {card_name}\nApprove with /pay {user_id}\nApprove with /paycard {card_name}"
    )
    
    # Clear user state
    user_withdraw_state.pop(user_id, None)