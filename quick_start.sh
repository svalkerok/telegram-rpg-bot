#!/bin/bash
# 🚀 Швидкий запуск Telegram RPG Bot "Легенди Валгаллії"
# Quick launch script

echo "🎮 Запуск Telegram RPG Bot 'Легенди Валгаллії'"
echo "=" * 50

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Створення віртуального середовища..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Активація віртуального середовища..."
source venv/bin/activate

# Install/upgrade requirements
echo "📋 Встановлення залежностей..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не знайдено!"
    echo "📝 Створюю шаблон .env файлу..."
    cp .env.example .env
    echo ""
    echo "🔧 УВАГА: Налаштуйте .env файл перед запуском:"
    echo "   - BOT_TOKEN=your_telegram_bot_token"
    echo "   - ADMIN_USER_ID=your_telegram_user_id"
    echo ""
    echo "ℹ️  Отримати токен бота: https://t.me/BotFather"
    echo "ℹ️  Дізнатись свій ID: https://t.me/userinfobot"
    echo ""
    exit 1
fi

# Run tests
echo "🧪 Запуск тестів..."
python test_character_object_fixes.py

if [ $? -eq 0 ]; then
    echo "✅ Всі тести пройшли успішно!"
    echo ""
    echo "🚀 Запуск бота..."
    python main.py
else
    echo "❌ Тести не пройшли! Перевірте конфігурацію."
    exit 1
fi
