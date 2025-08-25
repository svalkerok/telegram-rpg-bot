"""
Admin handler - manages admin commands
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from datetime import datetime

from database.db_manager import DatabaseManager
from utils.utils_monitoring import game_metrics
import config

logger = logging.getLogger(__name__)
db = DatabaseManager(config.DATABASE_URL)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin panel"""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if user_id != config.ADMIN_USER_ID:
        await update.message.reply_text("❌ У вас немає доступу до адмін панелі!")
        return
    
    # Update metrics
    await game_metrics.update_metrics(db)
    
    admin_text = f"""
🔧 **Адміністративна панель**
━━━━━━━━━━━━━━━━━━━━━━━━━

{game_metrics.get_metrics_text()}

**Доступні команди:**
"""
    
    keyboard = [
        [InlineKeyboardButton("📊 Оновити метрики", callback_data="admin_update_metrics")],
        [InlineKeyboardButton("👥 Список користувачів", callback_data="admin_users_list")],
        [InlineKeyboardButton("💰 Додати золото", callback_data="admin_add_gold")],
        [InlineKeyboardButton("💾 Створити backup", callback_data="admin_backup")],
        [InlineKeyboardButton("📢 Розсилка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⚙️ Налаштування гри", callback_data="admin_game_settings")],
        [InlineKeyboardButton("🔄 Перезапустити бота", callback_data="admin_restart")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        admin_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Check if user is admin
    if user_id != config.ADMIN_USER_ID:
        return
    
    action = query.data.replace("admin_", "")
    
    if action == "update_metrics":
        await update_metrics(update, context)
    
    elif action == "users_list":
        await show_users_list(update, context)
    
    elif action == "add_gold":
        await show_add_gold_menu(update, context)
    
    elif action == "backup":
        await create_backup(update, context)
    
    elif action == "broadcast":
        await show_broadcast_menu(update, context)
    
    elif action == "game_settings":
        await show_game_settings(update, context)
    
    elif action == "restart":
        await restart_bot(update, context)
    
    elif action.startswith("add_gold_user_"):
        # Parse: admin_add_gold_user_USER_ID
        user_id = int(action.replace("add_gold_user_", ""))
        await show_user_gold_options(update, context, user_id)
    
    elif action.startswith("give_gold_"):
        # Parse: admin_give_gold_USER_ID_AMOUNT
        parts = action.replace("give_gold_", "").split("_")
        if len(parts) == 2:
            target_user_id = int(parts[0])
            amount = int(parts[1])
            await give_gold_to_user(update, context, target_user_id, amount)
    
    elif action.startswith("custom_gold_"):
        target_user_id = int(action.replace("custom_gold_", ""))
        # Store target user ID for custom amount input
        context.user_data['custom_gold_user_id'] = target_user_id
        await show_custom_gold_input(update, context, target_user_id)
    
    elif action == "panel":
        await show_admin_panel(update, context)


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin panel via callback"""
    # Update metrics
    await game_metrics.update_metrics(db)
    
    admin_text = f"""
🔧 **Адміністративна панель**
━━━━━━━━━━━━━━━━━━━━━━━━━

{game_metrics.get_metrics_text()}

**Доступні команди:**
"""
    
    keyboard = [
        [InlineKeyboardButton("📊 Оновити метрики", callback_data="admin_update_metrics")],
        [InlineKeyboardButton("👥 Список користувачів", callback_data="admin_users_list")],
        [InlineKeyboardButton("💰 Додати золото", callback_data="admin_add_gold")],
        [InlineKeyboardButton("💾 Створити backup", callback_data="admin_backup")],
        [InlineKeyboardButton("📢 Розсилка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⚙️ Налаштування гри", callback_data="admin_game_settings")],
        [InlineKeyboardButton("🔄 Перезапустити бота", callback_data="admin_restart")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        admin_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def update_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update and show metrics"""
    await game_metrics.update_metrics(db)
    
    metrics_text = f"""
📊 **Метрики оновлено!**
━━━━━━━━━━━━━━━━━━━━━━━━━

{game_metrics.get_metrics_text()}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад до панелі", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        metrics_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of all users"""
    users = await db.get_all_users()
    
    users_text = f"""
👥 **Список користувачів**
━━━━━━━━━━━━━━━━━━━━━━━━━
Всього: {len(users)}

"""
    
    for user in users[:20]:  # Show first 20 users
        user_line = f"• {user['username'] or 'Unknown'} (ID: {user['user_id']})"
        if user.get('name'):
            user_line += f" - {user['name']} (Рівень {user.get('level', 1)})"
        users_text += user_line + "\n"
    
    if len(users) > 20:
        users_text += f"\n... та ще {len(users) - 20} користувачів"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад до панелі", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        users_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def create_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create database backup"""
    try:
        backup_file = await db.create_backup()
        
        backup_text = f"""
✅ **Backup створено успішно!**
━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Файл: {backup_file}
📅 Час: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Backup збережено в папці /backups/
"""
        
        keyboard = [[InlineKeyboardButton("🔙 Назад до панелі", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            backup_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        await update.callback_query.answer("❌ Помилка при створенні backup!", show_alert=True)


async def show_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show broadcast menu"""
    broadcast_text = """
📢 **Розсилка повідомлень**
━━━━━━━━━━━━━━━━━━━━━━━━━
Введіть текст повідомлення для розсилки всім користувачам:

(Наступне повідомлення буде відправлено всім)
"""
    
    context.user_data['waiting_for_broadcast'] = True
    
    keyboard = [[InlineKeyboardButton("❌ Скасувати", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        broadcast_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process broadcast message"""
    if not context.user_data.get('waiting_for_broadcast'):
        return
    
    user_id = update.effective_user.id
    if user_id != config.ADMIN_USER_ID:
        return
    
    broadcast_text = update.message.text
    context.user_data['waiting_for_broadcast'] = False
    
    # Get all users
    all_users = await db.get_all_users()
    
    sent_count = 0
    failed_count = 0
    
    status_message = await update.message.reply_text("📤 Розпочато розсилку...")
    
    for user in all_users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"📢 **Повідомлення від адміністрації:**\n\n{broadcast_text}",
                parse_mode='Markdown'
            )
            sent_count += 1
            
            # Update status every 10 messages
            if sent_count % 10 == 0:
                await status_message.edit_text(f"📤 Відправлено: {sent_count}/{len(all_users)}")
                
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to {user['user_id']}: {e}")
    
    final_text = f"""
✅ **Розсилка завершена!**
━━━━━━━━━━━━━━━━━━━━━━━━━
📤 Відправлено: {sent_count}
❌ Не вдалося відправити: {failed_count}
👥 Всього користувачів: {len(all_users)}
"""
    
    await status_message.edit_text(final_text, parse_mode='Markdown')


async def show_game_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show game settings"""
    settings_text = f"""
⚙️ **Налаштування гри**
━━━━━━━━━━━━━━━━━━━━━━━━━

**Поточні налаштування:**
• Макс. рівень: {config.MAX_LEVEL}
• Базовий досвід: {config.BASE_EXP_REQUIRED}
• Множник досвіду: {config.EXP_MULTIPLIER}
• Макс. гравців: {config.MAX_PLAYERS_PER_SERVER}
• Інтервал backup: {config.BACKUP_INTERVAL_HOURS} год
• Debug режим: {config.DEBUG_MODE}

**Вартість входу в підземелля:**
• Склеп: {config.DUNGEON_ENTRY_COSTS['crypt']} золота
• Печера орків: {config.DUNGEON_ENTRY_COSTS['orcs']} золота
• Вежа чародія: {config.DUNGEON_ENTRY_COSTS['tower']} золота
• Логово дракона: {config.DUNGEON_ENTRY_COSTS['dragon']} золота
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад до панелі", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        settings_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Restart bot (placeholder)"""
    await update.callback_query.answer(
        "⚠️ Перезапуск бота потребує ручного втручання на сервері",
        show_alert=True
    )


async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /backup command"""
    user_id = update.effective_user.id
    
    if user_id != config.ADMIN_USER_ID:
        await update.message.reply_text("❌ У вас немає доступу до цієї команди!")
        return
    
    try:
        backup_file = await db.create_backup()
        await update.message.reply_text(
            f"✅ Backup створено: {backup_file}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        await update.message.reply_text("❌ Помилка при створенні backup!")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /broadcast command"""
    user_id = update.effective_user.id
    
    if user_id != config.ADMIN_USER_ID:
        await update.message.reply_text("❌ У вас немає доступу до цієї команди!")
        return
    
    # Get message text after command
    message_text = update.message.text.replace('/broadcast', '').strip()
    
    if not message_text:
        await update.message.reply_text(
            "Використання: /broadcast <текст повідомлення>",
            parse_mode='Markdown'
        )
        return
    
    # Get all users
    all_users = await db.get_all_users()
    
    sent_count = 0
    failed_count = 0
    
    status_message = await update.message.reply_text("📤 Розпочато розсилку...")
    
    for user in all_users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"📢 **Повідомлення від адміністрації:**\n\n{message_text}",
                parse_mode='Markdown'
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to {user['user_id']}: {e}")
    
    await status_message.edit_text(
        f"✅ Розсилка завершена!\nВідправлено: {sent_count}\nПомилок: {failed_count}",
        parse_mode='Markdown'
    )


async def show_add_gold_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show add gold menu"""
    # Get all users with characters
    all_users = await db.get_all_users()
    users_with_characters = []
    
    for user in all_users:
        character = await db.get_character(user['user_id'])
        if character:
            users_with_characters.append({
                'user_id': user['user_id'],
                'username': user['username'],
                'character_name': character.name,
                'current_gold': character.gold,
                'level': character.level
            })
    
    # Sort by level (highest first)
    users_with_characters.sort(key=lambda x: x['level'], reverse=True)
    
    gold_text = f"""
💰 **Додавання золота**
━━━━━━━━━━━━━━━━━━━━━━━━━

**Оберіть персонажа для додавання золота:**
**Гравці з персонажами ({len(users_with_characters)}):**
"""
    
    keyboard = []
    
    for user in users_with_characters[:20]:  # Show first 20 users
        display_name = user['username'] or f"User{user['user_id']}"
        button_text = f"{user['character_name']} ({display_name}) - {user['current_gold']}💰"
        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f"admin_add_gold_user_{user['user_id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад до панелі", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        gold_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def process_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE, user_action: str) -> None:
    """Process user-related actions"""
    if user_action.startswith("add_gold_user_"):
        user_id = int(user_action.replace("add_gold_user_", ""))
        await show_user_gold_options(update, context, user_id)
    
    elif user_action.startswith("quick_gold_"):
        amount = int(user_action.replace("quick_gold_", ""))
        await show_quick_gold_users(update, context, amount)


async def show_user_gold_options(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int) -> None:
    """Show gold options for specific user"""
    character = await db.get_character(target_user_id)
    if not character:
        await update.callback_query.answer("❌ Персонаж не знайдено!", show_alert=True)
        return
    
    user = await db.get_user(target_user_id)
    display_name = user.username if user else f"User{target_user_id}"
    
    gold_text = f"""
💰 **Додавання золота**
━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **Гравець:** {character.name}
📱 **Username:** {display_name}
⭐ **Рівень:** {character.level}
💰 **Поточне золото:** {character.gold:,}

**Оберіть суму для додавання:**
"""
    
    keyboard = []
    
    # Quick amounts
    amounts = [100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]
    for i in range(0, len(amounts), 2):
        row = []
        row.append(InlineKeyboardButton(
            f"+{amounts[i]:,}💰",
            callback_data=f"admin_give_gold_{target_user_id}_{amounts[i]}"
        ))
        if i + 1 < len(amounts):
            row.append(InlineKeyboardButton(
                f"+{amounts[i+1]:,}💰",
                callback_data=f"admin_give_gold_{target_user_id}_{amounts[i+1]}"
            ))
        keyboard.append(row)
    
    # Custom amount
    keyboard.append([InlineKeyboardButton("✏️ Власна сума", callback_data=f"admin_custom_gold_{target_user_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад до списку", callback_data="admin_add_gold")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        gold_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_quick_gold_users(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int) -> None:
    """Show users for quick gold addition"""
    # Get all users with characters
    all_users = await db.get_all_users()
    users_with_characters = []
    
    for user in all_users:
        character = await db.get_character(user['user_id'])
        if character:
            users_with_characters.append({
                'user_id': user['user_id'],
                'username': user['username'],
                'character_name': character.name,
                'current_gold': character.gold,
                'level': character.level
            })
    
    # Sort by level (highest first)
    users_with_characters.sort(key=lambda x: x['level'], reverse=True)
    
    gold_text = f"""
💰 **Додати +{amount:,} золота**
━━━━━━━━━━━━━━━━━━━━━━━━━

**Оберіть гравця:**
"""
    
    keyboard = []
    
    for user in users_with_characters[:20]:  # Show first 20 users
        display_name = user['username'] or f"User{user['user_id']}"
        button_text = f"{user['character_name']} ({display_name})"
        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f"admin_give_gold_{user['user_id']}_{amount}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад до списку", callback_data="admin_add_gold")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        gold_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def give_gold_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int, amount: int) -> None:
    """Give gold to specific user"""
    try:
        # Get current character
        character = await db.get_character(target_user_id)
        if not character:
            await update.callback_query.answer("❌ Персонаж не знайдено!", show_alert=True)
            return
        
        # Update gold
        new_gold = character.gold + amount
        await db.update_character_by_id(target_user_id, {'gold': new_gold})
        
        # Get user info
        user = await db.get_user(target_user_id)
        display_name = user.username if user else f"User{target_user_id}"
        
        # Log the action
        admin_user_id = update.effective_user.id
        logger.info(f"Admin {admin_user_id} gave {amount:,} gold to user {target_user_id} ({display_name})")
        
        # Show success message
        success_text = f"""
✅ **Золото додано!**
━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **Гравець:** {character.name}
📱 **Username:** {display_name}
💰 **Додано:** +{amount:,} золота
💰 **Нове золото:** {new_gold:,}

**Дія виконана адміністратором.**
"""
        
        keyboard = [
            [InlineKeyboardButton("💰 Додати ще золота", callback_data=f"admin_add_gold_user_{target_user_id}")],
            [InlineKeyboardButton("🔙 Назад до меню", callback_data="admin_add_gold")],
            [InlineKeyboardButton("🏠 Адмін панель", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            success_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error giving gold to user {target_user_id}: {e}")
        await update.callback_query.answer("❌ Помилка при додаванні золота!", show_alert=True)


async def show_custom_gold_input(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int) -> None:
    """Show custom gold input interface"""
    character = await db.get_character(target_user_id)
    if not character:
        await update.callback_query.answer("❌ Персонаж не знайдено!", show_alert=True)
        return
    
    user = await db.get_user(target_user_id)
    display_name = user.username if user else f"User{target_user_id}"
    
    gold_text = f"""
💰 **Власна сума золота**
━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **Гравець:** {character.name}
📱 **Username:** {display_name}
💰 **Поточне золото:** {character.gold:,}

**Введіть суму для додавання:**
(Наприклад: 1500, 10000, 50000)
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=f"admin_add_gold_user_{target_user_id}")],
        [InlineKeyboardButton("🏠 Адмін панель", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        gold_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def process_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process admin message input (broadcast or custom gold)"""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if user_id != config.ADMIN_USER_ID:
        return
    
    # Check if we're waiting for custom gold input
    if 'custom_gold_user_id' in context.user_data:
        await process_custom_gold_input(update, context)
        return
    
    # Check if we're waiting for broadcast message
    if 'waiting_for_broadcast' in context.user_data:
        await process_broadcast(update, context)
        return
    
    # Default: treat as broadcast message
    await process_broadcast(update, context)


async def process_custom_gold_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process custom gold amount input"""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if user_id != config.ADMIN_USER_ID:
        return
    
    # Get target user ID from context
    target_user_id = context.user_data.get('custom_gold_user_id')
    if not target_user_id:
        await update.message.reply_text("❌ Помилка: не знайдено цільового гравця!")
        return
    
    # Get amount from message
    try:
        amount = int(update.message.text.strip())
        if amount <= 0:
            await update.message.reply_text("❌ Сума повинна бути більше 0!")
            return
        if amount > 1000000:  # Limit to 1 million
            await update.message.reply_text("❌ Сума не може перевищувати 1,000,000!")
            return
    except ValueError:
        await update.message.reply_text("❌ Будь ласка, введіть число!")
        return
    
    # Give gold
    try:
        character = await db.get_character(target_user_id)
        if not character:
            await update.message.reply_text("❌ Персонаж не знайдено!")
            return
        
        new_gold = character.gold + amount
        await db.update_character_by_id(target_user_id, {'gold': new_gold})
        
        user = await db.get_user(target_user_id)
        display_name = user.username if user else f"User{target_user_id}"
        
        # Log the action
        logger.info(f"Admin {user_id} gave {amount:,} gold to user {target_user_id} ({display_name})")
        
        success_text = f"""
✅ **Золото додано!**
━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **Гравець:** {character.name}
📱 **Username:** {display_name}
💰 **Додано:** +{amount:,} золота
💰 **Нове золото:** {new_gold:,}

**Дія виконана адміністратором.**
"""
        
        keyboard = [
            [InlineKeyboardButton("💰 Додати ще золота", callback_data=f"admin_add_gold_user_{target_user_id}")],
            [InlineKeyboardButton("🔙 Назад до меню", callback_data="admin_add_gold")],
            [InlineKeyboardButton("🏠 Адмін панель", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            success_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Clear custom gold user ID
        if 'custom_gold_user_id' in context.user_data:
            del context.user_data['custom_gold_user_id']
        
    except Exception as e:
        logger.error(f"Error giving custom gold to user {target_user_id}: {e}")
        await update.message.reply_text("❌ Помилка при додаванні золота!")