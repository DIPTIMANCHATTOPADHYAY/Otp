from db import set_country_price
from config import ADMIN_IDS
from bot_init import bot

@bot.message_handler(commands=['setprice'])
def handle_setprice(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "Usage: /setprice <country_code> <price>\nExample: /setprice +91 0.20$")
        return
    country_code, price = parts[1], parts[2]
    try:
        if price.endswith('$'):
            price = price[:-1]
        price = float(price)
    except ValueError:
        bot.reply_to(message, "❌ Price must be a number (e.g. 0.20$).")
        return
    set_country_price(country_code, price)
    bot.reply_to(message, f"✅ Price for {country_code} set to {price}$.")
