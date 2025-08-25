"""
Daily quests handler for Telegram RPG Bot
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from datetime import datetime

from database.db_manager import DatabaseManager
from game_logic.daily_quests import DailyQuestManager, QuestStatus
import config

logger = logging.getLogger(__name__)
db = DatabaseManager(config.DATABASE_URL)
quest_manager = DailyQuestManager(db)


async def show_daily_quests(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show daily quests menu"""
    
    # Get user ID
    if hasattr(character, 'user_id'):
        user_id = character.user_id
    else:
        user_id = character['user_id']
    
    # Get character name
    if hasattr(character, 'name'):
        char_name = character.name
    else:
        char_name = character['name']
    
    # Get daily quests
    quests = await quest_manager.get_daily_quests(user_id)
    
    # Get quest summary
    summary = await quest_manager.get_quest_summary(user_id)
    
    quests_text = f"""
📋 **Щоденні завдання {char_name}**
━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Прогрес дня:** {summary['progress']} ({summary['completion_rate']}%)
🏆 **Отримано нагород:** {summary['claimed']}/{summary['total']}

🕐 **Завдання оновляються о 00:00 (Київ)**

"""
    
    if not quests:
        quests_text += """
❌ **Завдання не знайдені**

Спробуйте оновити або зверніться до адміністратора.
"""
    else:
        for i, quest in enumerate(quests, 1):
            # Status icon
            if quest.status == QuestStatus.CLAIMED:
                status_icon = "✅"
                status_text = "Отримано"
            elif quest.status == QuestStatus.COMPLETED:
                status_icon = "🎁"
                status_text = "Готово!"
            else:
                status_icon = "⏳"
                status_text = f"{quest.current_progress}/{quest.requirement}"
            
            # Progress bar
            progress_bar = quest.get_progress_bar()
            
            quests_text += f"""
{status_icon} **{quest.icon} {quest.name}**
📝 {quest.description}
📊 {progress_bar} {quest.progress_percentage}%
📈 Прогрес: {status_text}

🎁 **Нагороди:**
"""
            
            # Show rewards
            if quest.reward.experience > 0:
                quests_text += f"⚡ {quest.reward.experience} досвіду  "
            if quest.reward.gold > 0:
                quests_text += f"💰 {quest.reward.gold} золота  "
            if quest.reward.item_name:
                quests_text += f"🎁 {quest.reward.item_name}"
            
            quests_text += "\n\n"
    
    # Add refresh timestamp to make message unique
    refresh_time = context.user_data.get('quests_refresh_time', '')
    if refresh_time:
        quests_text += f"🔄 **Оновлено:** {refresh_time}\n"
        context.user_data.pop('quests_refresh_time', None)
    
    # Create keyboard
    keyboard = []
    
    # Add claim buttons for completed quests
    for quest in quests:
        if quest.status == QuestStatus.COMPLETED:
            keyboard.append([InlineKeyboardButton(
                f"🎁 Отримати нагороду - {quest.name}",
                callback_data=f"quest_claim_{quest.id}"
            )])
    
    # Navigation buttons
    if len(keyboard) == 0:
        keyboard.append([InlineKeyboardButton("📋 Оновити завдання", callback_data="quests_refresh")])
    else:
        keyboard.append([InlineKeyboardButton("📋 Оновити", callback_data="quests_refresh")])
    
    keyboard.append([InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        quests_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_quest_tips(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show quest tips and help"""
    
    tips_text = """
💡 **Поради щодо щоденних завдань**
━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **Типи завдань:**

🌲 **Очищення лісу** - Полюйте в Темному лісі
🏰 **Дослідник підземель** - Проходьте підземелля
⚔️ **Чемпіон арени** - Змагайтеся на арені
💰 **Збирач скарбів** - Заробляйте золото
💥 **Майстер бою** - Завдавайте урон ворогам
🛡 **Виживший** - Уникайте отримання урону
🛒 **Торговець** - Купуйте у магазині

⏰ **Система оновлення:**
- Завдання оновляються щодня о 00:00 за Київським часом
- У вас є 24 години на виконання завдань
- Невиконані завдання зникають при оновленні

🎁 **Нагороди:**
- Досвід для швидкого розвитку
- Золото для покупок
- Корисні зілля та предмети

💡 **Поради:**
- Виконуйте завдання протягом дня
- Не забувайте забирати нагороди
- Плануйте дії під завдання
"""
    
    keyboard = [
        [InlineKeyboardButton("📋 Повернутися до завдань", callback_data="tavern_quests")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        tips_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def daily_quests_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle daily quests callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Get character
    character = await db.get_character(user_id)
    if not character:
        await query.edit_message_text("❌ Персонаж не знайдений!")
        return
    
    if data == "quests_refresh":
        # Add refresh timestamp to make message unique
        from datetime import datetime
        context.user_data['quests_refresh_time'] = datetime.now().strftime("%H:%M:%S")
        await show_daily_quests(update, context, character)
    
    elif data == "quests_tips":
        await show_quest_tips(update, context)
    
    elif data.startswith("quest_claim_"):
        quest_id = data.replace("quest_claim_", "")
        await claim_quest_reward(update, context, character, quest_id)


async def claim_quest_reward(update: Update, context: ContextTypes.DEFAULT_TYPE, character, quest_id: str) -> None:
    """Claim reward for completed quest"""
    
    if hasattr(character, 'user_id'):
        user_id = character.user_id
    else:
        user_id = character['user_id']
    
    # Give reward
    reward_text = await quest_manager.give_quest_reward(user_id, quest_id)
    
    # Get quest name for display
    quest_data = await db.get_daily_quest(user_id, quest_id)
    quest_name = quest_data.get('name', 'Завдання') if quest_data else 'Завдання'
    
    # Show reward message
    reward_message = f"""
🎉 **НАГОРОДА ОТРИМАНА!**
━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **Завдання:** {quest_name}

🎁 **Отримано:**
{reward_text}

Вітаємо з виконанням щоденного завдання!
"""
    
    keyboard = [
        [InlineKeyboardButton("📋 Повернутися до завдань", callback_data="tavern_quests")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        reward_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# Helper function to update quest progress from other handlers
async def update_quest_progress(user_id: int, quest_type_str: str, amount: int = 1) -> list:
    """Helper function to update quest progress from other handlers"""
    try:
        from game_logic.daily_quests import QuestType
        
        # Map string to QuestType enum
        quest_type_map = {
            'forest': QuestType.FOREST_CLEARING,
            'dungeon': QuestType.DUNGEON_EXPLORER, 
            'arena': QuestType.ARENA_CHAMPION,
            'gold': QuestType.TREASURE_COLLECTOR,
            'damage': QuestType.BATTLE_MASTER,
            'survive': QuestType.SURVIVOR,
            'trade': QuestType.TRADER
        }
        
        quest_type = quest_type_map.get(quest_type_str)
        if quest_type:
            return await quest_manager.update_quest_progress(user_id, quest_type, amount)
        
        return []
        
    except Exception as e:
        logger.error(f"Error updating quest progress: {e}")
        return []


async def notify_quest_completion(update: Update, context: ContextTypes.DEFAULT_TYPE, completed_quests: list) -> str:
    """Create notification text for completed quests"""
    if not completed_quests:
        return ""
    
    notification = "\n🎉 **ЗАВДАННЯ ВИКОНАНО!**\n"
    for quest in completed_quests:
        notification += f"📋 {quest.icon} {quest.name}\n"
        notification += "🎁 Нагорода готова до отримання!\n"
    
    return notification
