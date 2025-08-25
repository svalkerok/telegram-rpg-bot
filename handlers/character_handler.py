"""
Character handler - manages character operations
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from database.db_manager import DatabaseManager
from database.database_models import Character
import config

logger = logging.getLogger(__name__)
db = DatabaseManager(config.DATABASE_URL)


def character_required(func):
    """Декоратор для перевірки наявності персонажа"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        character = await db.get_character(user_id)
        
        if not character:
            if update.callback_query:
                await update.callback_query.answer("❌ У вас немає персонажа! Використайте /start щоб створити.", show_alert=True)
            else:
                await update.message.reply_text("❌ У вас немає персонажа! Використайте /start щоб створити.")
            return
        
        return await func(update, context, character, *args, **kwargs)
    
    return wrapper


# Character creation functions moved to start_handler.py
# This handler now focuses on character management functions


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command"""
    user_id = update.effective_user.id
    
    # Get character data
    character = await db.get_character(user_id)
    
    if not character:
        await update.message.reply_text(
            "❌ У вас немає персонажа! Використайте /start щоб створити."
        )
        return
    
    # Get statistics
    stats = await db.get_statistics(user_id)
    
    # Get character class info
    char_class = character.character_class
    class_info = config.CHARACTER_CLASSES.get(char_class, config.CHARACTER_CLASSES['warrior'])
    
    stats_text = f"""
📊 **Статистика {character.name}**
━━━━━━━━━━━━━━━━━━━━━━━━━
**Основні характеристики:**
👤 Клас: {class_info['name']} {class_info['emoji']}
⭐ Рівень: {character.level}
⚡ Досвід: {character.experience}/{character.experience_needed}
💚 Здоров'я: {character.health}/{character.max_health}
💙 Мана: {character.mana}/{character.max_mana}
💰 Золото: {character.gold}

**Бойові характеристики:**
⚔️ Атака: {character.attack}
🛡 Захист: {character.defense}
🔮 Магічна сила: {character.magic_power}
⚡ Швидкість: {character.speed}
💥 Шанс криту: {character.critical_chance}%
🛡 Шанс блоку: {character.block_chance}%

**Прогрес:**
🏛 Підземель пройдено: {character.dungeon_progress}
"""
    
    if stats:
        stats_text += f"""
**Статистика битв:**
👹 Ворогів вбито: {stats.enemies_killed}
🏆 Перемог на арені: {stats.arena_wins}
💀 Поразок на арені: {stats.arena_losses}
⚔️ Завдано урону: {stats.total_damage_dealt}
🛡 Отримано урону: {stats.total_damage_received}
"""
    
    keyboard = [
        [InlineKeyboardButton("🏆 Досягнення", callback_data="stats_achievements")],
        [InlineKeyboardButton("📋 Щоденні завдання", callback_data="stats_quests")],
        [InlineKeyboardButton("🏛 Таверна", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def inventory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /inventory command"""
    user_id = update.effective_user.id
    
    # Get character data
    character = await db.get_character(user_id)
    
    if not character:
        await update.message.reply_text(
            "❌ У вас немає персонажа! Використайте /start щоб створити."
        )
        return
    
    # Get inventory
    inventory = await db.get_inventory(user_id)
    
    inventory_text = f"""
📦 **Інвентар {character.name}**
━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Золото: {character.gold}

**Споряджено:**
⚔️ Зброя: {character.weapon}
🛡 Броня: {character.armor}

**Предмети в сумці:**
"""
    
    if inventory and inventory.items:
        for item in inventory.items:
            inventory_text += f"\n• {item.name} x{item.quantity}"
    else:
        inventory_text += "\n🔍 Інвентар порожній"
    
    keyboard = [
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop_main")],
        [InlineKeyboardButton("🏛 Таверна", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        inventory_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def quests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /quests command"""
    user_id = update.effective_user.id
    
    # Get character data
    character = await db.get_character(user_id)
    
    if not character:
        await update.message.reply_text(
            "❌ У вас немає персонажа! Використайте /start щоб створити."
        )
        return
    
    # TODO: Implement daily quests system
    quests_text = """
📋 **Щоденні завдання**
━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 Система щоденних завдань буде доступна найближчим часом!

Слідкуйте за оновленнями!
"""
    
    keyboard = [
        [InlineKeyboardButton("🏛 Таверна", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        quests_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )