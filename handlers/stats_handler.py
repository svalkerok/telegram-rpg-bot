"""
Statistics and achievements handler for Telegram RPG Bot
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from datetime import datetime

from database.db_manager import DatabaseManager
from game_logic.achievements import AchievementManager, AchievementType
from game_logic.equipment import EquipmentManager
from game_logic.inventory_manager import InventoryManager
import config

logger = logging.getLogger(__name__)
db = DatabaseManager(config.DATABASE_URL)
achievement_manager = AchievementManager(db)


async def show_character_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show complete character statistics"""
    
    # Convert Character object if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
        user_id = character.user_id
    else:
        char_dict = character
        user_id = character['user_id']
    
    # Get statistics
    stats = await db.get_statistics(user_id)
    
    # Get equipment and bonuses using new system
    inventory_manager = InventoryManager(db)
    equipment_manager = EquipmentManager(db)
    
    # Get character's full stats with equipment bonuses
    character_stats = await inventory_manager.calculate_character_stats(user_id)
    equipment = await inventory_manager.get_character_equipment(user_id)
    
    stats_text = f"""
📊 **Статистика {char_dict['name']}**
━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **Основні характеристики:**
🆔 Рівень: {char_dict['level']}
⚡ Досвід: {char_dict['experience']}/{char_dict['experience_needed']}
💚 Здоров'я: {char_dict['health']}/{char_dict['max_health']}
💙 Мана: {char_dict['mana']}/{char_dict['max_mana']}
💰 Золото: {char_dict['gold']}

⚔️ **Бойові характеристики:**
🗡 Атака: {character_stats.base_attack} → {character_stats.total_attack} (+{character_stats.total_attack - character_stats.base_attack})
🛡 Захист: {character_stats.base_defense} → {character_stats.total_defense} (+{character_stats.total_defense - character_stats.base_defense})
⚡ Швидкість: {character_stats.base_speed} → {character_stats.total_speed} (+{character_stats.total_speed - character_stats.base_speed})
💥 Крит. шанс: {character_stats.total_crit_chance}%
🛡 Шанс блоку: {character_stats.total_block_chance}%
🔮 Магічна сила: {character_stats.base_magic_power} → {character_stats.total_magic_power} (+{character_stats.total_magic_power - character_stats.base_magic_power})

🎒 **Поточне спорядження:**
⚔️ Зброя: {_get_equipment_display_name(equipment_manager, equipment.equipped_weapon, equipment.weapon_upgrade_level)}
🛡 Броня: {_get_equipment_display_name(equipment_manager, equipment.equipped_armor, equipment.armor_upgrade_level)}

📈 **Статистика боїв:**
👹 Ворогів убито: {stats.enemies_killed if stats else 0}
💥 Критичних ударів: {getattr(stats, 'critical_hits', 0) if stats else 0}
🏃 Втеч з боїв: {getattr(stats, 'battles_fled', 0) if stats else 0}

🏰 **Дослідження:**
🗡 Підземель завершено: {stats.dungeons_completed if stats else 0}
🌲 Перемог у лісі: {getattr(stats, 'forest_wins', 0) if stats else 0}
🐉 Драконів убито: {getattr(stats, 'dragon_boss_kills', 0) if stats else 0}

🏟 **Арена:**
🏆 Перемог: {stats.arena_wins if stats else 0}
💀 Поразок: {stats.arena_losses if stats else 0}
🔥 Поточна серія: {getattr(stats, 'arena_win_streak', 0) if stats else 0}

💰 **Економіка:**
💸 Витрачено золота: {stats.gold_spent if stats else 0}
💎 Зароблено золота: {stats.gold_earned if stats else 0}
🧪 Зілля використано: {getattr(stats, 'potions_used', 0) if stats else 0}

🕐 **Час гри:**
📅 Останній вхід: {char_dict['last_played'] or 'Невідомо'}
🎮 Днів гри: {_calculate_days_played(char_dict.get('created_at'))}"""
    
    # Add refresh timestamp if available to make message unique
    refresh_time = context.user_data.get('stats_refresh_time', '')
    if refresh_time:
        stats_text += f"\n🔄 **Оновлено:** {refresh_time}"
        context.user_data.pop('stats_refresh_time', None)  # Remove after use
    
    stats_text += "\n"
    
    keyboard = [
        [InlineKeyboardButton("🏆 Досягнення", callback_data="stats_achievements")],
        [InlineKeyboardButton("📊 Детальна статистика", callback_data="stats_detailed")],
        [InlineKeyboardButton("🔄 Оновити", callback_data="stats_character")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show achievements list"""
    
    if hasattr(character, 'user_id'):
        user_id = character.user_id
    else:
        user_id = character['user_id']
    
    # Get earned achievements
    earned_achievements = await db.get_user_achievements(user_id)
    earned_ids = [ach['achievement_id'] for ach in earned_achievements] if earned_achievements else []
    
    # Check for new achievements
    new_achievements = await achievement_manager.check_achievements(user_id)
    
    achievements_text = """
🏆 **Досягнення**
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    if new_achievements:
        achievements_text += "🎉 **НОВІ ДОСЯГНЕННЯ!**\n\n"
        for achievement in new_achievements:
            reward_text = await achievement_manager.give_achievement_reward(user_id, achievement)
            achievements_text += f"{achievement.icon} **{achievement.name}**\n"
            achievements_text += f"📝 {achievement.description}\n"
            achievements_text += f"🎁 {reward_text}\n\n"
    
    # Group achievements by type
    achievement_types = {
        AchievementType.COMBAT: "⚔️ **Бойові досягнення:**",
        AchievementType.EXPLORATION: "🗺️ **Дослідницькі досягнення:**",
        AchievementType.ECONOMIC: "💰 **Економічні досягнення:**",
        AchievementType.ARENA: "🏟️ **Арена досягнення:**",
        AchievementType.SOCIAL: "👥 **Соціальні досягнення:**",
        AchievementType.SPECIAL: "⭐ **Особливі досягнення:**"
    }
    
    for ach_type, type_title in achievement_types.items():
        type_achievements = achievement_manager.get_achievements_by_type(ach_type)
        achievements_text += f"\n{type_title}\n"
        
        for achievement in type_achievements:
            if achievement.hidden and achievement.id not in earned_ids:
                continue
                
            if achievement.id in earned_ids:
                achievements_text += f"✅ {achievement.icon} {achievement.name}\n"
            else:
                achievements_text += f"⭕ {achievement.icon} {achievement.name}\n"
                achievements_text += f"   📝 {achievement.condition}\n"
    
    earned_count = len(earned_ids)
    total_count = len([ach for ach in achievement_manager.get_all_achievements() if not ach.hidden])
    
    # Add timestamp if force check to make message unique
    force_check_time = context.user_data.get('force_check_time', '')
    if force_check_time:
        achievements_text += f"\n🔄 **Перевірено:** {force_check_time}"
        context.user_data.pop('force_check_time', None)  # Remove after use
    
    achievements_text += f"\n📊 **Прогрес:** {earned_count}/{total_count} досягнень"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Перевірити нові", callback_data="stats_check_achievements")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats_character")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        achievements_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show detailed statistics"""
    
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
        user_id = character.user_id
    else:
        char_dict = character
        user_id = character['user_id']
    
    stats = await db.get_statistics(user_id)
    
    detailed_text = f"""
📈 **Детальна статистика {char_dict['name']}**
━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Прогрес персонажа:**
🆔 Поточний рівень: {char_dict['level']}
⭐ Максимальний рівень: {char_dict['level']}
⚡ Всього досвіду: {char_dict['experience']}
🔥 Досвіду до наступного рівня: {char_dict['experience_needed'] - char_dict['experience']}

⚔️ **Детальна бойова статистика:**
👹 Ворогів убито: {stats.enemies_killed if stats else 0}
💥 Критичних ударів: {getattr(stats, 'critical_hits', 0) if stats else 0}
🛡 Блоків: {getattr(stats, 'blocks_made', 0) if stats else 0}
💔 Отримано шкоди: {getattr(stats, 'damage_taken', 0) if stats else 0}
⚔️ Завдано шкоди: {getattr(stats, 'damage_dealt', 0) if stats else 0}
🏃 Втеч з боїв: {getattr(stats, 'battles_fled', 0) if stats else 0}

🏰 **Підземелля:**
✅ Завершено: {stats.dungeons_completed if stats else 0}
👑 Босів убито: {getattr(stats, 'bosses_killed', 0) if stats else 0}
💎 Скарбів знайдено: {getattr(stats, 'treasures_found', 0) if stats else 0}

🌲 **Темний ліс:**
🏆 Перемог: {getattr(stats, 'forest_wins', 0) if stats else 0}
💀 Поразок: {getattr(stats, 'forest_losses', 0) if stats else 0}
🦌 Тварин убито: {getattr(stats, 'animals_killed', 0) if stats else 0}

🏟 **Арена детально:**
🥇 Перемог: {stats.arena_wins if stats else 0}
💀 Поразок: {stats.arena_losses if stats else 0}
🔥 Найкраща серія: {getattr(stats, 'best_arena_streak', 0) if stats else 0}
🏆 Чемпіонств: {getattr(stats, 'arena_championships', 0) if stats else 0}

💰 **Економіка детально:**
💸 Витрачено: {stats.gold_spent if stats else 0} золота
💎 Зароблено: {stats.gold_earned if stats else 0} золота
💰 Максимум мав: {getattr(stats, 'max_gold_owned', char_dict['gold']) if stats else char_dict['gold']} золота
🛒 Предметів куплено: {getattr(stats, 'items_bought', 0) if stats else 0}
💰 Предметів продано: {getattr(stats, 'items_sold', 0) if stats else 0}

🧪 **Використання предметів:**
🧪 Зілль використано: {getattr(stats, 'potions_used', 0) if stats else 0}
⚔️ Зброї змінено: {getattr(stats, 'weapons_equipped', 0) if stats else 0}
🛡 Броні змінено: {getattr(stats, 'armor_equipped', 0) if stats else 0}
"""
    
    keyboard = [
        [InlineKeyboardButton("🏆 Досягнення", callback_data="stats_achievements")],
        [InlineKeyboardButton("📊 Основна статистика", callback_data="stats_character")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        detailed_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle statistics callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Get character
    character = await db.get_character(user_id)
    if not character:
        await query.edit_message_text("❌ Персонаж не знайдений!")
        return
    
    if data == "stats_character":
        # Add timestamp to make message unique when refreshing
        from datetime import datetime
        context.user_data['stats_refresh_time'] = datetime.now().strftime("%H:%M:%S")
        await show_character_stats(update, context, character)
    
    elif data == "stats_achievements":
        await show_achievements(update, context, character)
    
    elif data == "stats_detailed":
        await show_detailed_stats(update, context, character)
    
    elif data == "stats_check_achievements":
        # Force check for new achievements with timestamp to make unique
        from datetime import datetime
        context.user_data['force_check_time'] = datetime.now().strftime("%H:%M:%S")
        await show_achievements(update, context, character)


def _calculate_equipment_bonuses(char_dict: dict) -> dict:
    """Calculate equipment bonuses display"""
    # This would normally check actual equipment stats
    # For now, just show if equipped
    bonuses = {
        'attack': "",
        'defense': "",
        'speed': "",
        'magic_power': ""
    }
    
    if char_dict['weapon'] != 'none':
        bonuses['attack'] = "(+спорядження)"
    if char_dict['armor'] != 'none':
        bonuses['defense'] = "(+спорядження)"
    
    return bonuses


def _get_equipment_display_name(equipment_manager, item_id: str, upgrade_level: int = 0) -> str:
    """Get display name for equipment using new system"""
    if not item_id:
        return "Немає"
    
    item = equipment_manager.get_equipment_by_id(item_id)
    if not item:
        return item_id.replace('_', ' ').title()
    
    upgrade_text = f" +{upgrade_level}" if upgrade_level > 0 else ""
    return f"{item.name}{upgrade_text}"


def _get_item_display_name(item_id: str) -> str:
    """Get display name for item (legacy function)"""
    item_names = {
        'none': 'Немає',
        'ironsword': 'Залізний меч',
        'steelsword': 'Сталевий меч',
        'magicstaff': 'Магічний посох',
        'elvenbbow': 'Ельфійський лук',
        'leatherarmor': 'Шкіряна броня',
        'chainmail': 'Кольчуга',
        'platearmor': 'Латна броня',
        'magerobe': 'Мантія мага'
    }
    return item_names.get(item_id, item_id.replace('_', ' ').title())


def _calculate_days_played(created_at) -> int:
    """Calculate days since character creation"""
    if not created_at:
        return 0
    
    try:
        if isinstance(created_at, str):
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        else:
            created_date = created_at
        
        return (datetime.now() - created_date).days
    except:
        return 0
