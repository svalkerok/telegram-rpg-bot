#!/bin/bash

# RPG Bot Launch Script

echo "╔══════════════════════════════════════╗"
echo "║   Telegram RPG Bot - Легенди Валгаллії   ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python version: $PYTHON_VERSION"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Check if requirements are installed
if [ ! -f ".requirements_installed" ]; then
    echo "📥 Installing requirements..."
    pip install --upgrade pip
    pip install -r requirements.txt
    touch .requirements_installed
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "Please edit .env file and add your BOT_TOKEN"
    echo "Get your bot token from @BotFather in Telegram"
    echo ""
    read -p "Press Enter after you've added the token..."
fi

# Check if database exists
if [ ! -f "game.db" ]; then
    echo "🗄️  Initializing database..."
    python database/init_db.py <<< "1"
fi

# Create necessary directories
mkdir -p logs backups data

# Launch the bot
echo ""
echo "🚀 Launching bot..."
echo "Press Ctrl+C to stop"
echo ""

python main.py