import re
from db import set_country_claim_time
from config import ADMIN_IDS
from bot_init import bot

SETTIME_REGEX = re.compile(r'^/settime\s+(\+\d{1,5})\s+(\d+)s$', re.IGNORECASE)

@bot.message_handler(commands=['settime'])
def handle_settime(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    match = SETTIME_REGEX.match(message.text)
    if not match:
        bot.reply_to(message, "Usage: /settime <country_code> <seconds>s\nExample: /settime +91 600s")
        return
    country_code, seconds = match.groups()
    try:
        seconds = int(seconds)
    except ValueError:
        bot.reply_to(message, "❌ Time must be a number of seconds (e.g. 600s).")
        return
    set_country_claim_time(country_code, seconds)
    bot.reply_to(message, f"✅ Claim time for {country_code} set to {seconds} seconds.")
