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
from translations import get_text
import telebot
import time

# In-memory state to track users waiting for card input
user_withdraw_state = {}

def check_withdraw_conditions(user_id, balance, user_language='English'):
    """Shared function to check withdrawal conditions"""
    if balance < 1.0:
        return get_text('minimum_withdrawal', user_language)
    if get_pending_withdrawal(user_id):
        return get_text('pending_withdrawal_exists', user_language)
    return None

def clear_withdraw_state(user_id):
    """Clear withdrawal state for user"""
    if user_id in user_withdraw_state:
        user_withdraw_state.pop(user_id)

@bot.message_handler(commands=['withdraw'])
@require_channel_membership
def handle_withdraw(message):
    user_id = message.from_user.id
    user = get_user(user_id) or {}
    balance = user.get('balance', 0.0)
    user_language = user.get('language', 'English')
    
    # Clear any existing state first
    clear_withdraw_state(user_id)
    
    # Check conditions
    error_msg = check_withdraw_conditions(user_id, balance, user_language)
    if error_msg:
        bot.send_message(message.chat.id, f"❌ {error_msg}")
        return
        
    bot.send_message(message.chat.id, get_text('withdrawal_prompt', user_language))
    user_withdraw_state[user_id] = {
        "awaiting_card": True,
        "balance": balance
    }

# Handler for non-command text messages during withdrawal
@bot.message_handler(func=lambda m: (
    hasattr(m, 'text') and 
    m.text and 
    not m.text.startswith('/') and 
    m.from_user.id in user_withdraw_state
))
@require_channel_membership
def handle_withdrawal_card_input(message):
    handle_leader_card_input(message)

def handle_leader_card_input(message):
    user_id = message.from_user.id
    card_name = message.text.strip()
    user = get_user(user_id) or {}
    user_language = user.get('language', 'English')
    
    if not check_leader_card(card_name):
        bot.send_message(message.chat.id, get_text('incorrect_leader_card', user_language))
        return
        
    balance = user_withdraw_state[user_id]["balance"]
    
    # Log the withdrawal as pending
    log_withdrawal(user_id, balance, card_name)
    bot.send_message(
        message.chat.id, 
        get_text('withdrawal_submitted', user_language, balance=balance, card_name=card_name)
    )
    
    # Notify admin channel (admin messages in English)
    bot.send_message(
        WITHDRAWAL_LOG_CHAT_ID,
        get_text('new_withdrawal_request', 'English', user_id=user_id, balance=balance, card_name=card_name)
    )
    
    # Clear user state
    clear_withdraw_state(user_id)