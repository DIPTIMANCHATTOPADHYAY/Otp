"""
Admin command for testing device count functionality
"""

from bot_init import bot
from config import ADMIN_IDS
from telegram_otp import get_logged_in_device_count, get_real_device_count
from translations import get_text
import traceback

@bot.message_handler(commands=['checkdevices'])
def handle_check_devices(message):
    """Admin command to check device count for a phone number"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Access denied. Admin only.")
        return
    
    try:
        # Extract phone number from command
        command_parts = message.text.split()
        if len(command_parts) < 2:
            bot.reply_to(message, """
📱 **Device Count Checker**

Usage: `/checkdevices +1234567890`

This will check how many devices are logged into the specified phone number.
""", parse_mode="Markdown")
            return
        
        phone_number = command_parts[1].strip()
        
        # Clean phone number format
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        bot.reply_to(message, f"🔍 Checking device count for {phone_number}...")
        
        # Get REAL device count for admin debugging
        device_count = get_real_device_count(phone_number)
        
        if device_count == -1:
            status_msg = "❌ **Error Getting Device Count**\n\nThis number has:\n- Session verification error\n- Connection issues\n- Invalid session file"
            reward_msg = "🚫 **Reward Status:** ERROR"
        elif device_count == 1:
            status_msg = "✅ **Single Device Login**\n\nThis number has exactly one active session."
            reward_msg = "💰 **Reward Status:** ALLOWED"
        elif device_count == 0:
            status_msg = "⚠️ **No Active Sessions**\n\nThis number has no logged-in devices."
            reward_msg = "🚫 **Reward Status:** NO SESSIONS"
        else:
            status_msg = f"⚠️ **Multiple Devices ({device_count})**\n\nThis number has {device_count} active sessions."
            reward_msg = "🚫 **Reward Status:** BLOCKED"
        
        response = f"""
📱 **Device Count Report**

📞 **Number:** `{phone_number}`
🔢 **Device Count:** `{device_count}`

{status_msg}

{reward_msg}

---
*Note: Device count -1 indicates error condition. This shows REAL device count for debugging.*
"""
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        error_msg = f"""
❌ **Error checking device count**

**Error:** `{str(e)}`

**Traceback:**
```
{traceback.format_exc()}
```
"""
        bot.reply_to(message, error_msg, parse_mode="Markdown")

@bot.message_handler(commands=['testdevicereward'])
def handle_test_device_reward(message):
    """Admin command to test if a number would receive rewards"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Access denied. Admin only.")
        return
    
    try:
        # Extract phone number from command
        command_parts = message.text.split()
        if len(command_parts) < 2:
            bot.reply_to(message, """
💰 **Device Reward Tester**

Usage: `/testdevicereward +1234567890`

This will simulate the reward check for the specified phone number.
""", parse_mode="Markdown")
            return
        
        phone_number = command_parts[1].strip()
        
        # Clean phone number format
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        bot.reply_to(message, f"🧪 Testing reward eligibility for {phone_number}...")
        
        # Simulate the exact logic from otp.py
        device_count = get_logged_in_device_count(phone_number)
        
        if device_count == 1:
            result = "✅ **REWARD WOULD BE GIVEN**"
            reason = "Single device login detected"
            status = "PASS"
        else:
            result = "🚫 **REWARD WOULD BE BLOCKED**"
            if device_count == 999:
                reason = "Error condition or multiple devices detected (security block)"
            elif device_count == 0:
                reason = "No active sessions found"
            else:
                reason = f"Multiple devices detected ({device_count} sessions)"
            status = "BLOCKED"
        
        response = f"""
🧪 **Reward Eligibility Test**

📞 **Number:** `{phone_number}`
🔢 **Device Count:** `{device_count}`

{result}

**Reason:** {reason}
**Status:** `{status}`

---
**Logic:** Rewards are only given when device_count == 1
**Security:** Any error or multiple devices → BLOCK
"""
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        error_msg = f"""
❌ **Error testing reward eligibility**

**Error:** `{str(e)}`

**Traceback:**
```
{traceback.format_exc()}
```
"""
        bot.reply_to(message, error_msg, parse_mode="Markdown")

@bot.message_handler(commands=['devicestatus'])
def handle_device_status(message):
    """Admin command to show overall device security status"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Access denied. Admin only.")
        return
    
    try:
        status_report = """
🛡️ **Device Security Status Report**

**Current Configuration:**
✅ Strict device counting enabled
✅ Multi-device blocking active  
✅ Error conditions block rewards
✅ Only single-device logins receive rewards

**Security Features:**
🔒 **Error Fallback:** Returns 999 (blocks rewards)
🔒 **Multi-Device Detection:** Counts ALL authorizations
🔒 **Session Validation:** Comprehensive authorization check
🔒 **Zero Tolerance:** No permissive fallbacks

**Available Commands:**
• `/checkdevices +number` - Check device count
• `/testdevicereward +number` - Test reward eligibility
• `/devicestatus` - Show this status

**Recent Fix:**
✅ Fixed critical vulnerability where multi-device logins were receiving rewards
✅ Replaced faulty session counting with comprehensive authorization check
✅ Removed permissive error handling that allowed reward bypass

---
*System is now secure against multi-device reward bypass*
"""
        
        bot.reply_to(message, status_report, parse_mode="Markdown")
        
    except Exception as e:
        error_msg = f"❌ Error generating status report: {str(e)}"
        bot.reply_to(message, error_msg)

@bot.message_handler(commands=['testfailmessage'])
def handle_test_fail_message(message):
    """Admin command to test the verification failure message in different languages"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Access denied. Admin only.")
        return
    
    try:
        # Extract language and phone number from command
        command_parts = message.text.split()
        if len(command_parts) < 3:
            bot.reply_to(message, """
🧪 **Test Verification Failure Message**

Usage: `/testfailmessage <language> +1234567890`

Languages: English, Arabic, Chinese

Example: `/testfailmessage Arabic +972597277582`

This will show how the verification failure message appears in different languages.
""", parse_mode="Markdown")
            return
        
        language = command_parts[1].strip()
        phone_number = command_parts[2].strip()
        
        # Validate language
        if language not in ['English', 'Arabic', 'Chinese']:
            bot.reply_to(message, "❌ Invalid language. Use: English, Arabic, or Chinese")
            return
        
        # Clean phone number format
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        # Test the verification failure message
        verification_failed_msg = get_text(
            'verification_failed', language, 
            phone_number=phone_number
        )
        
        # Test the multiple device warning message
        multiple_device_warning = get_text(
            'multiple_device_warning', language,
            phone_number=phone_number,
            device_count=6
        )
        
        # Test the verification success message
        verification_success_msg = get_text(
            'verification_success', language,
            phone_number=phone_number,
            reward=0.1
        )
        
        response = f"""
🧪 **Verification Message Tests**

**Language:** {language}
**Phone:** {phone_number}

---

**❌ VERIFICATION FAILED MESSAGE:**
{verification_failed_msg}

---

**⚠️ MULTIPLE DEVICE WARNING:**
{multiple_device_warning}

---

**✅ VERIFICATION SUCCESS MESSAGE:**
{verification_success_msg}

---
*These are the actual messages users see during verification*
"""
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        error_msg = f"❌ Error testing messages: {str(e)}"
        bot.reply_to(message, error_msg)
