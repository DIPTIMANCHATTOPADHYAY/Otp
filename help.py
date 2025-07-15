from bot_init import bot
from utils import require_channel_membership
from translations import TRANSLATIONS

@bot.message_handler(commands=['help'])
@require_channel_membership
def handle_help(message):
    user_id = message.from_user.id
    from db import get_user
    user = get_user(user_id) or {}
    lang = user.get('language', 'English')
    help_text = TRANSLATIONS['help_support'][lang]
    bot.reply_to(message, help_text, parse_mode="Markdown")