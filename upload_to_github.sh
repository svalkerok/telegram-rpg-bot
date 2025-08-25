#!/bin/bash

# 🚀 Скрипт для завантаження RPG Bot на GitHub
# Використання: ./upload_to_github.sh YOUR_USERNAME REPO_NAME

set -e  # Зупинка при помилці

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функція для виводу повідомлень
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Перевірка аргументів
if [ $# -lt 2 ]; then
    print_error "Використання: $0 <github_username> <repository_name>"
    print_error "Приклад: $0 john_doe telegram-rpg-bot"
    exit 1
fi

GITHUB_USERNAME=$1
REPO_NAME=$2
REPO_URL="https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"

print_message "🚀 Початок завантаження RPG Bot на GitHub"
print_message "Користувач: $GITHUB_USERNAME"
print_message "Репозиторій: $REPO_NAME"

# Перевірка Git
print_step "Перевірка Git..."
if ! command -v git &> /dev/null; then
    print_error "Git не встановлено. Встановіть Git спочатку."
    exit 1
fi

# Перевірка статусу репозиторію
print_step "Перевірка статусу Git репозиторію..."
if [ ! -d ".git" ]; then
    print_error "Поточна директорія не є Git репозиторієм"
    exit 1
fi

# Перевірка чи є коміти
if ! git log --oneline -1 &> /dev/null; then
    print_error "Немає комітів в репозиторії. Створіть коміт спочатку."
    exit 1
fi

print_message "✅ Git репозиторій готовий"

# Перевірка віддаленого репозиторію
print_step "Перевірка віддаленого репозиторію..."
if git remote get-url origin &> /dev/null; then
    CURRENT_REMOTE=$(git remote get-url origin)
    print_warning "Віддалений репозиторій вже налаштований: $CURRENT_REMOTE"
    read -p "Хочете замінити його на $REPO_URL? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote remove origin
        git remote add origin "$REPO_URL"
        print_message "✅ Віддалений репозиторій оновлено"
    else
        print_message "Використовуємо існуючий віддалений репозиторій"
    fi
else
    git remote add origin "$REPO_URL"
    print_message "✅ Віддалений репозиторій додано"
fi

# Перевірка підключення
print_step "Перевірка підключення до GitHub..."
if ! git ls-remote origin &> /dev/null; then
    print_error "Не вдається підключитися до GitHub"
    print_error "Перевірте:"
    print_error "1. Правильність URL репозиторію"
    print_error "2. Наявність Personal Access Token"
    print_error "3. Права доступу до репозиторію"
    exit 1
fi

print_message "✅ Підключення до GitHub успішне"

# Створення тегу
print_step "Створення тегу версії..."
VERSION="v1.0.0"
if git tag -l | grep -q "$VERSION"; then
    print_warning "Тег $VERSION вже існує"
    read -p "Хочете видалити старий тег та створити новий? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git tag -d "$VERSION"
        git push origin ":refs/tags/$VERSION" 2>/dev/null || true
    else
        print_message "Пропускаємо створення тегу"
        VERSION=""
    fi
fi

if [ -n "$VERSION" ]; then
    git tag -a "$VERSION" -m "Version $VERSION - Initial release"
    print_message "✅ Тег $VERSION створено"
fi

# Відправка коду
print_step "Відправка коду на GitHub..."
if git push -u origin main; then
    print_message "✅ Код успішно відправлено"
else
    print_error "Помилка при відправці коду"
    print_error "Перевірте права доступу та токен"
    exit 1
fi

# Відправка тегів
if [ -n "$VERSION" ]; then
    print_step "Відправка тегів..."
    if git push origin --tags; then
        print_message "✅ Теги успішно відправлено"
    else
        print_warning "Помилка при відправці тегів"
    fi
fi

# Фінальна перевірка
print_step "Фінальна перевірка..."
if git ls-remote --heads origin main | grep -q "main"; then
    print_message "✅ Гілка main успішно створена на GitHub"
else
    print_error "Гілка main не знайдена на GitHub"
    exit 1
fi

# Виведення результатів
echo
print_message "🎉 Завантаження завершено успішно!"
echo
echo -e "${BLUE}📋 Інформація про репозиторій:${NC}"
echo -e "URL: ${GREEN}https://github.com/$GITHUB_USERNAME/$REPO_NAME${NC}"
echo -e "Клонування: ${GREEN}git clone https://github.com/$GITHUB_USERNAME/$REPO_NAME.git${NC}"
echo
echo -e "${BLUE}📊 Наступні кроки:${NC}"
echo "1. Перейдіть на https://github.com/$GITHUB_USERNAME/$REPO_NAME"
echo "2. Перевірте, що всі файли завантажені"
echo "3. Налаштуйте опис репозиторію"
echo "4. Створіть Release з тегом $VERSION"
echo "5. Поділіться посиланням з іншими"
echo
echo -e "${BLUE}🔄 Для оновлень використовуйте:${NC}"
echo "git add ."
echo "git commit -m 'Description of changes'"
echo "git push origin main"
echo
print_message "🚀 Успішного розгортання!" 
