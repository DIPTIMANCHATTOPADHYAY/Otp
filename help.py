from bot_init import bot
from utils import require_channel_membership

@bot.message_handler(commands=['help'])
@require_channel_membership
def handle_help(message):
    help_text = (
        "🆘 *Help & Support* 🆘\n\n"
        "If you need assistance, please contact our support team:\n"
        "👉 @TGVIPRECEIVER\n\n"
        "Common commands:\n"
        "/account - View your account information\n"
        "/withdraw - Request a withdrawal\n"
        "/withdrawhistory - View your withdrawal history\n"
        "/cap - View available countries and capacities"
    )
    
    bot.reply_to(message, help_text, parse_mode="Markdown")