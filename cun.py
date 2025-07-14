from db import set_country_capacity
from config import ADMIN_IDS
from bot_init import bot
from cap import get_country_info

@bot.message_handler(commands=['cun'])
def handle_cun(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "Usage: /cun <country_code> <quantity>\nExample: /cun +91 100")
        return
    country_code, quantity = parts[1], parts[2]
    try:
        quantity = int(quantity)
    except ValueError:
        bot.reply_to(message, "❌ Quantity must be a number.")
        return
    info = get_country_info(country_code)
    set_country_capacity(country_code, quantity, info['name'], info['flag'])
    bot.reply_to(message, f"✅ Capacity for {info['flag']}{info['name']} ({country_code}) set to {quantity}.")
