from datetime import datetime
from utils import require_channel_membership
from db import get_user
from bot_init import bot
import telebot

@bot.message_handler(commands=['account'])
@require_channel_membership
def handle_account(message):
    user_id = message.from_user.id
    user = get_user(user_id) or {}
    name = user.get('name', message.from_user.first_name)
    sent_accounts = user.get('sent_accounts', 0)
    balance = user.get('balance', 0.0)
    registered_at = user.get('registered_at', datetime.utcnow())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lang = user.get('language', 'English')
    texts = {
        'English': (
            "🌟 *Account Information* 🌟\n\n"
            f"👤 *Name*: {name}\n"
            f"🆔 *User ID*: {user_id}\n"
            f"📅 *Registered*: {registered_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"📊 Number of sent accounts: {sent_accounts}\n"
            f"💰 Balance that can be settled: {balance} $\n\n"
            f"⏰ *Time Now*: {now}\n\n"
            f"Withdraw: /withdraw\n"
            f"Withdraw history: /withdrawhistory"
        ),
        'Arabic': (
            "🌟 *معلومات الحساب* 🌟\n\n"
            f"👤 *الاسم*: {name}\n"
            f"🆔 *معرف المستخدم*: {user_id}\n"
            f"📅 *تاريخ التسجيل*: {registered_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"📊 عدد الحسابات المرسلة: {sent_accounts}\n"
            f"💰 الرصيد القابل للسحب: {balance} $\n\n"
            f"⏰ *الوقت الحالي*: {now}\n\n"
            f"سحب: /withdraw\n"
            f"تاريخ السحب: /withdrawhistory"
        ),
        'Chinese': (
            "🌟 *账户信息* 🌟\n\n"
            f"👤 *姓名*: {name}\n"
            f"🆔 *用户ID*: {user_id}\n"
            f"📅 *注册时间*: {registered_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"📊 已发送账户数: {sent_accounts}\n"
            f"💰 可结算余额: {balance} $\n\n"
            f"⏰ *当前时间*: {now}\n\n"
            f"提现: /withdraw\n"
            f"提现历史: /withdrawhistory"
        )
    }
    text = texts.get(lang, texts['English'])
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(
        text={
            'English': 'Withdraw',
            'Arabic': 'سحب',
            'Chinese': '提现'
        }.get(lang, 'Withdraw'),
        callback_data='account_withdraw')
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'account_withdraw')
def handle_account_withdraw_callback(call):
    # Simulate /withdraw command trigger
    from withdraw import handle_withdraw
    class DummyMessage:
        def __init__(self, call):
            self.from_user = call.from_user
            self.chat = call.message.chat
            self.message_id = call.message.message_id
            self.text = '/withdraw'
    handle_withdraw(DummyMessage(call))
    bot.answer_callback_query(call.id)