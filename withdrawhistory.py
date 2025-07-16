from db import get_withdrawals
from utils import require_channel_membership
from bot_init import bot
from db import get_user
from translations import get_text

@bot.message_handler(commands=['withdrawhistory'])
@require_channel_membership
def handle_withdrawhistory(message):
    user_id = message.from_user.id
    user = get_user(user_id) or {}
    lang = user.get('language', 'English')
    withdrawals = get_withdrawals(user_id)
    
    text = get_text('withdrawal_history_title', lang) + "\n\n"
    
    if not withdrawals:
        text += get_text('no_withdrawals', lang)
    else:
        for w in withdrawals:
            status = w['status']
            if lang == 'Arabic':
                status = {'pending': 'قيد الانتظار', 'approved': 'تمت الموافقة', 'rejected': 'مرفوض'}.get(status, status)
            elif lang == 'Chinese':
                status = {'pending': '待处理', 'approved': '已批准', 'rejected': '已拒绝'}.get(status, status)
            text += f"- {w['amount']}$ | {status} | {w['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
