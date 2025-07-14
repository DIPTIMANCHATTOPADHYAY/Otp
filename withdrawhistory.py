from db import get_withdrawals
from utils import require_channel_membership
from bot_init import bot
from db import get_user

@bot.message_handler(commands=['withdrawhistory'])
@require_channel_membership
def handle_withdrawhistory(message):
    user_id = message.from_user.id
    user = get_user(user_id) or {}
    lang = user.get('language', 'English')
    withdrawals = get_withdrawals(user_id)
    texts = {
        'English': "🏛️ *Your withdrawals requests:*\n",
        'Arabic': "🏛️ *طلبات السحب الخاصة بك:*\n",
        'Chinese': "🏛️ *您的提现请求：*\n"
    }
    text = texts.get(lang, texts['English'])
    if not withdrawals:
        no_withdrawals = {
            'English': "No withdrawals yet.",
            'Arabic': "لا توجد طلبات سحب بعد.",
            'Chinese': "还没有提现记录。"
        }
        text += no_withdrawals.get(lang, no_withdrawals['English'])
    else:
        for w in withdrawals:
            status = w['status']
            if lang == 'Arabic':
                status = {'pending': 'قيد الانتظار', 'approved': 'تمت الموافقة', 'rejected': 'مرفوض'}.get(status, status)
            elif lang == 'Chinese':
                status = {'pending': '待处理', 'approved': '已批准', 'rejected': '已拒绝'}.get(status, status)
            text += f"- {w['amount']}$ | {status} | {w['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
