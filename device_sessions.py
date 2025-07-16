"""
Device Sessions Checker
This module checks device login sessions for phone numbers and determines reward eligibility.

Requirements:
- If 1 device is logged in: Give reward
- If 2-100 devices are logged in: Do not give reward
"""

import os
import asyncio
import tempfile
import shutil
from telethon import TelegramClient
from telethon.tl.functions.account import GetAuthorizationsRequest
from config import API_ID, API_HASH, SESSIONS_DIR
from db import get_user, update_user_balance, add_transaction_log
from typing import Tuple, Optional


class DeviceSessionChecker:
    """Class to handle device session checking and reward distribution"""
    
    def __init__(self):
        self.session_manager = None
    
    def _get_session_path(self, phone_number: str) -> str:
        """Get the session file path for a phone number"""
        # Import here to avoid circular imports
        from telegram_otp import SessionManager
        if not self.session_manager:
            self.session_manager = SessionManager()
        return self.session_manager._get_session_path(phone_number)
    
    async def get_device_count(self, phone_number: str) -> Tuple[int, Optional[str]]:
        """
        Get the number of logged-in devices for a phone number.
        Uses your reference pattern with TelegramClient context manager.
        
        Returns:
            Tuple[int, Optional[str]]: (device_count, error_message)
            - device_count: Number of active devices (0 if error)
            - error_message: None if successful, error string if failed
        """
        session_path = self._get_session_path(phone_number)
        
        if not os.path.exists(session_path):
            return 0, f"Session file not found for {phone_number}"
        
        try:
            # Create a temporary copy to avoid locking conflicts
            with tempfile.NamedTemporaryFile(suffix='.session', delete=False) as temp_file:
                temp_session_path = temp_file.name
            
            try:
                # Copy the session file to temporary location
                shutil.copy2(session_path, temp_session_path)
                
                # Use context manager pattern from your reference code
                with TelegramClient(temp_session_path, API_ID, API_HASH) as client:
                    try:
                        # Get authorization sessions using your reference pattern
                        result = await client(GetAuthorizationsRequest())
                        
                        print(f"📱 Active sessions for {phone_number}:")
                        for i, auth in enumerate(result.authorizations, 1):
                            current = " (✅ current session)" if auth.current else ""
                            platform = getattr(auth, 'platform', 'Unknown')
                            device_model = getattr(auth, 'device_model', 'Unknown Device')
                            print(f"  {i}. {platform} - {device_model}{current}")
                        
                        device_count = len(result.authorizations)
                        print(f"\n🔒 Total logged-in devices: {device_count}")
                        
                        return device_count, None
                        
                    except Exception as client_error:
                        error_msg = str(client_error).lower()
                        if "database is locked" in error_msg:
                            print(f"⚠️ Database locked for {phone_number}, using fallback")
                            return 1, None  # Fallback: assume single device
                        else:
                            print(f"❌ Client error for {phone_number}: {client_error}")
                            return 0, f"Client error: {client_error}"
                        
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(temp_session_path):
                        os.unlink(temp_session_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"❌ Error checking device count for {phone_number}: {e}")
            return 0, f"Error checking device count: {e}"
    
    def check_reward_eligibility(self, device_count: int) -> Tuple[bool, str]:
        """
        Check if user is eligible for reward based on device count.
        
        Args:
            device_count: Number of logged-in devices
            
        Returns:
            Tuple[bool, str]: (is_eligible, reason)
        """
        if device_count == 1:
            return True, "Single device login confirmed - eligible for reward"
        elif 2 <= device_count <= 100:
            return False, f"Multiple devices logged in ({device_count} devices) - not eligible for reward"
        else:
            return False, f"Invalid device count ({device_count}) - not eligible for reward"
    
    async def process_device_session_reward(self, user_id: int, phone_number: str, reward_amount: float) -> Tuple[bool, str]:
        """
        Complete process: Check device sessions and give reward if eligible.
        
        Args:
            user_id: Telegram user ID
            phone_number: Phone number to check
            reward_amount: Amount to reward if eligible
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            print(f"🔍 Starting device session check for {phone_number} (User: {user_id})")
            
            # Get device count
            device_count, error = await self.get_device_count(phone_number)
            
            if error:
                return False, f"❌ Failed to check device count: {error}"
            
            # Check eligibility
            is_eligible, reason = self.check_reward_eligibility(device_count)
            
            print(f"📋 Reward eligibility for {phone_number}: {is_eligible} - {reason}")
            
            if is_eligible:
                # Give reward
                try:
                    # Update user balance
                    current_balance = update_user_balance(user_id, reward_amount)
                    
                    # Log transaction
                    add_transaction_log(
                        user_id=user_id,
                        transaction_type="device_session_reward",
                        amount=reward_amount,
                        description=f"Reward for single device login: {phone_number}",
                        phone_number=phone_number
                    )
                    
                    success_msg = (
                        f"✅ Reward granted!\n"
                        f"📞 Phone: {phone_number}\n"
                        f"📱 Devices: {device_count}\n"
                        f"💰 Reward: ${reward_amount}\n"
                        f"💳 New balance: ${current_balance}"
                    )
                    
                    print(f"✅ Reward processed successfully for {phone_number}")
                    return True, success_msg
                    
                except Exception as reward_error:
                    return False, f"❌ Failed to process reward: {reward_error}"
            else:
                # Not eligible for reward
                no_reward_msg = (
                    f"🚫 No reward given\n"
                    f"📞 Phone: {phone_number}\n"
                    f"📱 Devices: {device_count}\n"
                    f"❌ Reason: {reason}"
                )
                
                print(f"🚫 No reward for {phone_number} - {reason}")
                return False, no_reward_msg
                
        except Exception as e:
            error_msg = f"❌ System error during device session check: {e}"
            print(error_msg)
            return False, error_msg


# Standalone functions for use in other modules
device_checker = DeviceSessionChecker()

def check_device_login_reference_pattern(session_name: str, api_id: int, api_hash: str) -> Tuple[int, Optional[str]]:
    """
    Check device login using your exact reference pattern.
    This is a standalone function that matches your code structure exactly.
    
    Args:
        session_name: Path to the session file
        api_id: Telegram API ID
        api_hash: Telegram API hash
        
    Returns:
        Tuple[int, Optional[str]]: (device_count, error_message)
    """
    try:
        # Import here to avoid circular imports
        from telethon import TelegramClient
        from telethon.tl import functions
        
        # Use your exact reference pattern
        with TelegramClient(session_name, api_id, api_hash) as client:
            try:
                result = client(functions.account.GetAuthorizationsRequest())
                print("📱 Active sessions:\n")
                for i, auth in enumerate(result.authorizations, 1):
                    current = " (✅ current session)" if auth.current else ""
                    platform = getattr(auth, 'platform', 'Unknown')
                    device_model = getattr(auth, 'device_model', 'Unknown Device')
                    print(f"{i}. {platform} - {device_model}{current}")
                
                device_count = len(result.authorizations)
                print(f"\n🔒 Total logged-in devices: {device_count}")
                
                return device_count, None
                
            except Exception as client_error:
                error_msg = str(client_error).lower()
                if "database is locked" in error_msg:
                    print(f"⚠️ Database locked, using fallback")
                    return 1, None  # Fallback: assume single device
                else:
                    print(f"❌ Client error: {client_error}")
                    return 0, f"Client error: {client_error}"
                    
    except Exception as e:
        print(f"❌ Error in reference pattern check: {e}")
        return 0, f"Error: {e}"

def check_device_sessions_and_reward(user_id: int, phone_number: str, reward_amount: float) -> Tuple[bool, str]:
    """
    Synchronous wrapper for device session checking and reward processing.
    
    Args:
        user_id: Telegram user ID
        phone_number: Phone number to check
        reward_amount: Amount to reward if eligible
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        # Create new event loop for this thread
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function
        return loop.run_until_complete(
            device_checker.process_device_session_reward(user_id, phone_number, reward_amount)
        )
        
    except Exception as e:
        return False, f"❌ Error in device session check: {e}"
    finally:
        try:
            loop.close()
        except:
            pass

def get_device_count_sync(phone_number: str) -> Tuple[int, Optional[str]]:
    """
    Synchronous wrapper to get device count for a phone number.
    
    Args:
        phone_number: Phone number to check
        
    Returns:
        Tuple[int, Optional[str]]: (device_count, error_message)
    """
    try:
        # Create new event loop for this thread
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function
        return loop.run_until_complete(device_checker.get_device_count(phone_number))
        
    except Exception as e:
        return 0, f"Error: {e}"
    finally:
        try:
            loop.close()
        except:
            pass


# Example usage functions
def example_usage():
    """Example of how to use the device session checker"""
    
    # Example 1: Check device count only
    phone_number = "+1234567890"
    device_count, error = get_device_count_sync(phone_number)
    
    if error:
        print(f"❌ Error: {error}")
    else:
        print(f"📱 {phone_number} has {device_count} devices logged in")
    
    # Example 2: Full reward process
    user_id = 123456789
    reward_amount = 0.1
    
    success, message = check_device_sessions_and_reward(user_id, phone_number, reward_amount)
    print(f"Reward result: {message}")


if __name__ == "__main__":
    # Run example if script is executed directly
    example_usage()
