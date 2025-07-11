from db import remove_country_by_code
from config import ADMIN_IDS
from bot_init import bot

@bot.message_handler(commands=['numberd'])
def handle_numberd(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /numberd <country_code>\nExample: /numberd +91")
        return
    country_code = parts[1]
    removed = remove_country_by_code(country_code)
    if removed:
        bot.reply_to(message, f"✅ Country {country_code} has been removed.")
    else:
        bot.reply_to(message, f"❌ Country {country_code} not found.")
