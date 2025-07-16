import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from bot_init import bot
import start
import account
import cap
import withdraw
import withdrawhistory
import cun
import setprice
import settime
import numberd
import cancel
import otp
import userdel
import pay
import card
import paycard
import cardw
import rejectpayment
import admin
import notice
import help
import add_country
import admin_sessions
import admin_delete_sessions
import device_sessions
import admin_device_check
import threading
from flask import Flask, jsonify

# Create Flask app for health checks
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Telegram Bot is running", "status": "active"})

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def main():
    print("Bot is running...")
    
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot crashed: {str(e)}")
        # Add any cleanup or restart logic here

if __name__ == "__main__":
    main()