"""
🔐 REWARD LOGOUT VERIFICATION SYSTEM

This module handles device logout verification during the reward confirmation process.
It ensures only one device is logged in before confirming rewards, with enhanced 
error handling and user feedback.

Flow:
1. Check active sessions on the verified number
2. If single device → Confirm reward immediately
3. If multiple devices → Attempt automatic logout
4. If logout fails → Request manual cleanup from user
"""

import asyncio
import os
from telethon.sync import TelegramClient
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from config import API_ID, API_HASH, SESSIONS_DIR, DEFAULT_2FA_PASSWORD
from bot_init import bot
import time

class RewardLogoutVerifier:
    def __init__(self):
        self.verification_attempts = {}  # Track attempts per phone number
        
    async def verify_and_reward(self, user_id, phone_number, price, message_id):
        """
        Enhanced verification with logout management before reward confirmation
        
        Returns:
        - ("success", reward_data) - Reward should be given
        - ("failed", reason) - Reward should not be given
        - ("retry_needed", reason) - User needs to manually logout and retry
        """
        session_path = os.path.join(SESSIONS_DIR, f"{phone_number}.session")
        
        if not os.path.exists(session_path):
            return ("failed", "Session file does not exist")
        
        print(f"🔍 Starting reward verification for {phone_number}")
        
        try:
            # Connect to the session
            client = TelegramClient(session_path, API_ID, API_HASH)
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.disconnect()
                return ("failed", "Session is not authorized")
            
            # Get current device sessions
            verification_result = await self._check_and_manage_sessions(
                client, user_id, phone_number, price, message_id
            )
            
            await client.disconnect()
            return verification_result
            
        except Exception as e:
            error_msg = str(e).lower()
            print(f"❌ Reward verification error for {phone_number}: {str(e)}")
            
            # Handle specific error types
            if "flood" in error_msg:
                return ("failed", "Rate limited by Telegram. Please wait before retrying.")
            elif "auth" in error_msg:
                return ("failed", "Session authentication failed")
            else:
                return ("failed", f"Verification error: {str(e)}")

    async def _check_and_manage_sessions(self, client, user_id, phone_number, price, message_id):
        """
        Check active sessions and manage device logout
        """
        try:
            # Get all active sessions
            auths = await client(GetAuthorizationsRequest())
            sessions = auths.authorizations
            active_sessions = len(sessions)
            
            print(f"📱 Found {active_sessions} active session(s) for {phone_number}")
            
            # Case 1: Single device - Perfect! Give reward immediately
            if active_sessions == 1:
                print(f"✅ Single device confirmed for {phone_number} - Proceeding with reward")
                
                # Update success message
                try:
                    bot.edit_message_text(
                        f"🎉 *Device Check Passed!*\n\n"
                        f"📞 Number: `{phone_number}`\n"
                        f"📱 Devices: 1 (Perfect!)\n"
                        f"💰 Processing reward: `{price}` USDT...",
                        user_id,
                        message_id,
                        parse_mode="Markdown"
                    )
                except Exception as edit_error:
                    print(f"Failed to edit message: {edit_error}")
                
                return ("success", {
                    "phone": phone_number,
                    "price": price,
                    "devices_before": active_sessions,
                    "devices_after": 1,
                    "logout_attempted": False
                })
            
            # Case 2: Multiple devices - Attempt automatic logout
            elif active_sessions > 1:
                print(f"⚠️ Multiple devices detected ({active_sessions}) for {phone_number} - Attempting logout")
                
                # Notify user of logout attempt
                try:
                    bot.edit_message_text(
                        f"🔄 *Device Cleanup in Progress*\n\n"
                        f"📞 Number: `{phone_number}`\n"
                        f"📱 Found: {active_sessions} devices\n"
                        f"🔒 Logging out other devices...",
                        user_id,
                        message_id,
                        parse_mode="Markdown"
                    )
                except Exception as edit_error:
                    print(f"Failed to edit message: {edit_error}")
                
                # Attempt to logout other devices
                logout_result = await self._attempt_device_logout(client, phone_number)
                
                if logout_result["success"]:
                    print(f"✅ Logout successful for {phone_number}")
                    
                    # Update success message
                    try:
                        bot.edit_message_text(
                            f"🎉 *Device Cleanup Successful!*\n\n"
                            f"📞 Number: `{phone_number}`\n"
                            f"📱 Devices: {logout_result['final_sessions']} (Cleaned up!)\n"
                            f"💰 Processing reward: `{price}` USDT...",
                            user_id,
                            message_id,
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        print(f"Failed to edit message: {edit_error}")
                    
                    return ("success", {
                        "phone": phone_number,
                        "price": price,
                        "devices_before": active_sessions,
                        "devices_after": logout_result['final_sessions'],
                        "logout_attempted": True,
                        "logged_out_devices": logout_result['logged_out_devices']
                    })
                else:
                    print(f"❌ Logout failed for {phone_number}")
                    return await self._handle_logout_failure(
                        user_id, phone_number, price, message_id, 
                        active_sessions, logout_result
                    )
            
            # Case 3: No sessions (should not happen, but handle gracefully)
            else:
                return ("failed", "No active sessions found")
                
        except Exception as e:
            print(f"❌ Session management error: {str(e)}")
            return ("failed", f"Session check failed: {str(e)}")

    async def _attempt_device_logout(self, client, phone_number):
        """
        Attempt to logout other devices and return detailed results
        """
        result = {
            "success": False,
            "final_sessions": 0,
            "logged_out_devices": [],
            "error": None
        }
        
        try:
            # Get initial sessions
            auths = await client(GetAuthorizationsRequest())
            initial_sessions = auths.authorizations
            
            # Logout all non-current sessions
            logged_out_count = 0
            for session in initial_sessions:
                if not session.current:
                    try:
                        await client(ResetAuthorizationRequest(hash=session.hash))
                        device_info = f"{session.device_model} | {session.app_name}"
                        result["logged_out_devices"].append(device_info)
                        logged_out_count += 1
                        print(f"🔒 Logged out: {device_info}")
                        
                        # Small delay to avoid flooding
                        await asyncio.sleep(0.5)
                        
                    except Exception as logout_error:
                        print(f"⚠️ Failed to logout device {session.device_model}: {logout_error}")
            
            # Verify logout success
            await asyncio.sleep(2)  # Wait for logout to propagate
            updated_auths = await client(GetAuthorizationsRequest())
            final_sessions = len(updated_auths.authorizations)
            
            result["final_sessions"] = final_sessions
            
            if final_sessions == 1:
                result["success"] = True
                print(f"✅ Logout successful: {logged_out_count} devices removed")
            else:
                result["success"] = False
                result["error"] = f"Still {final_sessions} sessions active after logout attempt"
                print(f"❌ Logout incomplete: {final_sessions} sessions remaining")
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Logout attempt failed: {str(e)}")
            return result

    async def _handle_logout_failure(self, user_id, phone_number, price, message_id, 
                                   initial_sessions, logout_result):
        """
        Handle failed logout attempts with user guidance
        """
        # Track failure attempts
        attempt_key = f"{user_id}_{phone_number}"
        current_attempts = self.verification_attempts.get(attempt_key, 0) + 1
        self.verification_attempts[attempt_key] = current_attempts
        
        error_details = logout_result.get("error", "Unknown logout error")
        logged_out_count = len(logout_result.get("logged_out_devices", []))
        remaining_sessions = logout_result.get("final_sessions", initial_sessions)
        
        print(f"❌ Logout failure attempt #{current_attempts} for {phone_number}")
        print(f"   Logged out: {logged_out_count} devices")
        print(f"   Remaining: {remaining_sessions} sessions")
        print(f"   Error: {error_details}")
        
        # Create detailed failure message
        failure_message = (
            f"❌ *Device Cleanup Failed*\n\n"
            f"📞 Number: `{phone_number}`\n"
            f"📱 Initial devices: {initial_sessions}\n"
            f"🔒 Logged out: {logged_out_count} devices\n"
            f"⚠️ Still active: {remaining_sessions} sessions\n\n"
            f"🔧 **Manual Action Required:**\n"
            f"1. Open Telegram on `{phone_number}`\n"
            f"2. Go to Settings → Privacy & Security → Active Sessions\n"
            f"3. Terminate all other sessions manually\n"
            f"4. Use the number again in this bot\n\n"
            f"💡 *Tip: Keep only ONE device logged in*\n"
            f"🔄 *Attempt: {current_attempts}/3*"
        )
        
        # Send guidance message
        try:
            bot.edit_message_text(
                failure_message,
                user_id,
                message_id,
                parse_mode="Markdown"
            )
        except Exception as edit_error:
            print(f"Failed to edit message: {edit_error}")
            # Send new message if editing fails
            bot.send_message(user_id, failure_message, parse_mode="Markdown")
        
        # Also send additional help if multiple attempts
        if current_attempts >= 2:
            help_message = (
                f"🆘 **Need Help with {phone_number}?**\n\n"
                f"If you're having trouble logging out other devices:\n\n"
                f"📱 **On Mobile:**\n"
                f"• Settings → Privacy & Security → Active Sessions\n"
                f"• Tap each session and select 'Terminate'\n\n"
                f"💻 **On Desktop:**\n"
                f"• Settings → Privacy & Security → Active Sessions\n"
                f"• Click 'Terminate' on unwanted sessions\n\n"
                f"⏰ **Wait 5 minutes** after manual logout before retrying"
            )
            
            try:
                bot.send_message(user_id, help_message, parse_mode="Markdown")
            except Exception as help_error:
                print(f"Failed to send help message: {help_error}")
        
        return ("retry_needed", f"Manual device cleanup required - {remaining_sessions} sessions active")

    def clear_attempt_history(self, user_id, phone_number):
        """Clear attempt history for successful verifications"""
        attempt_key = f"{user_id}_{phone_number}"
        if attempt_key in self.verification_attempts:
            del self.verification_attempts[attempt_key]
            print(f"🗑️ Cleared attempt history for {phone_number}")

# Global instance
reward_logout_verifier = RewardLogoutVerifier()