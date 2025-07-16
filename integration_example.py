"""
Integration Example: Device Session Checking with OTP System
This shows how to integrate device session checking into the existing OTP verification process.
"""

# Add this import to the top of otp.py
from device_sessions import check_device_sessions_and_reward, get_device_count_sync

def enhanced_process_successful_verification(user_id, phone_number):
    """
    Enhanced version of process_successful_verification that includes device session checking.
    This replaces the device count checking logic in the background reward process.
    """
    try:
        user = get_user(user_id) or {}
        lang = user.get('language', 'English')
        
        if check_number_used(phone_number):
            bot.send_message(user_id, TRANSLATIONS['number_claimed'][lang])
            return

        country = get_country_by_code(user.get("country_code", phone_number[:3]))
        
        if not country:
            bot.send_message(user_id, TRANSLATIONS['country_data_missing'][lang])
            return

        # Finalize session and get configuration
        session_manager.finalize_session(user_id)
        claim_time = country.get("claim_time", 600)
        price = country.get("price", 0.1)

        # Send immediate success message
        msg = bot.send_message(
            user_id,
            TRANSLATIONS['account_received'][lang].format(phone=phone_number, price=price, claim_time=claim_time),
            parse_mode="Markdown"
        )

        # Add pending number record
        pending_id = add_pending_number(user_id, phone_number, price, claim_time)

        # Enhanced Background Reward Process with Device Session Checking
        def enhanced_background_reward_process():
            # Create cancellation event for this thread
            cancel_event = threading.Event()
            
            # Register this thread for cancellation tracking
            with thread_lock:
                background_threads[user_id] = {
                    "thread": threading.current_thread(),
                    "cancel_event": cancel_event,
                    "phone": phone_number
                }
            
            try:
                # Wait (claim_time - 10 seconds) with cancellation checks
                wait_time = max(10, claim_time - 10)
                print(f"⏳ Starting enhanced background validation for {phone_number} in {wait_time} seconds")
                
                # Sleep in small intervals to check for cancellation
                sleep_interval = 2  # Check every 2 seconds
                elapsed = 0
                while elapsed < wait_time:
                    if cancel_event.is_set():
                        print(f"🛑 Background verification cancelled for {phone_number} (User: {user_id})")
                        cleanup_cancelled_verification(user_id, phone_number, msg, pending_id, lang)
                        return  # Exit the background process
                    
                    sleep_time = min(sleep_interval, wait_time - elapsed)
                    time.sleep(sleep_time)
                    elapsed += sleep_time
                
                # Check one more time before validation
                if cancel_event.is_set():
                    print(f"🛑 Background verification cancelled just before validation for {phone_number}")
                    cleanup_cancelled_verification(user_id, phone_number, msg, pending_id, lang)
                    return
                
                # Validate session (basic session validation)
                print(f"🔍 Starting session validation for {phone_number}")
                try:
                    valid, reason = session_manager.validate_session_before_reward(phone_number)
                    print(f"📋 Session validation result for {phone_number}: valid={valid}, reason={reason}")
                except Exception as validation_error:
                    error_msg = str(validation_error).lower()
                    print(f"❌ Session validation exception for {phone_number}: {str(validation_error)}")
                    if "database is locked" in error_msg or "database" in error_msg:
                        print(f"🔄 Database locking detected - treating as validation success")
                        valid, reason = True, None
                    else:
                        print(f"❌ Treating validation exception as failure")
                        valid, reason = False, f"Validation error: {str(validation_error)}"

                if not valid:
                    print(f"❌ Session validation failed for {phone_number}: {reason}")
                    update_pending_number_status(pending_id, "failed")
                    
                    try:
                        bot.edit_message_text(
                            f"❌ *Verification Failed*\n\n"
                            f"📞 Number: `{phone_number}`\n"
                            f"❌ Reason: {reason}\n"
                            f"🔄 You can try this number again",
                            user_id,
                            msg.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        print(f"Failed to edit message: {edit_error}")
                        bot.send_message(
                            user_id,
                            f"❌ *Verification Failed*\n\n"
                            f"📞 Number: `{phone_number}`\n"
                            f"❌ Reason: {reason}\n"
                            f"🔄 You can try this number again",
                            parse_mode="Markdown"
                        )
                    return

                # NEW: Enhanced Device Session Checking and Reward Process
                print(f"🔍 Starting enhanced device session checking for {phone_number}")
                
                try:
                    # Use the new device session checker
                    success, result_message = check_device_sessions_and_reward(user_id, phone_number, price)
                    
                    if success:
                        # Device session check passed and reward was given
                        print(f"✅ Device session check passed for {phone_number}")
                        
                        # Mark number as used (success)
                        mark_number_as_used(phone_number, user_id)
                        update_pending_number_status(pending_id, "completed")
                        
                        # Update success message with device info
                        try:
                            device_count, _ = get_device_count_sync(phone_number)
                            bot.edit_message_text(
                                f"✅ *Verification Successful*\n\n"
                                f"📞 Number: `{phone_number}`\n"
                                f"📱 Device Count: {device_count}\n"
                                f"💰 Reward: ${price}\n"
                                f"✅ Payment added to your balance!",
                                user_id,
                                msg.message_id,
                                parse_mode="Markdown"
                            )
                        except Exception as edit_error:
                            print(f"Failed to edit success message: {edit_error}")
                            bot.send_message(
                                user_id,
                                f"✅ Verification successful! ${price} added to your balance.",
                                parse_mode="Markdown"
                            )
                        
                        # Send detailed reward notification
                        bot.send_message(
                            user_id,
                            result_message,
                            parse_mode="Markdown"
                        )
                        
                    else:
                        # Device session check failed - multiple devices detected
                        print(f"❌ Device session check failed for {phone_number}")
                        
                        # Update pending number status but don't mark as used
                        update_pending_number_status(pending_id, "device_check_failed")
                        
                        # Update message with failure info
                        try:
                            device_count, _ = get_device_count_sync(phone_number)
                            bot.edit_message_text(
                                f"🚫 *Reward Blocked*\n\n"
                                f"📞 Number: `{phone_number}`\n"
                                f"📱 Device Count: {device_count}\n"
                                f"❌ Multiple devices detected\n"
                                f"🔄 Number remains available for retry",
                                user_id,
                                msg.message_id,
                                parse_mode="Markdown"
                            )
                        except Exception as edit_error:
                            print(f"Failed to edit failure message: {edit_error}")
                            bot.send_message(
                                user_id,
                                f"🚫 No reward given - multiple devices detected on {phone_number}",
                                parse_mode="Markdown"
                            )
                        
                        # Send detailed explanation
                        bot.send_message(
                            user_id,
                            result_message,
                            parse_mode="Markdown"
                        )
                
                except Exception as device_check_error:
                    print(f"❌ Device session check error for {phone_number}: {device_check_error}")
                    
                    # Update pending number status
                    update_pending_number_status(pending_id, "error")
                    
                    # Notify user of technical error
                    try:
                        bot.edit_message_text(
                            f"⚠️ *Technical Error*\n\n"
                            f"📞 Number: `{phone_number}`\n"
                            f"❌ Could not verify device status\n"
                            f"🔄 Please try again later",
                            user_id,
                            msg.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        print(f"Failed to edit error message: {edit_error}")
                        bot.send_message(
                            user_id,
                            f"⚠️ Technical error during device verification for {phone_number}",
                            parse_mode="Markdown"
                        )
                
            except Exception as e:
                print(f"❌ Critical error in enhanced background process for {phone_number}: {e}")
                update_pending_number_status(pending_id, "error")
            finally:
                # Clean up thread tracking
                with thread_lock:
                    background_threads.pop(user_id, None)
                print(f"🧹 Enhanced background thread cleanup completed for {phone_number}")

        # Start the enhanced background thread
        thread = threading.Thread(target=enhanced_background_reward_process, daemon=True)
        thread.start()
        print(f"🚀 Enhanced background verification started for {phone_number}")

    except Exception as e:
        print(f"❌ Error in enhanced_process_successful_verification: {e}")
        bot.send_message(user_id, "⚠️ System error. Please try again.")


# Command to manually check device count for testing
@bot.message_handler(commands=['checkdevices'])
def handle_check_devices_command(message):
    """Admin command to manually check device count for a phone number"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Admin access required")
        return
    
    try:
        # Extract phone number from command
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "Usage: /checkdevices +1234567890")
            return
        
        phone_number = parts[1]
        
        # Check device count
        device_count, error = get_device_count_sync(phone_number)
        
        if error:
            bot.reply_to(message, f"❌ Error: {error}")
        else:
            # Check reward eligibility
            from device_sessions import DeviceSessionChecker
            checker = DeviceSessionChecker()
            is_eligible, reason = checker.check_reward_eligibility(device_count)
            
            status = "✅ ELIGIBLE FOR REWARD" if is_eligible else "❌ NOT ELIGIBLE FOR REWARD"
            
            response = (
                f"📱 *Device Check Results*\n\n"
                f"📞 Phone: `{phone_number}`\n"
                f"📱 Device Count: {device_count}\n"
                f"🎯 Status: {status}\n"
                f"📋 Reason: {reason}"
            )
            
            bot.reply_to(message, response, parse_mode="Markdown")
    
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


# Command to test device session reward system
@bot.message_handler(commands=['testdevicereward'])
def handle_test_device_reward_command(message):
    """Admin command to test device session reward system"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Admin access required")
        return
    
    try:
        # Extract phone number and amount from command
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "Usage: /testdevicereward +1234567890 0.1")
            return
        
        phone_number = parts[1]
        reward_amount = float(parts[2])
        user_id = message.from_user.id
        
        # Test the device session reward system
        success, result_message = check_device_sessions_and_reward(user_id, phone_number, reward_amount)
        
        status = "✅ SUCCESS" if success else "❌ FAILED"
        
        response = (
            f"🧪 *Device Reward Test Results*\n\n"
            f"📞 Phone: `{phone_number}`\n"
            f"💰 Test Amount: ${reward_amount}\n"
            f"🎯 Result: {status}\n\n"
            f"📋 Details:\n{result_message}"
        )
        
        bot.reply_to(message, response, parse_mode="Markdown")
    
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


"""
INTEGRATION INSTRUCTIONS:

1. Replace the existing process_successful_verification function with enhanced_process_successful_verification
2. Add the new admin commands to your bot command handlers
3. The system will automatically:
   - Check device count after session validation
   - Give reward only if exactly 1 device is logged in
   - Block reward if 2-100 devices are logged in
   - Log all transactions to database
   - Provide detailed feedback to users

4. Test with admin commands:
   /checkdevices +1234567890 - Check device count for a number
   /testdevicereward +1234567890 0.1 - Test full reward process
"""
