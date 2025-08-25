"""
Tavern handler - main game menu
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import asyncio

from database.db_manager import DatabaseManager
import config

logger = logging.getLogger(__name__)
db = DatabaseManager(config.DATABASE_URL)


async def show_tavern_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show tavern menu (main menu)"""
    
    # Convert Character object to dict for template if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
    else:
        char_dict = character
    
    # Check rest status
    from game_logic.rest_manager import rest_manager
    user_id = char_dict.get('user_id', character.user_id)
    is_resting = rest_manager.is_resting(user_id)
    
    tavern_text = config.TAVERN_MESSAGE.format(
        name=char_dict.get('name', character.name),
        level=char_dict.get('level', character.level),
        health=char_dict.get('health', character.health),
        max_health=char_dict.get('max_health', character.max_health),
        experience=char_dict.get('experience', character.experience),
        experience_needed=char_dict.get('experience_needed', character.experience_needed),
        gold=char_dict.get('gold', character.gold)
    )
    
    # Add rest status if resting
    if is_resting:
        progress = rest_manager.get_rest_progress(user_id)
        if progress:
            time_remaining = int(progress['time_remaining'])
            minutes = time_remaining // 60
            seconds = time_remaining % 60
            
            tavern_text += f"\n\n🏠 **Відпочинок в прогресі...**\n"
            tavern_text += f"💚 Здоров'я: {progress['current_health']}/{progress['max_health']}\n"
            tavern_text += f"💚 {progress['health_bar']}\n"
            tavern_text += f"📊 Прогрес відпочинку: {progress['progress_bar']}\n"
            tavern_text += f"⏱️ Залишилось: {minutes:02d}:{seconds:02d}\n"
            tavern_text += f"💚 Відновлено: +{progress['total_healed']} HP\n"
            tavern_text += f"🔄 Оновлюється кожні 15 секунд"
    
    keyboard = [
        [InlineKeyboardButton("🗡 Підземелля", callback_data="tavern_dungeons")],
        [InlineKeyboardButton("⚔️ Арена", callback_data="tavern_arena")],
        [InlineKeyboardButton("🌲 Темний ліс", callback_data="tavern_forest")],
        [InlineKeyboardButton("🛒 Торговець Олаф", callback_data="merchant_main")],
        [InlineKeyboardButton("⚒️ Кузня гнома Торіна", callback_data="tavern_blacksmith")],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="tavern_stats"),
            InlineKeyboardButton("📦 Інвентар", callback_data="inventory_main")
        ],
        [
            InlineKeyboardButton("📋 Завдання", callback_data="tavern_quests"),
            InlineKeyboardButton("🏆 Досягнення", callback_data="tavern_achievements")
        ]
    ]
    
    # Add rest button with different text based on status
    if is_resting:
        keyboard.append([
            InlineKeyboardButton("⏹️ Зупинити відпочинок", callback_data="tavern_stop_rest"),
            InlineKeyboardButton("💀 Видалити персонажа", callback_data="tavern_delete")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("🏠 Відпочинок", callback_data="tavern_rest"),
            InlineKeyboardButton("💀 Видалити персонажа", callback_data="tavern_delete")
        ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            tavern_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            tavern_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def show_tavern_menu_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show tavern menu from a regular message (not callback)"""
    await show_tavern_menu(update, context, character)


async def tavern_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle tavern menu callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data.replace("tavern_", "")
    
    # Get character data
    character = await db.get_character(user_id)
    
    if not character:
        await query.edit_message_text(
            "❌ У вас немає персонажа! Використайте /start щоб створити."
        )
        return
    
    # Handle actions
    if action == "main":
        await show_tavern_menu(update, context, character)
        
    elif action == "dungeons":
        from handlers.dungeon_handler import show_dungeons_menu
        await show_dungeons_menu(update, context, character)
        
    elif action == "arena":
        from handlers.arena_handler import show_arena_menu
        await show_arena_menu(update, context, character)
        
    elif action == "forest":
        from handlers.forest_handler import show_forest_menu
        await show_forest_menu(update, context, character)
        
    elif action == "shop":
        from handlers.shop_handler import show_shop_menu
        await show_shop_menu(update, context, character)
        
    elif action == "stats":
        from handlers.stats_handler import show_character_stats
        await show_character_stats(update, context, character)
        
    elif action == "inventory":
        await show_inventory(update, context, character)
        
    elif action == "quests":
        from handlers.daily_quests_handler import show_daily_quests
        await show_daily_quests(update, context, character)
        
    elif action == "achievements":
        from handlers.stats_handler import show_achievements
        await show_achievements(update, context, character)
        
    elif action == "rest":
        await rest_character(update, context, character)
        
    elif action == "stop_rest":
        await stop_rest(update, context)
        
    elif action == "delete":
        await confirm_character_deletion(update, context, character)
    
    elif action == "blacksmith":
        from handlers.equipment_handler import show_blacksmith
        await show_blacksmith(update, context)
    
    # Handle potion usage
    elif query.data.startswith("tavern_use_potion_"):
        potion_id = query.data.replace("tavern_use_potion_", "")
        await use_potion(update, context, character, potion_id)


async def show_character_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show character statistics"""
    # Convert Character object if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
        user_id = character.user_id
    else:
        char_dict = character
        user_id = character['user_id']
    
    stats = await db.get_statistics(user_id)
    
    # Get class info
    char_class = char_dict['class']
    class_info = config.CHARACTER_CLASSES.get(char_class, config.CHARACTER_CLASSES['warrior'])
    
    stats_text = f"""
📊 **Статистика {char_dict['name']}**
━━━━━━━━━━━━━━━━━━━━━━━━━
👤 Клас: {class_info['name']} {class_info['emoji']}
⭐ Рівень: {char_dict['level']}
⚡ Досвід: {char_dict['experience']}/{char_dict['experience_needed']}
💚 Здоров'я: {char_dict['health']}/{char_dict['max_health']}
💰 Золото: {char_dict['gold']}

⚔️ Атака: {char_dict['attack']}
🛡 Захист: {char_dict['defense']}
⚡ Швидкість: {char_dict['speed']}
"""
    
    if stats:
        stats_dict = stats.to_dict() if hasattr(stats, 'to_dict') else stats
        stats_text += f"""
**Битви:**
👹 Ворогів вбито: {stats_dict['enemies_killed']}
🏆 Перемог на арені: {stats_dict['arena_wins']}
💀 Поразок на арені: {stats_dict['arena_losses']}
"""
    
    keyboard = [[InlineKeyboardButton("🏛 Назад до таверни", callback_data="tavern_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show character inventory"""
    # Convert Character object if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
        user_id = character.user_id
    else:
        char_dict = character
        user_id = character['user_id']
    
    inventory = await db.get_inventory(user_id)
    
    inventory_text = f"""
📦 **Інвентар {char_dict['name']}**
━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Золото: {char_dict['gold']}

**Споряджено:**
⚔️ Зброя: {char_dict['weapon']}
🛡 Броня: {char_dict['armor']}

**Предмети:**
"""
    
    keyboard = []
    
    if inventory and inventory.items:
        # Group potions for easy use
        potions = [item for item in inventory.items if item.item_type == 'potion']
        other_items = [item for item in inventory.items if item.item_type != 'potion']
        
        if potions:
            inventory_text += "\n**🧪 Зілля:**"
            for item in potions:
                inventory_text += f"\n• {item.name} x{item.quantity}"
                # Add use button for each potion type
                if item.quantity > 0:
                    keyboard.append([InlineKeyboardButton(
                        f"🧪 Використати {item.name}",
                        callback_data=f"tavern_use_potion_{item.item_id}"
                    )])
        
        if other_items:
            inventory_text += "\n\n**📦 Інші предмети:**"
            for item in other_items:
                inventory_text += f"\n• {item.name} x{item.quantity}"
    else:
        inventory_text += "\n🔍 Інвентар порожній"
    
    # Navigation buttons
    keyboard.extend([
        [InlineKeyboardButton("🛒 До магазину", callback_data="tavern_shop")],
        [InlineKeyboardButton("🏛 Назад до таверни", callback_data="tavern_main")]
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        inventory_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_daily_quests(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show daily quests"""
    quests_text = """
📋 **Щоденні завдання**
━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 Система щоденних завдань буде доступна найближчим часом!

Повертайтесь пізніше!
"""
    
    keyboard = [[InlineKeyboardButton("🏛 Назад до таверни", callback_data="tavern_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        quests_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show achievements"""
    achievements_text = """
🏆 **Досягнення**
━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 Система досягнень буде доступна найближчим часом!

Слідкуйте за оновленнями!
"""
    
    keyboard = [[InlineKeyboardButton("🏛 Назад до таверни", callback_data="tavern_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        achievements_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def rest_character(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Rest to restore health gradually"""
    # Convert Character object if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
        user_id = character.user_id
    else:
        char_dict = character
        user_id = character['user_id']
    
    from game_logic.rest_manager import rest_manager
    
    # Check if already resting
    if rest_manager.is_resting(user_id):
        # Show current rest status
        progress = rest_manager.get_rest_progress(user_id)
        if progress:
            time_remaining = int(progress['time_remaining'])
            minutes = time_remaining // 60
            seconds = time_remaining % 60
            
            text = f"""
🏠 **Відпочинок в прогресі...**
━━━━━━━━━━━━━━━━━━━━━━━━━
💚 Здоров'я: {progress['current_health']}/{progress['max_health']}
💚 {progress['health_bar']}
📊 Прогрес відпочинку: {progress['progress_bar']}
⏱️ Залишилось: {minutes:02d}:{seconds:02d}
💚 Відновлено: +{progress['total_healed']} HP

💡 Відновлення: +{progress['heal_per_tick']} HP кожні 15 секунд
"""
            
            keyboard = [
                [InlineKeyboardButton("⏹️ Зупинити відпочинок", callback_data="tavern_stop_rest")],
                [InlineKeyboardButton("🛒 Купити зілля", callback_data="merchant_potions")],
                [InlineKeyboardButton("🏛 Назад до таверни", callback_data="tavern_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
    
    # Start new rest session
    result = await rest_manager.start_rest(user_id, char_dict, db)
    
    if result['success']:
        text = f"""
🏠 **Відпочинок розпочато!**
━━━━━━━━━━━━━━━━━━━━━━━━━
{result['message']}

💡 **Поради:**
• Купіть зілля для швидшого відновлення
• Можете займатися іншими справами під час відпочинку
• Відпочинок автоматично зупиниться при повному здоров'ї
"""
        
        keyboard = [
            [InlineKeyboardButton("⏹️ Зупинити відпочинок", callback_data="tavern_stop_rest")],
            [InlineKeyboardButton("🛒 Купити зілля", callback_data="merchant_potions")],
            [InlineKeyboardButton("🏛 Назад до таверни", callback_data="tavern_main")]
        ]
    else:
        text = f"❌ {result['message']}"
        keyboard = [[InlineKeyboardButton("🏛 Назад до таверни", callback_data="tavern_main")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Start auto-refresh if resting
    if result['success']:
        # Store message info for auto-refresh
        context.user_data['rest_message_id'] = update.callback_query.message.message_id
        context.user_data['rest_chat_id'] = update.callback_query.message.chat_id
        logger.info(f"Starting rest auto-refresh for user {user_id}, message {update.callback_query.message.message_id}")
        asyncio.create_task(auto_refresh_rest_status(context, user_id))


async def auto_refresh_rest_status(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Auto-refresh rest status every 15 seconds"""
    
    from game_logic.rest_manager import rest_manager
    
    try:
        while rest_manager.is_resting(user_id):
            # Wait 15 seconds
            await asyncio.sleep(15)
            
            if not rest_manager.is_resting(user_id):
                break
            
            # Get updated progress
            progress = rest_manager.get_rest_progress(user_id)
            if not progress:
                break
            
            time_remaining = int(progress['time_remaining'])
            minutes = time_remaining // 60
            seconds = time_remaining % 60
            
            text = f"""
🏠 **Відпочинок в прогресі...**
━━━━━━━━━━━━━━━━━━━━━━━━━
💚 Здоров'я: {progress['current_health']}/{progress['max_health']}
💚 {progress['health_bar']}
📊 Прогрес відпочинку: {progress['progress_bar']}
⏱️ Залишилось: {minutes:02d}:{seconds:02d}
💚 Відновлено: +{progress['total_healed']} HP

💡 Відновлення: +{progress['heal_per_tick']} HP кожні 15 секунд
"""
            
            keyboard = [
                [InlineKeyboardButton("⏹️ Зупинити відпочинок", callback_data="tavern_stop_rest")],
                [InlineKeyboardButton("🛒 Купити зілля", callback_data="merchant_potions")],
                [InlineKeyboardButton("🏛 Назад до таверни", callback_data="tavern_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                # Get message info from context
                message_id = context.user_data.get('rest_message_id')
                chat_id = context.user_data.get('rest_chat_id')
                
                if message_id and chat_id:
                    logger.info(f"Updating rest message for user {user_id}, message {message_id}")
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                else:
                    # Message info not available, stop refreshing
                    logger.warning(f"Rest message info not available for user {user_id}")
                    break
                    
            except Exception as e:
                logger.error(f"Error updating rest message: {e}")
                # Message might be too old to edit, stop refreshing
                break
                
    except Exception as e:
        logger.error(f"Error in auto-refresh rest status: {e}")


async def stop_rest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop rest session"""
    
    user_id = update.effective_user.id
    from game_logic.rest_manager import rest_manager
    
    # Clear rest message data from context
    if 'rest_message_id' in context.user_data:
        del context.user_data['rest_message_id']
    if 'rest_chat_id' in context.user_data:
        del context.user_data['rest_chat_id']
    
    result = await rest_manager.stop_rest(user_id)
    
    if result['success']:
        logger.info(f"Rest stopped for user {user_id}: {result['message']}")
        text = f"""
🏠 **Відпочинок завершено!**
━━━━━━━━━━━━━━━━━━━━━━━━━
{result['message']}

💡 **Поради:**
• Купіть зілля для швидшого відновлення
• Поверніться до відпочинку коли потрібно
"""
    else:
        logger.warning(f"Failed to stop rest for user {user_id}: {result['message']}")
        text = f"❌ {result['message']}"
    
    keyboard = [
        [InlineKeyboardButton("🏠 Відпочити знову", callback_data="tavern_rest")],
        [InlineKeyboardButton("🛒 Купити зілля", callback_data="merchant_potions")],
        [InlineKeyboardButton("🏛 Назад до таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def confirm_character_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Confirm character deletion"""
    # Convert Character object if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
    else:
        char_dict = character
        
    text = f"""
⚠️ **УВАГА!**

Ви дійсно хочете видалити персонажа **{char_dict['name']}**?

Це видалить:
• Всі досягнення
• Весь інвентар
• Всю статистику
• Весь прогрес

**Цю дію неможливо відмінити!**
"""
    
    keyboard = [
        [InlineKeyboardButton("❌ Так, видалити", callback_data="confirm_delete_yes")],
        [InlineKeyboardButton("✅ Ні, залишити", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def delete_character_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Actually delete the character after confirmation"""
    user_id = update.effective_user.id
    
    # Delete character from database
    success = await db.delete_character(user_id)
    
    if success:
        text = """
💀 **ПЕРСОНАЖА ВИДАЛЕНО**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ваш персонаж та всі дані були успішно видалені.

Дякуємо за гру! Ви можете створити нового персонажа в будь-який час командою /start.
"""
        keyboard = [
            [InlineKeyboardButton("🆕 Створити нового персонажа", callback_data="start_new_character")]
        ]
    else:
        text = """
❌ **ПОМИЛКА**
━━━━━━━━━━━━━━━━━━━━━━━━━
Виникла помилка при видаленні персонажа.

Спробуйте ще раз або зверніться до адміністратора.
"""
        keyboard = [
            [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def use_potion(update: Update, context: ContextTypes.DEFAULT_TYPE, character, potion_id: str) -> None:
    """Use a potion from inventory"""
    
    # Convert Character object if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
        user_id = character.user_id
    else:
        char_dict = character
        user_id = character['user_id']
    
    # Get potion info from shop data
    from handlers.shop_handler import SHOP_ITEMS
    potion_info = None
    for category in SHOP_ITEMS.values():
        if potion_id in category:
            potion_info = category[potion_id]
            break
    
    if not potion_info:
        await update.callback_query.answer("❌ Зілля не знайдено!", show_alert=True)
        return
    
    # Check if player has this potion
    inventory = await db.get_inventory(user_id)
    has_potion = False
    for item in inventory.items:
        if item.item_id == potion_id and item.quantity > 0:
            has_potion = True
            break
    
    if not has_potion:
        await update.callback_query.answer("❌ У вас немає цього зілля!", show_alert=True)
        return
    
    # Apply potion effects
    updates = {}
    effects_text = ""
    
    # Instant effects
    if 'health' in potion_info:
        new_health = min(char_dict['max_health'], char_dict['health'] + potion_info['health'])
        health_gained = new_health - char_dict['health']
        updates['health'] = new_health
        effects_text += f"💚 Відновлено {health_gained} здоров'я\n"
    
    if 'mana' in potion_info:
        new_mana = min(char_dict['max_mana'], char_dict['mana'] + potion_info['mana'])
        mana_gained = new_mana - char_dict['mana']
        updates['mana'] = new_mana
        effects_text += f"⚡ Відновлено {mana_gained} мани\n"
    
    # Temporary effects (store in context for combat)
    temp_effects = {}
    if 'attack_boost' in potion_info:
        temp_effects['attack_boost'] = {
            'value': potion_info['attack_boost'],
            'duration': potion_info.get('duration', 1)
        }
        effects_text += f"⚔️ Атака +{potion_info['attack_boost']} на {potion_info.get('duration', 1)} ходів\n"
    
    if 'defense_boost' in potion_info:
        temp_effects['defense_boost'] = {
            'value': potion_info['defense_boost'],
            'duration': potion_info.get('duration', 1)
        }
        effects_text += f"🛡️ Захист +{potion_info['defense_boost']} на {potion_info.get('duration', 1)} ходів\n"
    
    if 'speed_boost' in potion_info:
        temp_effects['speed_boost'] = {
            'value': potion_info['speed_boost'],
            'duration': potion_info.get('duration', 1)
        }
        effects_text += f"⚡ Швидкість +{potion_info['speed_boost']} на {potion_info.get('duration', 1)} ходів\n"
    
    if 'health_regen' in potion_info:
        temp_effects['health_regen'] = {
            'value': potion_info['health_regen'],
            'duration': potion_info.get('duration', 1)
        }
        effects_text += f"💚 Регенерація {potion_info['health_regen']} HP/хід на {potion_info.get('duration', 1)} ходів\n"
    
    # Store temporary effects in user context
    if temp_effects:
        if 'temp_effects' not in context.user_data:
            context.user_data['temp_effects'] = {}
        context.user_data['temp_effects'].update(temp_effects)
    
    # Update character
    if updates:
        await db.update_character_by_id(user_id, updates)
    
    # Remove potion from inventory
    await db.remove_item_from_inventory(user_id, potion_id, 1)
    
    # Update statistics
    await db.update_statistics_by_id(user_id, {'potions_used': 1})
    
    use_text = f"""
🧪 **Зілля використано!**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви випили: **{potion_info['name']}**

**Ефекти:**
{effects_text}
{'🕐 Тимчасові ефекти будуть активні в бою!' if temp_effects else ''}
"""
    
    keyboard = [
        [InlineKeyboardButton("📦 Назад до інвентаря", callback_data="tavern_inventory")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        use_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )