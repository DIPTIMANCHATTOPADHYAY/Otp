from bot_init import bot
from config import ADMIN_IDS
from db import get_user
from utils import require_channel_membership
from pymongo import MongoClient
from config import MONGO_URI
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = MongoClient(MONGO_URI)
db = client['telegram_id_sell']  # Fixed database name to match db.py

@bot.message_handler(commands=['notice'])
@require_channel_membership
def handle_notice(message):
    # Check if user is admin
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    # Check if this is a reply to another message
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Please reply to the message you want to broadcast with /notice")
        return
    
    # Get the text/content to broadcast
    broadcast_message = message.reply_to_message.text or message.reply_to_message.caption
    if not broadcast_message:
        bot.reply_to(message, "❌ The message you replied to doesn't contain any text to broadcast.")
        return
    
    try:
        # Get all user IDs from the database
        all_users = db.users.find({}, {'user_id': 1})
        total_users = db.users.count_documents({})
        successful_sends = 0
        failed_sends = 0
        error_details = []
        
        # Send initial status
        status_msg = bot.reply_to(message, f"📢 Starting broadcast to {total_users} users...")
        
        # Send to each user
        for i, user in enumerate(all_users, 1):
            try:
                bot.send_message(user['user_id'], broadcast_message)
                successful_sends += 1
                logger.info(f"Successfully sent to user {user['user_id']}")
            except Exception as e:
                failed_sends += 1
                error_type = type(e).__name__
                error_msg = str(e)
                
                # Log specific error details
                if "Forbidden" in error_msg or "bot was blocked" in error_msg.lower():
                    error_details.append(f"User {user['user_id']}: Blocked bot")
                elif "chat not found" in error_msg.lower():
                    error_details.append(f"User {user['user_id']}: Chat not found")
                elif "user is deactivated" in error_msg.lower():
                    error_details.append(f"User {user['user_id']}: Deactivated account")
                elif "bot was stopped" in error_msg.lower():
                    error_details.append(f"User {user['user_id']}: Bot stopped")
                else:
                    error_details.append(f"User {user['user_id']}: {error_type} - {error_msg}")
                
                logger.warning(f"Failed to send to user {user['user_id']}: {error_type} - {error_msg}")
            
            # Update status every 10 users (more frequent updates)
            if i % 10 == 0 or i == total_users:
                try:
                    bot.edit_message_text(
                        f"📢 Broadcasting to {total_users} users...\n"
                        f"✅ Sent: {successful_sends}\n"
                        f"❌ Failed: {failed_sends}\n"
                        f"⏳ Progress: {i}/{total_users} ({int(i/total_users*100)}%)",
                        chat_id=status_msg.chat.id,
                        message_id=status_msg.message_id
                    )
                except:
                    pass
            
            # Small delay to avoid hitting rate limits
            time.sleep(0.05)  # Reduced delay for faster processing
        
        # Final report with error details
        final_report = (
            f"✅ Broadcast completed!\n"
            f"• Total users: {total_users}\n"
            f"• Successfully sent: {successful_sends}\n"
            f"• Failed sends: {failed_sends}\n"
            f"• Success rate: {int(successful_sends/total_users*100)}%"
        )
        
        # Add error details if there are failures
        if failed_sends > 0 and error_details:
            final_report += f"\n\n❌ **Failed sends details:**\n"
            # Show first 5 error details to avoid message too long
            for error in error_details[:5]:
                final_report += f"• {error}\n"
            if len(error_details) > 5:
                final_report += f"• ... and {len(error_details) - 5} more errors"
        
        bot.edit_message_text(
            final_report,
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error during broadcast: {str(e)}")
        bot.reply_to(message, f"❌ Error during broadcast: {str(e)}")

@bot.message_handler(commands=['cleanusers'])
@require_channel_membership
def handle_clean_users(message):
    """Identify and optionally remove users who have blocked the bot"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        # Get all users
        all_users = db.users.find({}, {'user_id': 1})
        total_users = db.users.count_documents({})
        blocked_users = []
        deactivated_users = []
        not_found_users = []
        other_errors = []
        
        status_msg = bot.reply_to(message, f"🔍 Checking {total_users} users for issues...")
        
        for i, user in enumerate(all_users, 1):
            try:
                # Try to send a test message
                bot.send_message(user['user_id'], "🔍 Test message - please ignore")
            except Exception as e:
                error_msg = str(e).lower()
                if "forbidden" in error_msg or "bot was blocked" in error_msg:
                    blocked_users.append(user['user_id'])
                elif "user is deactivated" in error_msg:
                    deactivated_users.append(user['user_id'])
                elif "chat not found" in error_msg:
                    not_found_users.append(user['user_id'])
                else:
                    other_errors.append((user['user_id'], str(e)))
            
            # Update progress
            if i % 10 == 0 or i == total_users:
                try:
                    bot.edit_message_text(
                        f"🔍 Checking users...\n"
                        f"⏳ Progress: {i}/{total_users} ({int(i/total_users*100)}%)\n"
                        f"🚫 Blocked: {len(blocked_users)}\n"
                        f"💀 Deactivated: {len(deactivated_users)}\n"
                        f"❓ Not found: {len(not_found_users)}",
                        chat_id=status_msg.chat.id,
                        message_id=status_msg.message_id
                    )
                except:
                    pass
            
            time.sleep(0.1)  # Slower for testing
        
        # Final report
        report = (
            f"🔍 **User Check Results:**\n\n"
            f"📊 **Total users checked**: {total_users}\n"
            f"🚫 **Blocked bot**: {len(blocked_users)}\n"
            f"💀 **Deactivated accounts**: {len(deactivated_users)}\n"
            f"❓ **Chat not found**: {len(not_found_users)}\n"
            f"⚠️ **Other errors**: {len(other_errors)}\n\n"
        )
        
        if blocked_users:
            report += f"🚫 **Blocked users**: {', '.join(map(str, blocked_users[:10]))}"
            if len(blocked_users) > 10:
                report += f" and {len(blocked_users) - 10} more"
            report += "\n\n"
        
        if deactivated_users:
            report += f"💀 **Deactivated users**: {', '.join(map(str, deactivated_users[:10]))}"
            if len(deactivated_users) > 10:
                report += f" and {len(deactivated_users) - 10} more"
            report += "\n\n"
        
        if not_found_users:
            report += f"❓ **Not found users**: {', '.join(map(str, not_found_users[:10]))}"
            if len(not_found_users) > 10:
                report += f" and {len(not_found_users) - 10} more"
            report += "\n\n"
        
        if other_errors:
            report += f"⚠️ **Other errors**:\n"
            for user_id, error in other_errors[:5]:
                report += f"• User {user_id}: {error}\n"
            if len(other_errors) > 5:
                report += f"• ... and {len(other_errors) - 5} more errors\n"
        
        report += f"\n💡 Use `/removeblocked` to remove blocked users from database"
        
        bot.edit_message_text(
            report,
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in clean_users: {str(e)}")
        bot.reply_to(message, f"❌ Error checking users: {str(e)}")

@bot.message_handler(commands=['removeblocked'])
@require_channel_membership
def handle_remove_blocked(message):
    """Remove users who have blocked the bot from the database"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        # Get all users
        all_users = db.users.find({}, {'user_id': 1})
        blocked_users = []
        
        status_msg = bot.reply_to(message, "🔍 Finding blocked users...")
        
        for i, user in enumerate(all_users, 1):
            try:
                # Try to send a test message
                bot.send_message(user['user_id'], "🔍 Test message - please ignore")
            except Exception as e:
                error_msg = str(e).lower()
                if "forbidden" in error_msg or "bot was blocked" in error_msg:
                    blocked_users.append(user['user_id'])
            
            # Update progress every 20 users
            if i % 20 == 0:
                try:
                    bot.edit_message_text(
                        f"🔍 Finding blocked users...\n"
                        f"⏳ Progress: {i} users checked\n"
                        f"🚫 Found blocked: {len(blocked_users)}",
                        chat_id=status_msg.chat.id,
                        message_id=status_msg.message_id
                    )
                except:
                    pass
            
            time.sleep(0.05)
        
        if not blocked_users:
            bot.edit_message_text(
                "✅ No blocked users found! All users are reachable.",
                chat_id=status_msg.chat.id,
                message_id=status_msg.message_id
            )
            return
        
        # Remove blocked users
        removed_count = 0
        for user_id in blocked_users:
            try:
                result = db.users.delete_one({"user_id": user_id})
                if result.deleted_count > 0:
                    removed_count += 1
            except Exception as e:
                logger.error(f"Error removing user {user_id}: {str(e)}")
        
        bot.edit_message_text(
            f"✅ **Blocked Users Cleanup Complete!**\n\n"
            f"🚫 **Found blocked users**: {len(blocked_users)}\n"
            f"🗑️ **Successfully removed**: {removed_count}\n"
            f"❌ **Failed to remove**: {len(blocked_users) - removed_count}\n\n"
            f"💡 Your next broadcast should have better success rate!",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in remove_blocked: {str(e)}")
        bot.reply_to(message, f"❌ Error removing blocked users: {str(e)}")