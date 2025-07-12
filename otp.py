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

        status, result = run_async(session_manager.start_verification(user_id, phone_number))

        if status == "code_sent":
            reply = bot.reply_to(
                message,
                f"📲 OTP sent to: {phone_number}\n\n"
                "Please reply to this message with the 6-digit code.\n"
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
        for x in ["otp sent to", "enter the otp"])
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

        status, result = run_async(session_manager.verify_code(user_id, otp_code))

        if status == "verified_and_secured":
            process_successful_verification(user_id, user["pending_phone"])
        elif status == "password_needed":
            bot.send_message(
                user_id,
                "🔐 This account has 2FA protection.\n"
                "Please enter your current Telegram password:",
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

        session_manager.finalize_session(user_id)
        claim_time = country.get("claim_time", 600)
        price = country.get("price", 0.1)

        mark_number_used(phone_number, user_id)
        msg = bot.send_message(
            user_id,
            f"✅ *Verification Started*\n\n"
            f"📱 Number: `{phone_number}`\n"
            f"💰 Reward: `{price}` USDT\n"
            f"⏳ Completing in: `{claim_time}` seconds",
            parse_mode="Markdown"
        )

        pending_id = add_pending_number(user_id, phone_number, price, claim_time)

        def finalize_verification():
            try:
                time.sleep(max(10, claim_time - 10))  # Minimum 10 sec buffer
                
                valid, reason = session_manager.validate_session_before_reward(phone_number)
                if not valid:
                    bot.send_message(user_id, f"❌ Failed: {reason}")
                    return

                update_pending_number_status(pending_id, "success")
                update_user(user_id, {
                    "balance": (user.get("balance", 0) + price),
                    "sent_accounts": (user.get("sent_accounts", 0) + 1),
                    "pending_phone": None,
                    "otp_msg_id": None
                })

                bot.edit_message_text(
                    f"🎉 *Successfully Verified!*\n\n"
                    f"📞 Number: `{phone_number}`\n"
                    f"💰 Earned: `{price}` USDT",
                    message.chat.id,
                    msg.message_id,
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Reward Error: {str(e)}")

        threading.Thread(target=finalize_verification, daemon=True).start()

    except Exception as e:
        bot.send_message(user_id, f"⚠️ Processing error: {str(e)}")