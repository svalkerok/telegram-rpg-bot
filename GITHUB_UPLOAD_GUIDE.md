# 🚀 Гід по завантаженню RPG Bot на GitHub

## 📋 Перед початком

### Вимоги:
- GitHub аккаунт
- Git встановлений на комп'ютері
- Токен доступу GitHub (Personal Access Token)

### Перевірка готовності:
- ✅ Git репозиторій ініціалізовано
- ✅ Перший коміт створено
- ✅ Всі файли додані до репозиторію

## 🎯 Покрокова інструкція

### Крок 1: Створення репозиторію на GitHub

1. **Увійдіть в GitHub**
2. **Натисніть кнопку "+" в правому верхньому куті**
3. **Виберіть "New repository"**
4. **Заповніть форму:**
   - **Repository name:** `telegram-rpg-bot` або `rpg-bot`
   - **Description:** `Повнофункціональний RPG бот для Telegram з системою персонажів, бою, підземеллями та економікою`
   - **Visibility:** Public (рекомендовано) або Private
   - **НЕ ставлять галочки:**
     - ❌ Add a README file
     - ❌ Add .gitignore
     - ❌ Choose a license
5. **Натисніть "Create repository"**

### Крок 2: Налаштування віддаленого репозиторію

1. **Скопіюйте URL репозиторію** (буде показано після створення)
2. **В терміналі виконайте:**
```bash
# Додайте віддалений репозиторій
git remote add origin https://github.com/YOUR_USERNAME/telegram-rpg-bot.git

# Перевірте, що репозиторій додано
git remote -v
```

### Крок 3: Налаштування токену доступу

1. **Створіть Personal Access Token:**
   - Перейдіть в Settings → Developer settings → Personal access tokens
   - Натисніть "Generate new token (classic)"
   - Виберіть "repo" права
   - Скопіюйте токен

2. **Налаштуйте Git для використання токену:**
```bash
# Збережіть токен (замініть YOUR_TOKEN на ваш токен)
git config --global credential.helper store
```

### Крок 4: Завантаження коду

1. **Відправте код на GitHub:**
```bash
# Відправте основну гілку
git push -u origin main
```

2. **При запиті введіть:**
   - **Username:** ваш GitHub username
   - **Password:** ваш Personal Access Token (НЕ пароль від GitHub)

### Крок 5: Перевірка завантаження

1. **Перейдіть на сторінку вашого репозиторію**
2. **Перевірте, що всі файли завантажені:**
   - `main.py`
   - `config.py`
   - `requirements.txt`
   - `README.md`
   - `LICENSE`
   - `CHANGELOG.md`
   - Папки: `handlers/`, `game_logic/`, `database/`, `utils/`

## 🔧 Альтернативні способи

### Спосіб 1: Через GitHub CLI

```bash
# Встановіть GitHub CLI
sudo apt install gh

# Авторизуйтесь
gh auth login

# Створіть репозиторій
gh repo create telegram-rpg-bot --public --description "Telegram RPG Bot"

# Відправте код
git push -u origin main
```

### Спосіб 2: Через веб-інтерфейс GitHub

1. **Створіть репозиторій з README**
2. **Клонуйте його локально:**
```bash
git clone https://github.com/YOUR_USERNAME/telegram-rpg-bot.git
cd telegram-rpg-bot
```

3. **Скопіюйте файли проекту:**
```bash
# Скопіюйте всі файли з вашого проекту
cp -r /path/to/your/project/* .
```

4. **Додайте та відправте:**
```bash
git add .
git commit -m "Add RPG Bot files"
git push
```

## 📊 Налаштування репозиторію

### Крок 6: Налаштування сторінки репозиторію

1. **Перейдіть в Settings → Pages**
2. **Виберіть Source: "Deploy from a branch"**
3. **Виберіть Branch: "main"**
4. **Натисніть "Save"**

### Крок 7: Додавання тегів (опціонально)

```bash
# Створіть тег для версії
git tag -a v1.0.0 -m "Version 1.0.0 - Initial release"

# Відправте теги
git push origin --tags
```

### Крок 8: Налаштування Issues та Projects

1. **Перейдіть в Issues**
2. **Створіть шаблони для:**
   - Bug reports
   - Feature requests
   - Questions

## 🔍 Перевірка репозиторію

### Структура файлів:
```
telegram-rpg-bot/
├── main.py                 # ✅ Головний файл
├── config.py              # ✅ Конфігурація
├── requirements.txt       # ✅ Залежності
├── README.md             # ✅ Документація
├── LICENSE               # ✅ Ліцензія
├── CHANGELOG.md          # ✅ Історія змін
├── .gitignore           # ✅ Ігноровані файли
├── config.py.example    # ✅ Приклад конфігурації
├── handlers/            # ✅ Обробники
├── game_logic/          # ✅ Ігрова логіка
├── database/            # ✅ База даних
├── utils/               # ✅ Утиліти
├── run.sh              # ✅ Скрипт запуску
└── quick_start.sh      # ✅ Швидкий старт
```

### Перевірка README:
- ✅ Опис проекту
- ✅ Особливості
- ✅ Встановлення
- ✅ Використання
- ✅ Структура проекту
- ✅ Ліцензія

## 🚀 Публікація

### Крок 9: Розповсюдження

1. **Поділіться посиланням:**
   ```
   https://github.com/YOUR_USERNAME/telegram-rpg-bot
   ```

2. **Додайте в опис:**
   - Зірки ⭐
   - Форки 🔄
   - Issues 🐛
   - Pull Requests 🔄

3. **Створіть Release:**
   - Перейдіть в Releases
   - Натисніть "Create a new release"
   - Заповніть інформацію про версію

## 🔄 Оновлення коду

### Для подальших оновлень:

```bash
# Внесіть зміни в код
# Додайте зміни
git add .

# Створіть коміт
git commit -m "Description of changes"

# Відправте на GitHub
git push origin main
```

### Створення нових версій:

```bash
# Створіть новий тег
git tag -a v1.1.0 -m "Version 1.1.0 - New features"

# Відправте тег
git push origin --tags
```

## 📈 Моніторинг

### GitHub Insights:
- **Traffic** - перегляди та клонування
- **Contributors** - учасники проекту
- **Commits** - активність розробки
- **Issues** - проблеми та запити

### Налаштування сповіщень:
1. **Перейдіть в Settings → Notifications**
2. **Налаштуйте сповіщення для:**
   - Issues
   - Pull requests
   - Releases

## 🆘 Вирішення проблем

### Проблема: "Authentication failed"
**Рішення:** Перевірте Personal Access Token

### Проблема: "Repository not found"
**Рішення:** Перевірте URL репозиторію та права доступу

### Проблема: "Permission denied"
**Рішення:** Перевірте права доступу до репозиторію

### Проблема: "Large file detected"
**Рішення:** Видаліть великі файли з .gitignore

## 📞 Підтримка

### Корисні команди:
```bash
# Перевірка статусу
git status

# Перегляд історії
git log --oneline

# Перегляд віддалених репозиторіїв
git remote -v

# Очищення кешу
git gc
```

### Посилання:
- [GitHub Help](https://help.github.com/)
- [Git Documentation](https://git-scm.com/doc)
- [GitHub CLI](https://cli.github.com/)

---

**🚀 Успішного завантаження на GitHub!** 🎮
