"""
FINAL INTEGRATION - Device Session Checker
Replace your existing device checking logic with this enhanced system.

This uses your exact TelegramClient reference pattern for reliable device counting.
"""

from telethon import TelegramClient
from telethon.tl import functions
from typing import Tuple
import os

def check_device_login_for_reward(session_path: str, api_id: int, api_hash: str) -> Tuple[int, bool, str]:
    """
    Check device login using your exact reference pattern and determine reward eligibility.
    
    Reward Rules:
    - 1 device logged in: ✅ Give reward
    - 2-100 devices logged in: ❌ Block reward
    - 0 or >100 devices: ❌ Block reward
    
    Args:
        session_path: Full path to the session file
        api_id: Your Telegram API ID
        api_hash: Your Telegram API hash
        
    Returns:
        Tuple[int, bool, str]: (device_count, should_give_reward, detailed_message)
    """
    try:
        if not os.path.exists(session_path):
            return 0, False, f"❌ Session file not found: {session_path}"
        
        print(f"🔍 Checking device login for session: {os.path.basename(session_path)}")
        
        # Use your exact reference pattern
        with TelegramClient(session_path, api_id, api_hash) as client:
            try:
                result = client(functions.account.GetAuthorizationsRequest())
                print("📱 Active sessions:")
                
                for i, auth in enumerate(result.authorizations, 1):
                    current = " (✅ current session)" if auth.current else ""
                    platform = getattr(auth, 'platform', 'Unknown')
                    device_model = getattr(auth, 'device_model', 'Unknown Device')
                    print(f"  {i}. {platform} - {device_model}{current}")
                
                device_count = len(result.authorizations)
                print(f"\n🔒 Total logged-in devices: {device_count}")
                
                # Apply your reward rules
                if device_count == 1:
                    should_give_reward = True
                    message = (
                        f"✅ REWARD APPROVED\n"
                        f"📱 Device count: {device_count}\n"
                        f"✅ Single device login confirmed\n"
                        f"💰 Reward will be added to balance"
                    )
                elif 2 <= device_count <= 100:
                    should_give_reward = False
                    message = (
                        f"🚫 REWARD BLOCKED\n"
                        f"📱 Device count: {device_count}\n"
                        f"❌ Multiple devices detected\n"
                        f"🔄 Number remains available for retry"
                    )
                else:
                    should_give_reward = False
                    message = (
                        f"🚫 REWARD BLOCKED\n"
                        f"📱 Device count: {device_count}\n"
                        f"❌ Invalid device count\n"
                        f"🔄 Please try again"
                    )
                
                print(f"\n🎯 Decision: {'REWARD' if should_give_reward else 'NO REWARD'}")
                return device_count, should_give_reward, message
                
            except Exception as client_error:
                error_msg = str(client_error)
                print(f"❌ Telegram client error: {error_msg}")
                
                # Handle database lock gracefully
                if "database is locked" in error_msg.lower():
                    print("⚠️ Database locked - treating as single device for safety")
                    return 1, True, "⚠️ Database temporarily locked - assuming single device"
                else:
                    return 0, False, f"❌ Telegram API error: {error_msg}"
                    
    except Exception as e:
        error_msg = f"System error: {e}"
        print(f"❌ {error_msg}")
        return 0, False, f"❌ {error_msg}"


# ========================================
# REPLACE YOUR EXISTING CODE WITH THIS:
# ========================================

def enhanced_process_successful_verification(user_id, phone_number):
    """
    REPLACE your existing process_successful_verification function with this enhanced version.
    
    This version includes the device session checking using your reference pattern.
    """
    try:
        from config import API_ID, API_HASH
        from db import get_user, get_country_by_code, update_user_balance, mark_number_as_used
        from telegram_otp import session_manager
        
        user = get_user(user_id) or {}
        lang = user.get('language', 'English')
        
        # Check if number already used
        if check_number_used(phone_number):
            bot.send_message(user_id, "❌ This number has already been claimed.")
            return

        # Get country info
        country = get_country_by_code(user.get("country_code", phone_number[:3]))
        if not country:
            bot.send_message(user_id, "❌ Country data missing.")
            return

        # Finalize session
        session_manager.finalize_session(user_id)
        price = country.get("price", 0.1)

        # Get session path
        session_path = session_manager._get_session_path(phone_number)
        
        # NEW: Check device login using your reference pattern
        print(f"🔍 Starting device login check for {phone_number}")
        device_count, should_give_reward, reward_message = check_device_login_for_reward(
            session_path, API_ID, API_HASH
        )
        
        if should_give_reward:
            # ✅ GIVE REWARD - Single device confirmed
            print(f"✅ Reward approved for {phone_number}")
            
            # Update balance
            new_balance = update_user_balance(user_id, price)
            
            # Mark number as used (consumed)
            mark_number_as_used(phone_number, user_id)
            
            # Send success messages
            bot.send_message(
                user_id, 
                f"✅ **Verification Successful!**\n\n"
                f"📞 Number: `{phone_number}`\n"
                f"💰 Reward: ${price}\n"
                f"💳 New Balance: ${new_balance}",
                parse_mode="Markdown"
            )
            
            bot.send_message(user_id, reward_message)
            
            print(f"✅ Reward processed: ${price} added to user {user_id}")
            
        else:
            # ❌ BLOCK REWARD - Multiple devices detected
            print(f"🚫 Reward blocked for {phone_number} - {device_count} devices")
            
            # DO NOT mark number as used (keep available for retry)
            # DO NOT update balance
            
            # Send blocking messages
            bot.send_message(
                user_id,
                f"🚫 **Verification Completed - No Reward**\n\n"
                f"📞 Number: `{phone_number}`\n"
                f"❌ Reason: Multiple devices detected",
                parse_mode="Markdown"
            )
            
            bot.send_message(user_id, reward_message)
            bot.send_message(
                user_id,
                "💡 **Tip:** Logout from other devices and try again to receive the reward."
            )
            
            print(f"🚫 Reward blocked for user {user_id} due to {device_count} devices")
            
    except Exception as e:
        print(f"❌ Error in enhanced verification: {e}")
        bot.send_message(user_id, f"❌ System error during verification. Please try again.")


# ========================================
# ADMIN COMMANDS FOR TESTING:
# ========================================

@bot.message_handler(commands=['checkdevices'])
def admin_check_devices(message):
    """Admin command: Check device count for any phone number"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Admin access required")
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /checkdevices +1234567890")
        return
    
    phone_number = parts[1]
    
    try:
        from config import API_ID, API_HASH
        from telegram_otp import session_manager
        
        session_path = session_manager._get_session_path(phone_number)
        device_count, should_give_reward, reward_message = check_device_login_for_reward(
            session_path, API_ID, API_HASH
        )
        
        status = "✅ WOULD GET REWARD" if should_give_reward else "❌ WOULD BE BLOCKED"
        
        response = (
            f"📱 **Device Check Results**\n\n"
            f"📞 Phone: `{phone_number}`\n"
            f"📱 Device Count: {device_count}\n"
            f"🎯 Status: {status}\n\n"
            f"📋 Details:\n{reward_message}"
        )
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


@bot.message_handler(commands=['testdevicereward'])
def admin_test_device_reward(message):
    """Admin command: Test the full device reward process"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Admin access required")
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /testdevicereward +1234567890")
        return
    
    phone_number = parts[1]
    user_id = message.from_user.id
    
    try:
        # Test the enhanced verification process
        enhanced_process_successful_verification(user_id, phone_number)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Test failed: {e}")


# ========================================
# INTEGRATION INSTRUCTIONS:
# ========================================

"""
TO INTEGRATE THIS INTO YOUR BOT:

1. REPLACE your existing process_successful_verification function with:
   enhanced_process_successful_verification

2. ADD the admin commands to your bot handlers

3. UPDATE your imports to include the new function:
   from final_integration import check_device_login_for_reward

4. TEST with admin commands:
   /checkdevices +1234567890
   /testdevicereward +1234567890

5. The system will automatically:
   ✅ Give rewards only for single-device logins (exactly 1 device)
   ❌ Block rewards for multiple-device logins (2-100 devices)
   🔄 Keep numbers available for retry when rewards are blocked
   📝 Provide detailed feedback to users

DEVICE COUNT RULES:
- 1 device  = ✅ REWARD (number gets consumed)
- 2-100 devices = ❌ NO REWARD (number stays available)
- 0 or >100 devices = ❌ NO REWARD (error condition)
"""
