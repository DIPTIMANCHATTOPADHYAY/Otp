from bot_init import bot
from config import ADMIN_IDS
from utils import require_channel_membership
from db import set_country_capacity, set_country_price, set_country_claim_time, get_country_by_code
import re

@bot.message_handler(commands=['add'])
@require_channel_membership
def handle_add_country(message):
    """
    Add a new country with all parameters in one command
    Usage: /add <country_code> <quantity> <price> <seconds> [name] [flag]
    Example: /add +1 100 5.50 300 "United States" 🇺🇸
    """
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return

    # Parse command arguments
    args = message.text.split(None, 6)  # Split into max 7 parts
    
    if len(args) < 5:  # Minimum: /add country_code quantity price seconds
        usage_msg = (
            "🔧 **Add Country Command Usage**\n\n"
            "`/add <country_code> <quantity> <price> <seconds> [name] [flag]`\n\n"
            "**Parameters:**\n"
            "• `country_code` - Country code (e.g., +1, +58, +44)\n"
            "• `quantity` - Number capacity (e.g., 100)\n"  
            "• `price` - Price per number (e.g., 5.50)\n"
            "• `seconds` - Claim time in seconds (e.g., 300)\n"
            "• `name` - Optional country name (e.g., \"United States\")\n"
            "• `flag` - Optional flag emoji (e.g., 🇺🇸)\n\n"
            "**Examples:**\n"
            "`/add +1 100 5.50 300`\n"
            "`/add +58 50 3.25 600 \"Venezuela\" 🇻🇪`\n"
            "`/add +44 75 4.00 450 \"United Kingdom\" 🇬🇧`"
        )
        bot.reply_to(message, usage_msg, parse_mode="Markdown")
        return

    try:
        # Extract required parameters
        country_code = args[1].strip()
        quantity = int(args[2])
        price = float(args[3])
        seconds = int(args[4])
        
        # Validate country code format
        if not re.match(r'^\+\d{1,4}$', country_code):
            bot.reply_to(message, "❌ Invalid country code format. Use format like +1, +58, +44")
            return
        
        # Validate ranges
        if quantity <= 0:
            bot.reply_to(message, "❌ Quantity must be greater than 0")
            return
            
        if price <= 0:
            bot.reply_to(message, "❌ Price must be greater than 0")
            return
            
        if seconds <= 0:
            bot.reply_to(message, "❌ Claim time must be greater than 0 seconds")
            return
        
        # Extract optional parameters
        name = None
        flag = None
        
        if len(args) >= 6:
            # Extract name (remove quotes if present)
            name = args[5].strip().strip('"').strip("'")
            if name == "":
                name = None
        
        if len(args) >= 7:
            # Extract flag emoji
            flag = args[6].strip()
            # Basic validation for emoji/flag
            if len(flag) > 10:  # Flags are usually 1-4 characters
                flag = flag[:10]  # Truncate if too long
        
        # Check if country already exists
        existing = get_country_by_code(country_code)
        is_update = existing is not None
        
        # Set all country parameters
        success_capacity = set_country_capacity(country_code, quantity, name, flag)
        success_price = set_country_price(country_code, price)
        success_time = set_country_claim_time(country_code, seconds)
        
        if success_capacity and success_price and success_time:
            # Prepare response message
            action = "updated" if is_update else "added"
            
            response = f"✅ **Country {action} successfully!**\n\n"
            response += f"🌍 **Country Code:** `{country_code}`\n"
            response += f"📊 **Quantity:** `{quantity:,}` numbers\n"
            response += f"💰 **Price:** `${price:.2f}` per number\n"
            response += f"⏱️ **Claim Time:** `{seconds}` seconds\n"
            
            if name:
                response += f"🏷️ **Name:** {name}\n"
            if flag:
                response += f"🏁 **Flag:** {flag}\n"
            
            if is_update:
                response += f"\n📝 **Note:** Country was updated with new values"
            else:
                response += f"\n🎉 **Note:** New country added to the system"
            
            bot.reply_to(message, response, parse_mode="Markdown")
            
            # Log the action
            print(f"✅ Admin {user_id} {action} country {country_code}: {quantity} numbers, ${price:.2f}, {seconds}s")
            
        else:
            bot.reply_to(message, "❌ Failed to add/update country. Please check database connection.")
            print(f"❌ Failed to add country {country_code}: capacity={success_capacity}, price={success_price}, time={success_time}")
    
    except ValueError as ve:
        if "invalid literal" in str(ve).lower():
            bot.reply_to(message, "❌ Invalid number format. Please check quantity, price, and seconds values.")
        else:
            bot.reply_to(message, f"❌ Value error: {str(ve)}")
    except Exception as e:
        bot.reply_to(message, f"❌ Error adding country: {str(e)}")
        print(f"❌ Error in add_country command: {str(e)}")

@bot.message_handler(commands=['countries'])
@require_channel_membership  
def handle_list_countries(message):
    """
    List all configured countries
    """
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        from db import get_country_capacities
        countries = get_country_capacities()
        
        if not countries:
            bot.reply_to(message, "📭 No countries configured yet. Use `/add` to add countries.", parse_mode="Markdown")
            return
        
        response = "🌍 **Configured Countries:**\n\n"
        
        # Sort countries by country code
        countries.sort(key=lambda x: x.get('country_code', ''))
        
        for country in countries:
            country_code = country.get('country_code', 'Unknown')
            capacity = country.get('capacity', 0)
            price = country.get('price', 0.0)
            claim_time = country.get('claim_time', 0)
            name = country.get('name', '')
            flag = country.get('flag', '')
            
            line = f"• `{country_code}`"
            
            if name or flag:
                line += f" {flag} {name}".strip()
            
            line += f"\n  └ {capacity:,} numbers, ${price:.2f}, {claim_time}s\n"
            
            response += line
        
        response += f"\n📊 **Total:** {len(countries)} countries configured"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error listing countries: {str(e)}")
        print(f"❌ Error in list_countries command: {str(e)}")