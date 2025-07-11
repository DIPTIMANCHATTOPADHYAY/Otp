"""
✅ TELEGRAM BOT USER FLOW IMPLEMENTATION

1️⃣ User Sends Phone Number
- Bot checks: Valid format (+123...), country code exists and has capacity, number not already used
- If valid: Sends OTP via Telethon, Bot replies: "📲 Please enter the OTP you received..."

2️⃣ User Sends OTP Code  
- Bot verifies the OTP:
  • If 2FA is required → Bot asks: "🔒 Please enter your 2FA password"
  • If verified → Proceeds to set and update 2FA password with "112233" and reward

3️⃣ User Sends 2FA Password (if needed)
- Bot signs in and sets/updates 2FA password to "112233"
- Sends immediate success message:
  ✅ Account Received
  📞 Number: +...
  💵 Price: 0.1 USDT  
  ⏳ Verified automatically after: 600 seconds

4️⃣ Background Reward Process (Runs in Thread)
- Waits (claim_time - 10 seconds)
- Validates session (only 1 device must be logged in)
- If valid: Adds USDT reward to user, edits success message, sends final reward notification

⚙️ SYSTEM COMPONENTS: Telethon, TeleBot, Threads, Session Manager
"""

import re
import asyncio
import threading
import time
from db import (
    get_user, update_user, get_country_by_code,
    add_pending_number, update_pending_number_status,
    check_number_used, mark_number_used
)
from bot_init import bot
from utils import require_channel_membership
from telegram_otp import session_manager

PHONE_REGEX = re.compile(r'^\+\d{1,4}\d{6,14}$')
otp_loop = asyncio.new_event_loop()

def run_async(coro):
    future = asyncio.run_coroutine_threadsafe(coro, otp_loop)
    return future.result()

def start_otp_loop():
    asyncio.set_event_loop(otp_loop)
    otp_loop.run_forever()

otp_thread = threading.Thread(target=start_otp_loop, daemon=True)
otp_thread.start()

def get_country_code(phone_number):
    for code_length in [4, 3, 2, 1]:
        code = phone_number[:code_length]
        if get_country_by_code(code):
            return code
    return None

@bot.message_handler(func=lambda m: m.text and PHONE_REGEX.match(m.text.strip()))
@require_channel_membership
def handle_phone_number(message):
    try:
        user_id = message.from_user.id
        phone_number = message.text.strip()

        # Bot checks: Valid format, country code exists, capacity, not already used
        if check_number_used(phone_number):
            bot.reply_to(message, "❌ This number is already used")
            return

        country_code = get_country_code(phone_number)
        if not country_code:
            bot.reply_to(message, "❌ Invalid country code")
            return

        country = get_country_by_code(country_code)
        if not country:
            bot.reply_to(message, "❌ Country not supported")
            return

        if country.get("capacity", 0) <= 0:
            bot.reply_to(message, "❌ No capacity for this country")
            return

        # Send OTP via Telethon
        status, result = run_async(session_manager.start_verification(user_id, phone_number))

        if status == "code_sent":
            reply = bot.reply_to(
                message,
                f"📲 Please enter the OTP you received on: {phone_number}\n\n"
                "Reply with the 6-digit code.\n"
                "Type /cancel to abort.",
                parse_mode="Markdown"
            )
            update_user(user_id, {
                "pending_phone": phone_number,
                "otp_msg_id": reply.message_id,
                "country_code": country_code
            })
        else:
            bot.reply_to(message, f"❌ Error: {result}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ System error: {str(e)}")

@bot.message_handler(func=lambda m: (
    m.reply_to_message and 
    any(x in m.reply_to_message.text.lower() 
        for x in ["please enter the otp", "enter the otp"])
))
@require_channel_membership
def handle_otp_reply(message):
    try:
        user_id = message.from_user.id
        otp_code = message.text.strip()
        user = get_user(user_id) or {}
        
        if not user.get("pending_phone"):
            bot.reply_to(message, "❌ No active verification")
            return

        # Bot verifies the OTP
        status, result = run_async(session_manager.verify_code(user_id, otp_code))

        if status == "verified_and_secured":
            # No 2FA needed, proceed directly
            process_successful_verification(user_id, user["pending_phone"])
        elif status == "password_needed":
            # 2FA is required
            bot.send_message(
                user_id,
                "� Please enter your 2FA password:",
                reply_to_message_id=message.message_id
            )
        else:
            bot.reply_to(message, f"❌ Verification failed: {result}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(func=lambda m: (
    session_manager.user_states.get(m.from_user.id, {}).get('state') == 'awaiting_password'
))
@require_channel_membership
def handle_2fa_password(message):
    try:
        user_id = message.from_user.id
        password = message.text.strip()
        
        # Bot signs in and sets 2FA password to "112233"
        status, result = run_async(session_manager.verify_password(user_id, password))

        if status == "verified_and_secured":
            phone = session_manager.user_states[user_id]['phone']
            process_successful_verification(user_id, phone)
        else:
            bot.reply_to(message, f"❌ 2FA Error: {result}")
    except Exception as e:
        bot.reply_to(message, "⚠️ System error. Please try again.")

def process_successful_verification(user_id, phone_number):
    try:
        if check_number_used(phone_number):
            bot.send_message(user_id, "❌ Number already claimed")
            return

        user = get_user(user_id) or {}
        country = get_country_by_code(user.get("country_code", phone_number[:3]))
        
        if not country:
            bot.send_message(user_id, "❌ Country data missing")
            return

        # Finalize session and get configuration
        session_manager.finalize_session(user_id)
        claim_time = country.get("claim_time", 600)
        price = country.get("price", 0.1)

        # Mark number as used
        mark_number_used(phone_number, user_id)
        
        # Send immediate success message
        msg = bot.send_message(
            user_id,
            f"✅ *Account Received*\n\n"
            f"� Number: `{phone_number}`\n"
            f"� Price: `{price}` USDT\n"
            f"⏳ Verified automatically after: `{claim_time}` seconds",
            parse_mode="Markdown"
        )

        # Add pending number record
        pending_id = add_pending_number(user_id, phone_number, price, claim_time)

        # Background Reward Process (Runs in Thread)
        def background_reward_process():
            try:
                # Wait (claim_time - 10 seconds)
                wait_time = max(10, claim_time - 10)
                print(f"⏳ Starting background validation for {phone_number} in {wait_time} seconds")
                time.sleep(wait_time)
                
                print(f"🔍 Validating session for {phone_number}")
                
                # Validate session (only 1 device must be logged in)
                try:
                    valid, reason = session_manager.validate_session_before_reward(phone_number)
                except Exception as validation_error:
                    print(f"❌ Session validation exception: {str(validation_error)}")
                    valid, reason = False, f"Validation error: {str(validation_error)}"
                
                if not valid:
                    print(f"❌ Session validation failed for {phone_number}: {reason}")
                    try:
                        bot.edit_message_text(
                            f"❌ *Verification Failed*\n\n"
                            f"📞 Number: `{phone_number}`\n"
                            f"❌ Reason: {reason}",
                            user_id,
                            msg.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        print(f"Failed to edit message: {edit_error}")
                        # Send a new message if editing fails
                        bot.send_message(
                            user_id,
                            f"❌ *Verification Failed*\n\n"
                            f"📞 Number: `{phone_number}`\n"
                            f"❌ Reason: {reason}",
                            parse_mode="Markdown"
                        )
                    return

                print(f"✅ Session validation passed for {phone_number}")
                
                # If valid: Add USDT reward to user
                try:
                    update_pending_number_status(pending_id, "success")
                    current_balance = user.get("balance", 0)
                    new_balance = current_balance + price
                    
                    success = update_user(user_id, {
                        "balance": new_balance,
                        "sent_accounts": (user.get("sent_accounts", 0) + 1),
                        "pending_phone": None,
                        "otp_msg_id": None
                    })
                    
                    if not success:
                        print(f"❌ Failed to update user balance for {user_id}")
                        bot.send_message(user_id, "❌ Error updating your balance. Please contact support.")
                        return

                    # Edit success message and send final reward notification
                    bot.edit_message_text(
                        f"🎉 *Successfully Verified!*\n\n"
                        f"📞 Number: `{phone_number}`\n"
                        f"💰 Earned: `{price}` USDT\n"
                        f"💳 New Balance: `{new_balance}` USDT",
                        user_id,
                        msg.message_id,
                        parse_mode="Markdown"
                    )
                    
                    print(f"✅ Reward processed successfully for {phone_number}")
                    
                except Exception as reward_error:
                    print(f"❌ Error processing reward: {str(reward_error)}")
                    bot.send_message(
                        user_id,
                        f"❌ Error processing reward for {phone_number}. Please contact support."
                    )
                
            except Exception as e:
                print(f"❌ Background Reward Process Error: {str(e)}")
                try:
                    bot.send_message(
                        user_id,
                        f"❌ System error during verification of {phone_number}. Please contact support."
                    )
                except:
                    print(f"❌ Failed to send error message to user {user_id}")

        # Start background thread
        print(f"🚀 Starting background reward process for {phone_number}")
        threading.Thread(target=background_reward_process, daemon=True).start()

    except Exception as e:
        bot.send_message(user_id, f"⚠️ Processing error: {str(e)}")