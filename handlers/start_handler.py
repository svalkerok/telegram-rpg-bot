"""
Start command handler and character creation for Telegram RPG Bot "Легенди Валгаллії"
Система реєстрації та створення персонажа
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import re

from database.db_manager import DatabaseManager
import config

logger = logging.getLogger(__name__)
db = DatabaseManager(config.DATABASE_URL)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Основний обробник команди /start
    Привітання та перевірка реєстрації
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    try:
        # Перевіряємо, чи користувач вже має персонажа
        character = await db.get_character(user_id)
        
        if character:
            # Користувач вже має персонажа - показуємо таверну
            logger.info(f"Existing user {user_id} ({username}) returned to game")
            await show_tavern_menu(update, context, character)
        else:
            # Новий користувач - показуємо привітання та створення персонажа
            logger.info(f"New user started bot: {user_id} ({username})")
            await show_welcome_message(update, context)
            
    except Exception as e:
        logger.error(f"Error in start_handler: {e}")
        await update.message.reply_text(
            "❌ Виникла помилка при запуску. Спробуйте ще раз або зверніться до адміністратора.",
            parse_mode='Markdown'
        )


async def show_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показати привітальне повідомлення для нових користувачів"""
    welcome_text = """
🎮 **Ласкаво просимо до "Легенди Валгаллії"!**

🏰 Ви прибули до містечка Камінний Притулок після довгої подорожі.
Попереду вас чекають безліч пригод, багатства та слава!

⚔️ У цьому світі ви зможете:
• Створити унікального героя з одного з трьох класів
• Досліджувати небезпечні підземелля з босами
• Битися на арені з іншими авантюристами
• Полювати на монстрів у Темному лісі
• Торгувати з місцевими торговцями
• Виконувати щоденні завдання та отримувати нагороди

📜 Щоб почати свою пригоду, створіть свого персонажа!
"""
    
    keyboard = [[InlineKeyboardButton("⚔️ Створити персонажа", callback_data="create_start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def character_creation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обробник процесу створення персонажа
    Керує усім процесом від вибору класу до завершення
    """
    query = update.callback_query
    if query:
        await query.answer()
        
        data = query.data
        
        if data == "create_start":
            # Почати створення персонажа - показати вибір класу
            await show_class_selection(update, context)
            
        elif data.startswith("create_class_"):
            # Зберегти вибраний клас та запитати ім'я
            char_class = data.replace("create_class_", "")
            context.user_data['selected_class'] = char_class
            logger.info(f"User {update.effective_user.id} selected class: {char_class}")
            await ask_character_name(update, context)


async def show_class_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показати вибір класу персонажа з inline кнопками
    Детальні описи кожного класу
    """
    
    # Отримуємо конфігурацію класів
    warrior_config = config.CHARACTER_CLASSES['warrior']
    mage_config = config.CHARACTER_CLASSES['mage']
    ranger_config = config.CHARACTER_CLASSES['ranger']
    
    class_text = f"""
👤 **Оберіть клас вашого героя:**

{warrior_config['emoji']} **{warrior_config['name']}** - Майстер ближнього бою
━━━━━━━━━━━━━━━━━━━━━━━━━
💚 Здоров'я: {warrior_config['base_stats']['max_health']}
⚔️ Атака: {warrior_config['base_stats']['attack']}
🛡 Захист: {warrior_config['base_stats']['defense']}
⚡ Швидкість: {warrior_config['base_stats']['speed']}
🛡 Блокування: {warrior_config['base_stats']['block_chance']}%
**Особливості:** Високе здоров'я та захист, сильні фізичні атаки

{mage_config['emoji']} **{mage_config['name']}** - Володар магічних сил
━━━━━━━━━━━━━━━━━━━━━━━━━
💚 Здоров'я: {mage_config['base_stats']['max_health']}
💙 Мана: {mage_config['base_stats']['max_mana']}
🔮 Магічна сила: {mage_config['base_stats']['magic_power']}
⚡ Швидкість: {mage_config['base_stats']['speed']}
**Особливості:** Потужна магія та лікування, високе розуміння магії

{ranger_config['emoji']} **{ranger_config['name']}** - Швидкий та спритний
━━━━━━━━━━━━━━━━━━━━━━━━━
💚 Здоров'я: {ranger_config['base_stats']['max_health']}
⚔️ Атака: {ranger_config['base_stats']['attack']}
⚡ Швидкість: {ranger_config['base_stats']['speed']}
💥 Критичний удар: {ranger_config['base_stats']['critical_chance']}%
**Особливості:** Висока швидкість та шанс критичного удару

Оберіть клас, який найкраще відповідає вашому стилю гри:
"""
    
    keyboard = [
        [InlineKeyboardButton(f"{warrior_config['emoji']} {warrior_config['name']}", callback_data="create_class_warrior")],
        [InlineKeyboardButton(f"{mage_config['emoji']} {mage_config['name']}", callback_data="create_class_mage")],
        [InlineKeyboardButton(f"{ranger_config['emoji']} {ranger_config['name']}", callback_data="create_class_ranger")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            class_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            class_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def ask_character_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Запит імені персонажа з валідацією
    Показує вимоги до імені та обраний клас
    """
    char_class = context.user_data.get('selected_class', 'warrior')
    class_config = config.CHARACTER_CLASSES.get(char_class, config.CHARACTER_CLASSES['warrior'])
    
    name_request_text = f"""
✅ **Клас обрано:** {class_config['emoji']} {class_config['name']}

📝 **Тепер введіть ім'я вашого героя:**

**Вимоги до імені:**
• Від {config.MIN_CHARACTER_NAME_LENGTH} до {config.MAX_CHARACTER_NAME_LENGTH} символів
• Українські та англійські літери
• Цифри та пробіли дозволені
• Без спеціальних символів

**Приклади гарних імен:**
• Тарас Шевченко
• Артур Король  
• Мерлін Чарівник
• Ельфійка Аріель

💬 Напишіть ім'я у наступному повідомленні:
"""
    
    # Встановлюємо флаг очікування імені
    context.user_data['waiting_for_name'] = True
    
    # Зберігаємо стан в БД як backup (на випадок проблем з persistence)
    try:
        import json
        user_id = update.effective_user.id
        state_data = json.dumps({
            'waiting_for_name': True,
            'selected_class': char_class
        })
        await db.set_user_data(user_id, 'character_creation_state', state_data)
        logger.info(f"Saved character creation state to DB for user {user_id}")
    except Exception as e:
        logger.warning(f"Could not save creation state to DB: {e}")
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            name_request_text, 
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            name_request_text, 
            parse_mode='Markdown'
        )


async def text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обробник введення імені персонажа та інших текстових даних
    Валідація, перевірка та створення персонажа
    """
    
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    logger.info(f"Text input from user {user_id}: '{message_text}'")
    logger.info(f"User data: {context.user_data}")
    
    # Skip admin users ONLY if they're not creating a character
    if user_id == config.ADMIN_USER_ID:
        # Check if admin is in character creation process
        waiting_for_name = context.user_data.get('waiting_for_name', False)
        
        # Also check DB backup state
        if not waiting_for_name:
            try:
                import json
                db_state_raw = await db.get_user_data(user_id, 'character_creation_state')
                if db_state_raw:
                    db_state = json.loads(db_state_raw)
                    waiting_for_name = db_state and db_state.get('waiting_for_name', False)
            except Exception as e:
                logger.warning(f"Could not check admin creation state: {e}")
        
        # If admin is not creating character, skip to admin handler
        if not waiting_for_name:
            logger.info(f"Skipping admin user {user_id} (not creating character)")
            return
        else:
            logger.info(f"Admin user {user_id} is creating character, processing...")
    
    # Перевіряємо стан створення персонажа (в context.user_data або в БД)
    waiting_for_name = context.user_data.get('waiting_for_name', False)
    selected_class = context.user_data.get('selected_class')
    
    # Якщо немає в context.user_data, перевіряємо БД
    if not waiting_for_name:
        try:
            import json
            db_state_raw = await db.get_user_data(user_id, 'character_creation_state')
            if db_state_raw:
                db_state = json.loads(db_state_raw)
                if db_state and db_state.get('waiting_for_name'):
                    waiting_for_name = True
                    selected_class = db_state.get('selected_class', 'warrior')
                    logger.info(f"Restored creation state from DB for user {user_id}: {db_state}")
                    
                    # Відновлюємо стан в context.user_data
                    context.user_data['waiting_for_name'] = True
                    context.user_data['selected_class'] = selected_class
        except Exception as e:
            logger.warning(f"Could not check DB state: {e}")
    
    # Перевіряємо, чи очікуємо ім'я персонажа
    if waiting_for_name:
        logger.info(f"Processing character name: '{message_text}' for user {user_id}")
        
        # Валідація імені
        validation_result = await validate_character_name(message_text)
        
        if validation_result['valid']:
            # Ім'я валідне - створюємо персонажа
            logger.info(f"Valid name, creating character for user {user_id}")
            
            # Очищаємо стан створення
            context.user_data['waiting_for_name'] = False
            
            # Очищаємо стан в БД
            try:
                await db.set_user_data(user_id, 'character_creation_state', None)
                logger.info(f"Cleared creation state from DB for user {user_id}")
            except Exception as e:
                logger.warning(f"Could not clear creation state: {e}")
            
            await create_character_with_name(update, context, message_text)
        else:
            # Ім'я невалідне - показуємо помилку
            logger.warning(f"Invalid name '{message_text}' for user {user_id}: {validation_result['error']}")
            await update.message.reply_text(
                f"❌ {validation_result['error']}\n\n💡 Спробуйте ще раз:",
                parse_mode='Markdown'
            )
            return
    
    # Перевіряємо інші типи текстового вводу (наприклад, для адміна)
    elif context.user_data.get('waiting_for_broadcast'):
        # Обробляємо повідомлення для розсилки (адмін функція)
        from handlers.admin_handler import process_broadcast
        await process_broadcast(update, context)
    
    else:
        # Невідомий текстовий ввід або користувач не в процесі створення персонажа
        logger.info(f"Unexpected text input from user {user_id}, showing help")
        
        # Спочатку перевіряємо, чи вже є персонаж
        character = await db.get_character(user_id)
        if character:
            # Є персонаж - пропонуємо меню таверни
            await update.message.reply_text(
                "🏛 Використайте /start щоб потрапити до таверни або /help для довідки.",
                parse_mode='Markdown'
            )
        else:
            # Немає персонажа - пропонуємо створити
            await update.message.reply_text(
                "👤 Схоже, у вас ще немає персонажа! Використайте /start щоб створити героя.",
                parse_mode='Markdown'
            )


async def validate_character_name(name: str) -> dict:
    """
    Валідація імені персонажа
    Повертає словник з результатом валідації
    """
    
    # Перевірка довжини
    if len(name) < config.MIN_CHARACTER_NAME_LENGTH:
        return {
            'valid': False,
            'error': f"Ім'я занадто коротке! Мінімум {config.MIN_CHARACTER_NAME_LENGTH} символи."
        }
    
    if len(name) > config.MAX_CHARACTER_NAME_LENGTH:
        return {
            'valid': False,
            'error': f"Ім'я занадто довге! Максимум {config.MAX_CHARACTER_NAME_LENGTH} символів."
        }
    
    # Перевірка на пустоту після обрізання пробілів
    if not name.strip():
        return {
            'valid': False,
            'error': "Ім'я не може бути порожнім!"
        }
    
    # Перевірка дозволених символів (українські, англійські літери, цифри, пробіли)
    allowed_pattern = re.compile(r'^[a-zA-Zа-яА-ЯіІїЇєЄґҐ0-9\s]+$')
    if not allowed_pattern.match(name):
        return {
            'valid': False,
            'error': "Ім'я може містити тільки українські та англійські літери, цифри та пробіли!"
        }
    
    # Перевірка на надмірну кількість пробілів підряд
    if '  ' in name:
        return {
            'valid': False,
            'error': "В імені не може бути кілька пробілів підряд!"
        }
    
    # Перевірка, щоб ім'я не починалось або не закінчувалось пробілом
    if name != name.strip():
        return {
            'valid': False,
            'error': "Ім'я не може починатись або закінчуватись пробілом!"
        }
    
    # Перевірка на цифри на початку імені
    if name[0].isdigit():
        return {
            'valid': False,
            'error': "Ім'я не може починатись з цифри!"
        }
    
    return {'valid': True, 'error': None}


async def create_character_with_name(update: Update, context: ContextTypes.DEFAULT_TYPE, name: str) -> None:
    """
    Створення персонажа з заданим ім'ям
    Автоматичне переходження до таверни після успішного створення
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    char_class = context.user_data.get('selected_class', 'warrior')
    
    try:
        # Перевіряємо, чи користувач вже не має персонажа (додаткова перевірка)
        existing_character = await db.get_character(user_id)
        if existing_character:
            await update.message.reply_text(
                "⚠️ У вас вже є персонаж! Використайте /start щоб потрапити до таверни.",
                parse_mode='Markdown'
            )
            context.user_data.clear()
            return
        
        # Отримуємо конфігурацію класу
        class_config = config.CHARACTER_CLASSES.get(char_class, config.CHARACTER_CLASSES['warrior'])
        
        # Підготовляємо дані персонажа
        character_data = {
            'user_id': user_id,
            'username': username,
            'name': name,
            'class': char_class,
            **class_config['base_stats'],
            'weapon': class_config['start_equipment']['weapon'],
            'armor': class_config['start_equipment']['armor']
        }
        
        # Створюємо персонажа в базі даних
        success = await db.create_character(character_data)
        
        if success:
            # Успішно створено - показуємо повідомлення та переходимо до таверни
            success_text = f"""
✅ **Персонажа успішно створено!**

🎭 **{name}** - {class_config['emoji']} {class_config['name']}
━━━━━━━━━━━━━━━━━━━━━━━━━

**Початкові характеристики:**
💚 Здоров'я: {character_data['health']}/{character_data['max_health']}
💰 Золото: {character_data.get('gold', 50)}
⚔️ Атака: {character_data['attack']}
🛡 Захист: {character_data['defense']}
⚡ Швидкість: {character_data['speed']}
"""
            
            if character_data.get('mana', 0) > 0:
                success_text += f"💙 Мана: {character_data['mana']}/{character_data['max_mana']}\n"
                success_text += f"🔮 Магічна сила: {character_data['magic_power']}\n"
            
            success_text += f"""
💥 Шанс криту: {character_data['critical_chance']}%
🛡 Шанс блоку: {character_data['block_chance']}%

**Початкове спорядження:**
⚔️ Зброя: {character_data['weapon']}
🛡 Броня: {character_data['armor']}

🏛 Ласкаво просимо до таверни "Камінний Притулок"!
Ваша пригода розпочинається зараз!
"""
            
            await update.message.reply_text(success_text, parse_mode='Markdown')
            
            # Очищаємо тимчасові дані
            context.user_data.clear()
            
            # Показуємо головне меню таверни
            character = await db.get_character(user_id)
            if character:
                await show_tavern_menu_from_message(update, context, character)
            
            logger.info(f"Character created successfully: {name} ({char_class}) for user {user_id}")
            
        else:
            # Помилка при створенні
            await update.message.reply_text(
                "❌ Помилка при створенні персонажа. Можливо, така проблема з базою даних.\n\nСпробуйте ще раз або зверніться до адміністратора.",
                parse_mode='Markdown'
            )
            logger.error(f"Failed to create character for user {user_id}")
            
    except Exception as e:
        logger.error(f"Error creating character: {e}")
        await update.message.reply_text(
            "❌ Сталася несподівана помилка при створенні персонажа.\n\nСпробуйте ще раз пізніше або зверніться до адміністратора.",
            parse_mode='Markdown'
        )


async def show_tavern_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """
    Показати головне меню таверни для існуючого персонажа
    """
    from handlers.tavern_handler import show_tavern_menu as tavern_menu
    await tavern_menu(update, context, character)


async def show_tavern_menu_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """
    Показати меню таверни з повідомлення (не callback)
    """
    from handlers.tavern_handler import show_tavern_menu_from_message as tavern_menu_from_msg
    await tavern_menu_from_msg(update, context, character)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /help - допомога по грі"""
    
    help_text = """
📖 **Довідка по грі "Легенди Валгаллії"**

**🎮 Основні команди:**
/start - Почати гру або повернутись до таверни
/help - Ця довідка
/stats - Статистика вашого персонажа
/inventory - Перегляд інвентаря
/quests - Щоденні завдання

**⚔️ Класи персонажів:**

🗡 **Воїн** - Майстер ближнього бою
• Високе здоров'я та захист
• Сильні фізичні атаки
• Здатність блокувати атаки ворогів

🧙‍♂️ **Маг** - Володар магічних сил
• Потужні магічні атаки
• Здатність до лікування
• Використовує ману для заклять

🏹 **Розвідник** - Швидкий та спритний
• Високий шанс критичного удару
• Велика швидкість та ухиляння
• Балансовані характеристики

**🌍 Локації для пригод:**

🗡 **Підземелля** - Структуровані данжі з босами
• Склеп Новачка (рівень 1+)
• Печера Орків (рівень 3+)  
• Вежа Магів (рівень 6+)
• Лігво Дракона (рівень 9+)

⚔️ **Арена** - PvP битви з іншими гравцями
• Отримуйте золото та досвід за перемоги
• Ризикуйте, але отримуйте великі нагороди

🌲 **Темний ліс** - Вільне полювання на монстрів
• Різні зони залежно від рівня
• Випадкові події та знахідки

🛒 **Торговець** - Купівля та продаж предметів
• Зброя, броня, зілля
• Спеціальні знижки по середах

**💡 Поради для новачків:**
• Завжди стежте за рівнем здоров'я
• Виконуйте щоденні завдання для досвіду
• Покращуйте спорядження для кращих характеристик
• Не йдіть у складні підземелля без підготовки
• Зберігайте золото для важливих покупок

**🏆 Прогресія:**
• Отримуйте досвід за перемоги над ворогами
• Підвищуйте рівень для кращих характеристик
• Розблоковуйте нові локації та можливості
• Збирайте досягнення за особливі вчинки

❓ **Потрібна додаткова допомога?**
Зверніться до адміністратора або використайте /start щоб повернутись до гри!

Удачі у ваших пригодах! ⚔️🛡✨
"""
    
    keyboard = [
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats_character")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# Додаткові допоміжні функції для обробки помилок

async def handle_creation_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error_message: str) -> None:
    """Обробка помилок при створенні персонажа"""
    
    error_text = f"""
❌ **Виникла помилка:** {error_message}

🔄 **Що можна зробити:**
• Спробувати ще раз через кілька хвилин
• Перевірити з'єднання з інтернетом
• Звернутися до адміністратора якщо проблема повторюється

Використайте /start щоб спробувати ще раз.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Спробувати ще раз", callback_data="create_start")],
        [InlineKeyboardButton("📞 Звернутися до адміна", url="tg://user?id=" + str(config.ADMIN_USER_ID))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        error_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def clear_user_creation_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Очищення тимчасових даних створення персонажа"""
    keys_to_remove = ['selected_class', 'waiting_for_name', 'creation_step']
    
    for key in keys_to_remove:
        context.user_data.pop(key, None)


async def start_new_character_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle start new character callback after character deletion"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    try:
        # Clear any existing user creation data
        await clear_user_creation_data(context)
        
        # Check if user already has a character (shouldn't happen after deletion)
        character = await db.get_character(user_id)
        
        if character:
            # User already has a character - show tavern
            logger.info(f"User {user_id} ({username}) already has character, showing tavern")
            from handlers.tavern_handler import show_tavern_menu
            await show_tavern_menu(update, context, character)
        else:
            # New character creation - show welcome message
            logger.info(f"Starting character creation for user: {user_id} ({username})")
            
            welcome_text = f"""
🏰 **Ласкаво просимо до світу Валгаллії!**
━━━━━━━━━━━━━━━━━━━━━━━━━

👋 Привіт, {update.effective_user.first_name}!

Ви потрапили в епічний світ RPG пригод, де вас чекають:

⚔️ **Бої з монстрами** в темних підземеллях
🌲 **Полювання** в таємничих лісах  
🏟 **PvP битви** на арені
🛒 **Торгівля** з магічними предметами
🏆 **Досягнення** та щоденні квести

Готові розпочати свою легенду?
"""
            
            keyboard = [
                [InlineKeyboardButton("🆕 Створити персонажа", callback_data="create_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                welcome_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in start_new_character_callback: {e}")
        await update.callback_query.answer("❌ Помилка при створенні персонажа")
