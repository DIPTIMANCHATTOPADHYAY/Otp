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
#import verification_flow

def main():
    print("Bot is running...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot crashed: {str(e)}")
        # Add any cleanup or restart logic here

if __name__ == "__main__":
    main()