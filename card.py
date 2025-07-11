from bot_init import bot
from config import ADMIN_IDS
from db import add_leader_card
from utils import require_channel_membership

@bot.message_handler(commands=['card'])
@require_channel_membership
def handle_card(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /card <card_name>")
        return
    card_name = parts[1].strip()
    add_leader_card(card_name)
    bot.reply_to(message, f"✅ Leader card '{card_name}' has been added.")
