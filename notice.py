from bot_init import bot
from config import ADMIN_IDS
from db import get_user
from utils import require_channel_membership
from pymongo import MongoClient
from config import MONGO_URI
import time  # Added missing import

client = MongoClient(MONGO_URI)
db = client['telegram_otp_bot_test']

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
        
        # Send initial status
        status_msg = bot.reply_to(message, f"📢 Starting broadcast to {total_users} users...")
        
        # Send to each user
        for i, user in enumerate(all_users, 1):
            try:
                bot.send_message(user['user_id'], broadcast_message)
                successful_sends += 1
            except Exception as e:
                failed_sends += 1
            
            # Update status every 50 users
            if i % 50 == 0 or i == total_users:
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
            time.sleep(0.1)
        
        # Final report
        bot.edit_message_text(
            f"✅ Broadcast completed!\n"
            f"• Total users: {total_users}\n"
            f"• Successfully sent: {successful_sends}\n"
            f"• Failed sends: {failed_sends}\n"
            f"• Success rate: {int(successful_sends/total_users*100)}%",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error during broadcast: {str(e)}")