# 📱 Telegram OTP Verification Bot

A sophisticated Telegram bot for phone number verification with OTP (One-Time Password) functionality, country-specific pricing, and automated session management.

## 🚀 Features

### Core Functionality
- **Phone Number Verification**: Support for multiple countries with custom pricing
- **OTP Processing**: Real-time SMS verification code handling  
- **2FA Management**: Automatic two-factor authentication setup
- **Session Management**: Secure Telegram session handling with cleanup
- **Background Verification**: Automated validation with cancellation support
- **Payment System**: User balance management and withdrawal processing

### Admin Features
- **Country Management**: Add/update countries with pricing and capacity
- **User Management**: User data and balance administration
- **Withdrawal Processing**: Approve/reject withdrawal requests
- **Leader Card System**: Group withdrawal management
- **Real-time Monitoring**: Command logging and error tracking

### Security Features
- **Database Locking Protection**: Multi-layer fallback validation system
- **Session Cleanup**: Automatic disconnection and data cleanup
- **Number Hash Storage**: Privacy-protected number usage tracking
- **Admin Authorization**: Role-based command access control

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- MongoDB database
- Telegram Bot Token
- Telegram API credentials (API_ID, API_HASH)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd telegram-otp-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create a `.env` file (see `.env.example` for reference):
   ```env
   BOT_TOKEN=your_bot_token_here
   API_ID=your_api_id
   API_HASH=your_api_hash
   DEFAULT_2FA_PASSWORD=112233
   MONGO_URI=your_mongodb_connection_string
   ADMIN_IDS=admin_user_id_1,admin_user_id_2
   REQUESTED_CHANNEL=@your_channel
   WITHDRAWAL_LOG_CHAT_ID=your_log_chat_id
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

## 📋 Commands

### User Commands
- `/start` - Begin phone verification process
- `/cancel` - Cancel current verification (works at any stage)
- `/account` - View account balance and statistics
- `/withdraw` - Request balance withdrawal
- `/help` - Show help information

### Admin Commands
- `/add <code> <qty> <price> <sec> [name] [flag]` - Add/update country configuration
- `/countries` - List all configured countries
- `/pay <user_id>` - Approve user withdrawal
- `/paycard <card_name>` - Approve all withdrawals for a leader card
- `/rejectpayment <user_id|card:name> [reason]` - Reject withdrawals
- `/userdel <user_id>` - Delete user and all data
- `/numberd <country_code>` - Remove country from system
- `/card <card_name>` - Add new leader card
- `/notice <message>` - Send notification to all users

### Legacy Admin Commands
- `/cun <country_code> <quantity>` - Set country capacity (use `/add` instead)
- `/setprice <country_code> <price>` - Set country price (use `/add` instead)  
- `/settime <country_code> <seconds>` - Set claim time (use `/add` instead)

## 🌍 Country Management

### Adding Countries
Use the new `/add` command for comprehensive country setup:

```bash
# Basic setup
/add +1 100 5.50 300

# With country name and flag
/add +58 50 3.25 600 "Venezuela" 🇻🇪

# Full example
/add +44 75 4.00 450 "United Kingdom" 🇬🇧
```

### Parameters
- **Country Code**: International format (+1, +58, +44, etc.)
- **Quantity**: Number of available phone numbers
- **Price**: Cost per number verification (USD)
- **Seconds**: Time limit for verification process
- **Name**: Optional country name for display
- **Flag**: Optional emoji flag for visual identification

## 🔄 Verification Flow

1. **Phone Input**: User provides phone number
2. **OTP Request**: System sends verification code via SMS
3. **Code Verification**: User enters received OTP code
4. **2FA Setup**: Automatic two-factor authentication configuration
5. **Background Validation**: Final session verification (cancellable)
6. **Reward Distribution**: User receives payment upon completion

## 🗄️ Database Schema

### Collections
- **users**: User profiles, balances, and statistics
- **countries**: Country configurations and pricing
- **pending_numbers**: Active verification sessions
- **used_numbers**: Hashed phone number usage tracking
- **withdrawals**: Withdrawal requests and history
- **leader_cards**: Group withdrawal management

## 🛡️ Error Handling

### Database Locking Protection
The bot includes comprehensive protection against database locking errors:

- **Primary Validation**: File-based session checks (no database access)
- **Secondary Validation**: Safe Telethon connection testing  
- **Fallback Mode**: Error recovery with graceful degradation
- **Emergency Bypass**: Ensures users never get permanently blocked

### Session Management
- **Automatic Cleanup**: Session files and connections properly closed
- **Cancellation Support**: Users can cancel at any verification stage
- **Background Process Control**: Long-running tasks can be interrupted
- **Thread Safety**: Proper locking and cleanup mechanisms

## 📊 Monitoring & Logging

- **Command Logging**: All admin actions logged with timestamps
- **Error Tracking**: Comprehensive error reporting and handling
- **Performance Monitoring**: Database operation success tracking
- **User Activity**: Verification attempts and completion rates

## 🔧 Configuration

### Environment Variables
| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `BOT_TOKEN` | Telegram Bot API token | Yes | - |
| `API_ID` | Telegram API application ID | Yes | - |
| `API_HASH` | Telegram API application hash | Yes | - |
| `DEFAULT_2FA_PASSWORD` | Default 2FA password for accounts | No | `112233` |
| `MONGO_URI` | MongoDB connection string | Yes | - |
| `ADMIN_IDS` | Comma-separated admin user IDs | Yes | - |
| `REQUESTED_CHANNEL` | Required channel for bot usage | No | - |
| `WITHDRAWAL_LOG_CHAT_ID` | Chat for withdrawal notifications | No | - |

### Directory Structure
```
telegram-otp-bot/
├── main.py              # Bot entry point
├── bot_init.py          # Bot initialization
├── config.py            # Configuration management
├── db.py                # Database operations
├── telegram_otp.py      # Core OTP functionality
├── otp.py               # OTP processing logic
├── cancel.py            # Cancellation handling
├── add_country.py       # NEW: Country management
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables
├── .env.example         # Configuration template
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## 🚀 Recent Updates

### Version 2.0 Features
- **NEW**: `/add` command for comprehensive country management
- **NEW**: `/countries` command to list all configured countries
- **NEW**: Configurable 2FA password via environment variables
- **ENHANCED**: Database locking protection with 4-layer fallback system
- **ENHANCED**: Complete cancellation support including background processes
- **ENHANCED**: Thread-safe session management with proper cleanup
- **FIXED**: Venezuela and all country codes now fully supported
- **OPTIMIZED**: Removed unnecessary documentation and test files

## 📝 License

This project is proprietary software. All rights reserved.

## 🤝 Support

For technical support or questions, contact the development team.

---

**Made with ❤️ for secure phone verification**