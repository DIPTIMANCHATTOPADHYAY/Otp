import os
import asyncio
import threading
import time
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError, ChatWriteForbiddenError
from bot_init import bot
from config import API_ID, API_HASH, SESSIONS_DIR, ADMIN_IDS
from telegram_otp import session_manager
from utils import require_channel_membership
import re

def is_admin(user_id):
    return user_id in ADMIN_IDS

class FrozenChecker:
    def __init__(self):
        self.checking = False
        self.results = {}
        
    def check_account_frozen_sync(self, session_path, phone_number):
        """Check if a single account is frozen using synchronous approach with retry logic"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"🔍 Checking account: {phone_number} (attempt {attempt + 1}/{max_retries})")
                
                # Create client with session
                client = TelegramClient(session_path, API_ID, API_HASH)
                
                # Set connection timeout
                client.connect(timeout=30)
                
                if not client.is_user_authorized():
                    client.disconnect()
                    print(f"❌ {phone_number}: Session not authorized")
                    return {
                        "phone": phone_number,
                        "status": "unauthorized",
                        "message": "Session not authorized"
                    }
                
                # Get account info
                me = client.get_me()
                if not me:
                    client.disconnect()
                    print(f"❌ {phone_number}: Could not get account info")
                    return {
                        "phone": phone_number,
                        "status": "error",
                        "message": "Could not get account info"
                    }
                
                print(f"✅ {phone_number}: Connected successfully")
                
                # Send message to @Spambot
                try:
                    spambot_entity = client.get_entity("@Spambot")
                    print(f"📤 {phone_number}: Sending message to @Spambot")
                    message = client.send_message(spambot_entity, "/start")
                    
                    # Wait for response with longer timeout
                    time.sleep(5)
                    
                    # Get the response
                    messages = client.get_messages(spambot_entity, limit=1)
                    if messages:
                        message = messages[0]
                        response_text = message.text.lower() if message.text else ""
                        print(f"📥 {phone_number}: Received response: {response_text[:100]}...")
                        
                        # Check for frozen indicators
                        if "good news, no limits are currently applied" in response_text:
                            status = "active"
                            message_text = "✅ Account is active and not frozen"
                        elif "account was blocked for violations" in response_text:
                            status = "frozen"
                            message_text = "❌ Account is frozen (blocked for violations)"
                        elif "account was limited by mistake" in response_text or "anti-spam systems" in response_text:
                            status = "limited"
                            message_text = "⚠️ Account is limited (anti-spam restrictions)"
                        elif "sorry" in response_text and "limited" in response_text:
                            status = "limited"
                            message_text = "⚠️ Account is limited (anti-spam restrictions)"
                        else:
                            status = "unknown"
                            message_text = f"❓ Unknown status: {response_text[:100]}..."
                        
                        client.disconnect()
                        print(f"✅ {phone_number}: Check completed - {status}")
                        return {
                            "phone": phone_number,
                            "status": status,
                            "message": message_text,
                            "response": response_text[:200]
                        }
                    else:
                        client.disconnect()
                        print(f"❌ {phone_number}: No response from @Spambot")
                        return {
                            "phone": phone_number,
                            "status": "error",
                            "message": "No response from @Spambot"
                        }
                    
                except FloodWaitError as e:
                    client.disconnect()
                    print(f"⏳ {phone_number}: Rate limited for {e.seconds} seconds")
                    return {
                        "phone": phone_number,
                        "status": "flood_wait",
                        "message": f"Rate limited: {e.seconds} seconds"
                    }
                except ChatWriteForbiddenError:
                    client.disconnect()
                    print(f"❌ {phone_number}: Cannot send message to @Spambot")
                    return {
                        "phone": phone_number,
                        "status": "error",
                        "message": "Cannot send message to @Spambot"
                    }
                except Exception as e:
                    client.disconnect()
                    print(f"❌ {phone_number}: Error checking account: {str(e)}")
                    return {
                        "phone": phone_number,
                        "status": "error",
                        "message": f"Error checking account: {str(e)}"
                    }
                    
            except Exception as e:
                error_msg = str(e)
                print(f"❌ {phone_number}: Attempt {attempt + 1} failed: {error_msg}")
                
                # Check if it's a connection error
                if "Connection reset" in error_msg or "Connection aborted" in error_msg:
                    if attempt < max_retries - 1:
                        print(f"🔄 {phone_number}: Connection error, retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        print(f"❌ {phone_number}: Max retries reached for connection error")
                        return {
                            "phone": phone_number,
                            "status": "error",
                            "message": f"Connection error after {max_retries} attempts: {error_msg}"
                        }
                else:
                    # For non-connection errors, don't retry
                    print(f"❌ {phone_number}: Non-connection error, not retrying")
                    return {
                        "phone": phone_number,
                        "status": "error",
                        "message": f"Session error: {error_msg}"
                    }
        
        # If we get here, all retries failed
        return {
            "phone": phone_number,
            "status": "error",
            "message": f"Failed after {max_retries} attempts"
        }

    def check_country_sessions_sync(self, country_code):
        """Check all sessions for a specific country using synchronous approach"""
        if self.checking:
            return {"error": "Already checking sessions"}
        
        self.checking = True
        self.results = {
            "country": country_code,
            "total": 0,
            "active": 0,
            "frozen": 0,
            "limited": 0,
            "error": 0,
            "unauthorized": 0,
            "flood_wait": 0,
            "details": []
        }
        
        try:
            print(f"🌍 Starting frozen check for {country_code}")
            
            # Get sessions for this country
            sessions_by_country = session_manager.list_country_sessions(country_code)
            
            if country_code not in sessions_by_country or not sessions_by_country[country_code]:
                self.checking = False
                return {"error": f"No sessions found for {country_code}"}
            
            sessions = sessions_by_country[country_code]
            self.results["total"] = len(sessions)
            
            print(f"📱 Found {len(sessions)} sessions for {country_code}")
            
            # Check each session
            for i, session in enumerate(sessions):
                session_path = session['session_path']
                phone_number = session['phone_number']
                
                print(f"🔍 Checking {i+1}/{len(sessions)}: {phone_number}")
                
                if not os.path.exists(session_path):
                    result = {
                        "phone": phone_number,
                        "status": "error",
                        "message": "Session file not found"
                    }
                else:
                    result = self.check_account_frozen_sync(session_path, phone_number)
                
                # Update counters
                status = result.get("status", "error")
                if status in self.results:
                    self.results[status] += 1
                
                self.results["details"].append(result)
                
                # Add delay between checks to avoid rate limiting
                if i < len(sessions) - 1:
                    delay = 5 + (i % 3)  # Vary delay between 5-7 seconds
                    print(f"⏳ Waiting {delay} seconds before next check...")
                    time.sleep(delay)
            
            self.checking = False
            print(f"✅ Completed frozen check for {country_code}: {self.results['total']} sessions")
            return self.results
            
        except Exception as e:
            self.checking = False
            print(f"❌ Error in check_country_sessions_sync: {str(e)}")
            return {"error": f"Error checking sessions: {str(e)}"}

# Global instance
frozen_checker = FrozenChecker()

@bot.message_handler(commands=['frozen'])
@require_channel_membership
def handle_frozen_check(message):
    """Check if session accounts are frozen for a specific country"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        # Parse the command: /frozen +country_code
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) != 2:
            bot.reply_to(
                message,
                "❌ **Usage:** `/frozen +country_code`\n\n"
                "**Examples:**\n"
                "• `/frozen +1` - Check all US/Canada sessions\n"
                "• `/frozen +44` - Check all UK sessions\n"
                "• `/frozen +91` - Check all India sessions\n"
                "• `/frozen +86` - Check all China sessions\n\n"
                "⚠️ **Note:** This will test each account with @Spambot and may take some time.",
                parse_mode="Markdown"
            )
            return
        
        country_code = parts[1].strip()
        
        # Validate country code format
        if not re.match(r'^\+\d{1,4}$', country_code):
            bot.reply_to(
                message,
                "❌ **Invalid country code format!**\n\n"
                "Use format like: `+1`, `+44`, `+91`, `+86`",
                parse_mode="Markdown"
            )
            return
        
        # Check if already running
        if frozen_checker.checking:
            bot.reply_to(message, "⏳ **Already checking sessions!**\n\nPlease wait for the current check to complete.")
            return
        
        # Send initial message
        status_msg = bot.reply_to(
            message,
            f"🔍 **Starting frozen check for {country_code}**\n\n"
            f"⏳ Please wait while I check all sessions...\n"
            f"📊 This may take several minutes depending on the number of sessions.",
            parse_mode="Markdown"
        )
        
        # Run the check in background
        def run_check():
            try:
                print(f"🚀 Starting frozen check for {country_code}")
                result = frozen_checker.check_country_sessions_sync(country_code)
                
                if result is None:
                    bot.edit_message_text(
                        f"❌ **Error:** Failed to run frozen check\n\n"
                        f"Please check the console logs for more details.",
                        chat_id=user_id,
                        message_id=status_msg.message_id,
                        parse_mode="Markdown"
                    )
                    return
                
                if "error" in result:
                    bot.edit_message_text(
                        f"❌ **Error:** {result['error']}",
                        chat_id=user_id,
                        message_id=status_msg.message_id,
                        parse_mode="Markdown"
                    )
                    return
                
                # Create detailed report
                report = create_frozen_report(result)
                
                # Send the report
                bot.edit_message_text(
                    report,
                    chat_id=user_id,
                    message_id=status_msg.message_id,
                    parse_mode="Markdown"
                )
                
                print(f"✅ Admin {user_id} completed frozen check for {country_code}: {result['total']} sessions")
                
            except Exception as e:
                error_msg = f"❌ **Error during frozen check:** {str(e)}"
                print(f"❌ Error in frozen check for user {user_id}: {e}")
                import traceback
                traceback.print_exc()
                
                bot.edit_message_text(
                    error_msg,
                    chat_id=user_id,
                    message_id=status_msg.message_id,
                    parse_mode="Markdown"
                )
        
        # Start the check in a separate thread
        check_thread = threading.Thread(target=run_check, daemon=True)
        check_thread.start()
        
    except Exception as e:
        bot.reply_to(message, f"❌ **Error:** {str(e)}", parse_mode="Markdown")
        print(f"❌ Error in frozen command for user {user_id}: {e}")

def create_frozen_report(result):
    """Create a detailed report from frozen check results"""
    country = result['country']
    total = result['total']
    
    # Calculate percentages
    active_pct = (result['active'] / total * 100) if total > 0 else 0
    frozen_pct = (result['frozen'] / total * 100) if total > 0 else 0
    limited_pct = (result['limited'] / total * 100) if total > 0 else 0
    error_pct = (result['error'] / total * 100) if total > 0 else 0
    
    report = f"🔍 **Frozen Check Report for {country}**\n\n"
    report += f"📊 **Summary:**\n"
    report += f"• 📱 **Total Sessions:** {total}\n"
    report += f"• ✅ **Active:** {result['active']} ({active_pct:.1f}%)\n"
    report += f"• ❌ **Frozen:** {result['frozen']} ({frozen_pct:.1f}%)\n"
    report += f"• ⚠️ **Limited:** {result['limited']} ({limited_pct:.1f}%)\n"
    report += f"• ❓ **Errors:** {result['error']} ({error_pct:.1f}%)\n"
    report += f"• 🔄 **Unauthorized:** {result['unauthorized']}\n"
    report += f"• ⏳ **Rate Limited:** {result['flood_wait']}\n\n"
    
    # Create separate text files for different account statuses
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Separate accounts by status
    active_accounts = [r for r in result['details'] if r['status'] == 'active']
    frozen_accounts = [r for r in result['details'] if r['status'] == 'frozen']
    limited_accounts = [r for r in result['details'] if r['status'] == 'limited']
    error_accounts = [r for r in result['details'] if r['status'] == 'error']
    
    # Create text files
    files_created = []
    
    if active_accounts:
        filename = f"active_accounts_{country}_{timestamp}.txt"
        create_account_file(filename, "Active Accounts", active_accounts)
        files_created.append(filename)
    
    if frozen_accounts:
        filename = f"frozen_accounts_{country}_{timestamp}.txt"
        create_account_file(filename, "Frozen Accounts", frozen_accounts)
        files_created.append(filename)
    
    if limited_accounts:
        filename = f"limited_accounts_{country}_{timestamp}.txt"
        create_account_file(filename, "Limited Accounts", limited_accounts)
        files_created.append(filename)
    
    if error_accounts:
        filename = f"error_accounts_{country}_{timestamp}.txt"
        create_account_file(filename, "Error Accounts", error_accounts)
        files_created.append(filename)
    
    # Add file information to report
    if files_created:
        report += f"📄 **Files Created:**\n"
        for filename in files_created:
            report += f"• `{filename}`\n"
        report += "\n"
    
    # Add timestamp
    report += f"📅 **Checked:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    return report

def create_account_file(filename, title, accounts):
    """Create a text file with account details"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{title} Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Count: {len(accounts)}\n")
            f.write("=" * 50 + "\n\n")
            
            for account in accounts:
                f.write(f"Phone: {account['phone']}\n")
                f.write(f"Status: {account['status']}\n")
                f.write(f"Message: {account['message']}\n")
                if 'response' in account:
                    f.write(f"Spambot Response: {account['response']}\n")
                f.write("-" * 30 + "\n")
        
        print(f"✅ Created {filename} with {len(accounts)} accounts")
        
    except Exception as e:
        print(f"❌ Error creating {filename}: {e}")

@bot.message_handler(commands=['frozenstatus'])
@require_channel_membership
def handle_frozen_status(message):
    """Check the status of ongoing frozen check"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    if not frozen_checker.checking:
        bot.reply_to(message, "📊 **No frozen check currently running**\n\nUse `/frozen +country_code` to start a check.")
        return
    
    # Get current progress if available
    if frozen_checker.results:
        progress = frozen_checker.results
        report = f"⏳ **Frozen Check in Progress**\n\n"
        report += f"🌍 **Country:** {progress.get('country', 'Unknown')}\n"
        report += f"📱 **Total:** {progress.get('total', 0)}\n"
        report += f"✅ **Active:** {progress.get('active', 0)}\n"
        report += f"❌ **Frozen:** {progress.get('frozen', 0)}\n"
        report += f"⚠️ **Limited:** {progress.get('limited', 0)}\n"
        report += f"❓ **Errors:** {progress.get('error', 0)}\n"
        bot.reply_to(message, report, parse_mode="Markdown")
    else:
        bot.reply_to(message, "⏳ **Frozen check is running...**\n\nPlease wait for completion.")

@bot.message_handler(commands=['frozencheck'])
@require_channel_membership
def handle_frozen_connection_check(message):
    """Check connection status before running frozen check"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        bot.reply_to(message, "🔍 **Testing connection to Telegram...**\n\nChecking if we can connect to Telegram servers.")
        
        # Test connection with a simple client
        try:
            test_client = TelegramClient("test_session", API_ID, API_HASH)
            test_client.connect(timeout=10)
            
            if test_client.is_user_authorized():
                bot.send_message(user_id, "✅ **Connection Test Successful**\n\nTelegram connection is working properly.")
            else:
                bot.send_message(user_id, "⚠️ **Connection Test Warning**\n\nConnected to Telegram but not authorized. This is normal for test sessions.")
            
            test_client.disconnect()
            
        except Exception as e:
            bot.send_message(user_id, f"❌ **Connection Test Failed**\n\nError: {str(e)}\n\nThis might indicate network issues or API problems.")
        
        print(f"✅ Admin {user_id} ran connection test")
        
    except Exception as e:
        bot.reply_to(message, f"❌ **Test Error:** {str(e)}", parse_mode="Markdown")
        print(f"❌ Error in connection test for user {user_id}: {e}")

@bot.message_handler(commands=['frozentest'])
@require_channel_membership
def handle_frozen_test(message):
    """Test the frozen checker with a simple check"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        bot.reply_to(message, "🧪 **Testing frozen checker...**\n\nChecking if the system is working properly.")
        
        # Simple test to check if the system is working
        test_result = {
            "country": "TEST",
            "total": 1,
            "active": 1,
            "frozen": 0,
            "limited": 0,
            "error": 0,
            "unauthorized": 0,
            "flood_wait": 0,
            "details": [{
                "phone": "+1234567890",
                "status": "active",
                "message": "✅ Test account is active",
                "response": "Good news, no limits are currently applied to your account. You're free as a bird!"
            }]
        }
        
        report = create_frozen_report(test_result)
        bot.send_message(user_id, report, parse_mode="Markdown")
        
        print(f"✅ Admin {user_id} ran frozen test successfully")
        
    except Exception as e:
        bot.reply_to(message, f"❌ **Test Error:** {str(e)}", parse_mode="Markdown")
        print(f"❌ Error in frozen test for user {user_id}: {e}")