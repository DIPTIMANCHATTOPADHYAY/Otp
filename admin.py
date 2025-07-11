from bot_init import bot
from config import ADMIN_IDS
from utils import require_channel_membership

@bot.message_handler(commands=['admin'])
@require_channel_membership
def handle_admin(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return

    admin_commands = [
        ("/admin", "Show this admin command list"),
        ("/add <code> <qty> <price> <sec> [name] [flag]", "Add/update country with all parameters"),
        ("/countries", "List all configured countries"),
        ("/pay <user_id>", "Approve withdrawal for specific user"),
        ("/paycard <card_name>", "Approve all withdrawals for a leader card"),
        ("/rejectpayment <user_id|card:name> [reason]", "Reject withdrawals with optional reason"),
        ("/cardw <card_name>", "Check withdrawal stats for a leader card"),
        ("/userdel <user_id>", "Delete user and all their data"),
        ("/cun <country_code> <quantity>", "Set country number capacity (legacy)"),
        ("/setprice <country_code> <price>", "Set price for a country (legacy)"),
        ("/settime <country_code> <seconds>", "Set claim time for a country (legacy)"),
        ("/numberd <country_code>", "Delete a country from the system"),
        ("/card <card_name>", "Add a new leader card"),
        ("/notice ", "Reply text All User Notification")
    ]

    response = "🔧 *Admin Command List* 🔧\n\n"
    for cmd, desc in admin_commands:
        response += f"• `{cmd}` - {desc}\n"

    bot.reply_to(message, response, parse_mode="Markdown")