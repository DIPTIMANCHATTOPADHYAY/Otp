#!/bin/bash

# Telegram Bot Koyeb Deployment Script

echo "🚀 Starting Telegram Bot deployment to Koyeb..."

# Check if Koyeb CLI is installed
if ! command -v koyeb &> /dev/null; then
    echo "❌ Koyeb CLI not found. Installing..."
    curl -fsSL https://cli.koyeb.com/install.sh | bash
    echo "✅ Koyeb CLI installed successfully"
else
    echo "✅ Koyeb CLI found"
fi

# Check if logged in
if ! koyeb whoami &> /dev/null; then
    echo "🔐 Please login to Koyeb..."
    koyeb login
else
    echo "✅ Already logged in to Koyeb"
fi

# Deploy the application
echo "📦 Deploying application to Koyeb..."
koyeb app init telegram-bot \
    --docker . \
    --ports 8080:http \
    --env API_ID=20094764 \
    --env API_HASH=ac33c77cfdbe4f94ebd73dde27b4a10c \
    --env BOT_TOKEN=7246099288:AAGEgP5hFkY3NJicptMgHInQ1APDTMBJT8M \
    --env DEFAULT_2FA_PASSWORD=112233 \
    --env MONGO_URI="mongodb+srv://noob:K3a4ofLngiMG8Hl9@tele.fjm9acq.mongodb.net/?retryWrites=true&w=majority" \
    --env REQUESTED_CHANNEL=@TGVIPR \
    --env WITHDRAWAL_LOG_CHAT_ID=-1002626888395 \
    --env ADMIN_IDS=1211362365 \
    --env SESSIONS_DIR=sessions \
    --env VERIFIED_DIR=verified

echo "✅ Deployment completed!"
echo "🌐 Your bot should be running on Koyeb now"
echo "📊 Check the Koyeb dashboard for logs and status"