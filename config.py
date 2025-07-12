import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API
API_ID = int(os.getenv('API_ID', 20094764))
API_HASH = os.getenv('API_HASH', 'ac33c77cfdbe4f94ebd73dde27b4a10c')
BOT_TOKEN = os.getenv('BOT_TOKEN', '7246099288:AAGEgP5hFkY3NJicptMgHInQ1APDTMBJT8M')

# OTP Settings
DEFAULT_2FA_PASSWORD = os.getenv('DEFAULT_2FA_PASSWORD', '112233')

# Database
MONGO_URI = os.getenv('MONGO_URI', "mongodb+srv://noob:K3a4ofLngiMG8Hl9@tele.fjm9acq.mongodb.net/?retryWrites=true&w=majority")

# Channels
REQUESTED_CHANNEL = os.getenv('REQUESTED_CHANNEL', "@TGVIPR")
WITHDRAWAL_LOG_CHAT_ID = int(os.getenv('WITHDRAWAL_LOG_CHAT_ID', -1002626888395))
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '1211362365').split(',')]

# Directories
SESSIONS_DIR = os.getenv('SESSIONS_DIR', "sessions")
VERIFIED_DIR = os.getenv('SESSIONS_DIR', "verified")

os.makedirs(SESSIONS_DIR, exist_ok=True)