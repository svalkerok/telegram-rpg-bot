"""
Equipment and Inventory Handler for Telegram RPG Bot
Handles merchant, blacksmith, inventory management
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from database.db_manager import DatabaseManager
from game_logic.equipment import EquipmentManager, EquipmentType, CharacterClass
from game_logic.inventory_manager import InventoryManager
import config

logger = logging.getLogger(__name__)
db = DatabaseManager(config.DATABASE_URL)


async def show_merchant_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show merchant shop with class-specific items"""
    
    user_id = update.effective_user.id
    character = await db.get_character(user_id)
    
    if not character:
        await update.callback_query.answer("❌ Спочатку створіть персонажа!")
        return
    
    equipment_manager = EquipmentManager(db)
    
    # Get available equipment for character class
    weapons = equipment_manager.get_class_equipment(character.character_class, "weapon")
    armor = equipment_manager.get_class_equipment(character.character_class, "armor")
    
    # Filter by level and affordable items
    affordable_weapons = [w for w in weapons if w.level_requirement <= character.level and w.base_price <= character.gold * 2]
    affordable_armor = [a for a in armor if a.level_requirement <= character.level and a.base_price <= character.gold * 2]
    
    class_names = {
        "warrior": "воїна",
        "mage": "мага", 
        "ranger": "рейнджера"
    }
    
    merchant_text = f"""
🏪 **Торговець Олаф**
━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Ваше золото: {int(character.gold):,}
👤 Клас: {class_names.get(character.character_class, character.character_class)}

⚔️ **Зброя для {class_names.get(character.character_class, character.character_class)}:**
"""
    
    for i, weapon in enumerate(affordable_weapons[:5], 1):
        status = "✅" if character.gold >= weapon.base_price else "❌"
        quality_stars = "⭐" * (weapon.quality.value.count("common") + weapon.quality.value.count("uncommon")*2 + weapon.quality.value.count("rare")*3 + weapon.quality.value.count("epic")*4 + weapon.quality.value.count("legendary")*5)
        
        merchant_text += f"\n{i}. {weapon.name} - {weapon.base_price:,} 💰 {quality_stars}\n"
        merchant_text += f"   📊 Атака: +{weapon.base_stats.attack} | Рівень: {weapon.level_requirement}+ {status}\n"
    
    merchant_text += f"\n🛡️ **Броня для {class_names.get(character.character_class, character.character_class)}:**\n"
    
    for i, armor_item in enumerate(affordable_armor[:5], 1):
        status = "✅" if character.gold >= armor_item.base_price else "❌"
        quality_stars = "⭐" * (1 + armor_item.quality.value.count("uncommon") + armor_item.quality.value.count("rare")*2 + armor_item.quality.value.count("epic")*3 + armor_item.quality.value.count("legendary")*4)
        
        merchant_text += f"\n{i}. {armor_item.name} - {armor_item.base_price:,} 💰 {quality_stars}\n"
        merchant_text += f"   📊 Захист: +{armor_item.base_stats.defense} | Рівень: {armor_item.level_requirement}+ {status}\n"
    
    if not affordable_weapons and not affordable_armor:
        merchant_text += "\n🚫 Немає доступних предметів для вашого рівня та бюджету."
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Купити зброю", callback_data="merchant_weapons")],
        [InlineKeyboardButton("🛡️ Купити броню", callback_data="merchant_armor")],
        [InlineKeyboardButton("🧪 Купити зілля", callback_data="merchant_potions")],
        [InlineKeyboardButton("📦 Мій інвентар", callback_data="inventory_main")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            merchant_text, reply_markup=reply_markup, parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            merchant_text, reply_markup=reply_markup, parse_mode='Markdown'
        )


async def show_weapon_shop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show weapons available for purchase"""
    
    user_id = update.effective_user.id
    character = await db.get_character(user_id)
    
    if not character:
        await update.callback_query.answer("❌ Персонаж не знайдено!")
        return
    
    equipment_manager = EquipmentManager(db)
    all_weapons = equipment_manager.get_class_equipment(character.character_class, "weapon")
    
    # Filter weapons by level (show all available levels, not just affordable)
    available_weapons = [w for w in all_weapons if w.level_requirement <= character.level + 5]  # Show a few levels ahead
    
    class_names = {
        "warrior": "воїна",
        "mage": "мага", 
        "ranger": "рейнджера"
    }
    
    weapons_text = f"""
⚔️ **Зброя для {class_names.get(character.character_class, character.character_class)}**
━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Ваше золото: {int(character.gold):,}
⭐ Рівень персонажа: {character.level}

"""
    
    keyboard = []
    
    if not available_weapons:
        weapons_text += "🚫 Немає доступної зброї для вашого класу."
    else:
        for weapon in available_weapons:
            can_afford = character.gold >= weapon.base_price
            level_ok = weapon.level_requirement <= character.level
            
            # Status indicators
            if level_ok and can_afford:
                status = "✅ Доступно"
            elif level_ok and not can_afford:
                status = "💰 Недостатньо золота"
            else:
                status = f"📈 Потрібен {weapon.level_requirement} рівень"
            
            # Quality stars
            quality_mapping = {
                "common": "⭐",
                "uncommon": "⭐⭐", 
                "rare": "⭐⭐⭐",
                "epic": "⭐⭐⭐⭐",
                "legendary": "⭐⭐⭐⭐⭐"
            }
            quality_stars = quality_mapping.get(weapon.quality.value, "⭐")
            
            weapons_text += f"🗡 **{weapon.name}** {quality_stars}\n"
            weapons_text += f"   💰 Ціна: {weapon.base_price:,} золота\n"
            weapons_text += f"   📊 Атака: +{weapon.base_stats.attack}\n"
            weapons_text += f"   📈 Рівень: {weapon.level_requirement}+\n"
            weapons_text += f"   📊 Статус: {status}\n"
            
            if weapon.special_effects:
                weapons_text += f"   🌟 Ефекти: "
                effects = [effect.description for effect in weapon.special_effects]
                weapons_text += ", ".join(effects) + "\n"
            
            weapons_text += f"   📝 {weapon.description}\n\n"
            
            # Add buy button if can purchase
            if level_ok and can_afford:
                keyboard.append([InlineKeyboardButton(
                    f"💰 Купити {weapon.name} ({weapon.base_price:,} 💰)",
                    callback_data=f"buy_weapon_{weapon.id}"
                )])
    
    keyboard.extend([
        [InlineKeyboardButton("🛡️ Броня", callback_data="merchant_armor")],
        [InlineKeyboardButton("🔙 Назад до магазину", callback_data="merchant_main")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        weapons_text, reply_markup=reply_markup, parse_mode='Markdown'
    )


async def show_armor_shop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show armor available for purchase"""
    
    user_id = update.effective_user.id
    character = await db.get_character(user_id)
    
    if not character:
        await update.callback_query.answer("❌ Персонаж не знайдено!")
        return
    
    equipment_manager = EquipmentManager(db)
    all_armor = equipment_manager.get_class_equipment(character.character_class, "armor")
    
    # Filter armor by level (show all available levels, not just affordable)
    available_armor = [a for a in all_armor if a.level_requirement <= character.level + 5]  # Show a few levels ahead
    
    class_names = {
        "warrior": "воїна",
        "mage": "мага", 
        "ranger": "рейнджера"
    }
    
    armor_text = f"""
🛡️ **Броня для {class_names.get(character.character_class, character.character_class)}**
━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Ваше золото: {int(character.gold):,}
⭐ Рівень персонажа: {character.level}

"""
    
    keyboard = []
    
    if not available_armor:
        armor_text += "🚫 Немає доступної броні для вашого класу."
    else:
        for armor_item in available_armor:
            can_afford = character.gold >= armor_item.base_price
            level_ok = armor_item.level_requirement <= character.level
            
            # Status indicators
            if level_ok and can_afford:
                status = "✅ Доступно"
            elif level_ok and not can_afford:
                status = "💰 Недостатньо золота"
            else:
                status = f"📈 Потрібен {armor_item.level_requirement} рівень"
            
            # Quality stars
            quality_mapping = {
                "common": "⭐",
                "uncommon": "⭐⭐", 
                "rare": "⭐⭐⭐",
                "epic": "⭐⭐⭐⭐",
                "legendary": "⭐⭐⭐⭐⭐"
            }
            quality_stars = quality_mapping.get(armor_item.quality.value, "⭐")
            
            armor_text += f"🛡 **{armor_item.name}** {quality_stars}\n"
            armor_text += f"   💰 Ціна: {armor_item.base_price:,} золота\n"
            armor_text += f"   📊 Захист: +{armor_item.base_stats.defense}\n"
            armor_text += f"   📈 Рівень: {armor_item.level_requirement}+\n"
            armor_text += f"   📊 Статус: {status}\n"
            
            if armor_item.special_effects:
                armor_text += f"   🌟 Ефекти: "
                effects = [effect.description for effect in armor_item.special_effects]
                armor_text += ", ".join(effects) + "\n"
            
            armor_text += f"   📝 {armor_item.description}\n\n"
            
            # Add buy button if can purchase
            if level_ok and can_afford:
                keyboard.append([InlineKeyboardButton(
                    f"💰 Купити {armor_item.name} ({armor_item.base_price:,} 💰)",
                    callback_data=f"buy_armor_{armor_item.id}"
                )])
    
    keyboard.extend([
        [InlineKeyboardButton("⚔️ Зброя", callback_data="merchant_weapons")],
        [InlineKeyboardButton("🔙 Назад до магазину", callback_data="merchant_main")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        armor_text, reply_markup=reply_markup, parse_mode='Markdown'
    )


async def show_potion_shop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show potions available for purchase"""
    
    user_id = update.effective_user.id
    character = await db.get_character(user_id)
    
    if not character:
        await update.callback_query.answer("❌ Персонаж не знайдено!")
        return
    
    from game_logic.potion_manager import potion_manager
    
    potions = potion_manager.get_all_potions()
    
    potion_text = f"""
🧪 **Зілля та еліксири**
━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Ваше золото: {int(character.gold):,}
⭐ Рівень персонажа: {character.level}

"""
    
    keyboard = []
    
    # Group potions by type
    health_potions = potion_manager.get_potions_by_type('health')
    mana_potions = potion_manager.get_potions_by_type('mana')
    combat_potions = potion_manager.get_potions_by_type('combat')
    
    # Health potions
    potion_text += "💚 **Зілля здоров'я:**\n"
    for potion_id, potion in health_potions.items():
        can_afford = character.gold >= potion.price
        level_ok = potion.level_required <= character.level
        
        if level_ok and can_afford:
            status = "✅ Доступно"
        elif level_ok and not can_afford:
            status = "💰 Недостатньо золота"
        else:
            status = f"📈 Потрібен {potion.level_required} рівень"
        
        potion_text += f"🧪 **{potion.name}**\n"
        potion_text += f"   💰 Ціна: {potion.price:,} золота\n"
        potion_text += f"   💚 Ефект: +{potion.effects['health']} HP\n"
        potion_text += f"   📈 Рівень: {potion.level_required}+\n"
        potion_text += f"   📊 Статус: {status}\n"
        potion_text += f"   📝 {potion.description}\n\n"
        
        if level_ok and can_afford:
            keyboard.append([InlineKeyboardButton(
                f"💰 Купити {potion.name} ({potion.price:,} 💰)",
                callback_data=f"buy_potion_{potion.id}"
            )])
    
    # Mana potions
    potion_text += "⚡ **Зілля мани:**\n"
    for potion_id, potion in mana_potions.items():
        can_afford = character.gold >= potion.price
        level_ok = potion.level_required <= character.level
        
        if level_ok and can_afford:
            status = "✅ Доступно"
        elif level_ok and not can_afford:
            status = "💰 Недостатньо золота"
        else:
            status = f"📈 Потрібен {potion.level_required} рівень"
        
        potion_text += f"🧪 **{potion.name}**\n"
        potion_text += f"   💰 Ціна: {potion.price:,} золота\n"
        potion_text += f"   ⚡ Ефект: +{potion.effects['mana']} MP\n"
        potion_text += f"   📈 Рівень: {potion.level_required}+\n"
        potion_text += f"   📊 Статус: {status}\n"
        potion_text += f"   📝 {potion.description}\n\n"
        
        if level_ok and can_afford:
            keyboard.append([InlineKeyboardButton(
                f"💰 Купити {potion.name} ({potion.price:,} 💰)",
                callback_data=f"buy_potion_{potion.id}"
            )])
    
    # Combat potions
    potion_text += "⚔️ **Бойові зілля:**\n"
    for potion_id, potion in combat_potions.items():
        can_afford = character.gold >= potion.price
        level_ok = potion.level_required <= character.level
        
        if level_ok and can_afford:
            status = "✅ Доступно"
        elif level_ok and not can_afford:
            status = "💰 Недостатньо золота"
        else:
            status = f"📈 Потрібен {potion.level_required} рівень"
        
        potion_text += f"🧪 **{potion.name}**\n"
        potion_text += f"   💰 Ціна: {potion.price:,} золота\n"
        
        # Show effects
        effects = []
        if 'temp_attack' in potion.effects:
            effects.append(f"⚔️ +{potion.effects['temp_attack']} атака")
        if 'temp_defense' in potion.effects:
            effects.append(f"🛡️ +{potion.effects['temp_defense']} захист")
        if 'temp_speed' in potion.effects:
            effects.append(f"⚡ +{potion.effects['temp_speed']} швидкість")
        if 'health_regen' in potion.effects:
            effects.append(f"💚 {potion.effects['health_regen']} HP/хід")
        
        potion_text += f"   🌟 Ефекти: {', '.join(effects)}\n"
        potion_text += f"   ⏱️ Тривалість: {potion.effects.get('duration', 1)} ходів\n"
        potion_text += f"   📈 Рівень: {potion.level_required}+\n"
        potion_text += f"   📊 Статус: {status}\n"
        potion_text += f"   📝 {potion.description}\n\n"
        
        if level_ok and can_afford:
            keyboard.append([InlineKeyboardButton(
                f"💰 Купити {potion.name} ({potion.price:,} 💰)",
                callback_data=f"buy_potion_{potion.id}"
            )])
    
    keyboard.extend([
        [InlineKeyboardButton("⚔️ Зброя", callback_data="merchant_weapons")],
        [InlineKeyboardButton("🛡️ Броня", callback_data="merchant_armor")],
        [InlineKeyboardButton("🔙 Назад до магазину", callback_data="merchant_main")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        potion_text, reply_markup=reply_markup, parse_mode='Markdown'
    )


async def show_potions_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show potions management menu"""
    
    user_id = update.effective_user.id
    character = await db.get_character(user_id)
    
    if not character:
        await update.callback_query.answer("❌ Персонаж не знайдено!")
        return
    
    from game_logic.potion_manager import potion_manager
    
    # Get player's potions from database
    conn = await db.get_connection()
    async with conn.execute('''
        SELECT item_id, quantity FROM player_equipment 
        WHERE user_id = ? AND item_type = 'consumable' AND quantity > 0
    ''', (user_id,)) as cursor:
        potion_rows = await cursor.fetchall()
    
    potions_text = f"""
🧪 **Управління зіллям**
━━━━━━━━━━━━━━━━━━━━━━━━━
👤 {character.name}
💰 Золото: {int(character.gold):,}

🧪 **Ваші зілля:**
"""
    
    keyboard = []
    has_potions = False
    
    for row in potion_rows:
        potion_id = row['item_id']
        quantity = row['quantity']
        
        potion = potion_manager.get_potion(potion_id)
        if potion and quantity > 0:
            has_potions = True
            potions_text += f"🧪 **{potion.name}** x{quantity}\n"
            potions_text += f"   📝 {potion.description}\n"
            
            # Show effects
            effects = []
            if 'health' in potion.effects:
                effects.append(f"💚+{potion.effects['health']} HP")
            if 'mana' in potion.effects:
                effects.append(f"⚡+{potion.effects['mana']} MP")
            if 'temp_attack' in potion.effects:
                effects.append(f"⚔️+{potion.effects['temp_attack']} атака")
            if 'temp_defense' in potion.effects:
                effects.append(f"🛡️+{potion.effects['temp_defense']} захист")
            if 'temp_speed' in potion.effects:
                effects.append(f"⚡+{potion.effects['temp_speed']} швидкість")
            if 'health_regen' in potion.effects:
                effects.append(f"💚{potion.effects['health_regen']} HP/хід")
            
            if effects:
                potions_text += f"   🌟 Ефекти: {' '.join(effects)}\n"
            
            potions_text += "\n"
            
            # Add use button
            keyboard.append([InlineKeyboardButton(
                f"🧪 Використати {potion.name}",
                callback_data=f"use_potion_{potion.id}"
            )])
    
    if not has_potions:
        potions_text += "\n🔍 У вас немає зілля\n"
        potions_text += "💡 Купіть зілля у торговця!"
    
    # Add timestamp for message uniqueness
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    potions_text += f"\n🕐 Оновлено: {timestamp}"
    
    keyboard.extend([
        [InlineKeyboardButton("🛒 Купити зілля", callback_data="merchant_potions")],
        [InlineKeyboardButton("📦 Назад до інвентаря", callback_data="inventory_main")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        potions_text, reply_markup=reply_markup, parse_mode='Markdown'
    )


async def buy_potion(update: Update, context: ContextTypes.DEFAULT_TYPE, potion_id: str) -> None:
    """Purchase a potion"""
    
    user_id = update.effective_user.id
    character = await db.get_character(user_id)
    
    if not character:
        await update.callback_query.answer("❌ Персонаж не знайдено!")
        return
    
    from game_logic.potion_manager import potion_manager
    
    potion = potion_manager.get_potion(potion_id)
    if not potion:
        await update.callback_query.answer("❌ Зілля не знайдено!")
        return
    
    # Check requirements
    if character.level < potion.level_required:
        await update.callback_query.answer(
            f"❌ Потрібен рівень {potion.level_required}!"
        )
        return
    
    if character.gold < potion.price:
        await update.callback_query.answer("❌ Недостатньо золота!")
        return
    
    # Purchase potion
    new_gold = character.gold - potion.price
    await db.update_character_by_id(user_id, {'gold': new_gold})
    
    # Add potion to inventory using InventoryManager
    inventory_manager = InventoryManager(db)
    success = await inventory_manager.add_potion_to_inventory(user_id, potion_id, 1)
    
    if not success:
        await update.callback_query.answer("❌ Помилка при додаванні зілля до інвентаря!")
        return
    
    await update.callback_query.answer(
        f"✅ Куплено {potion.name} за {potion.price:,} золота!"
    )
    
    # Show updated potion shop
    await show_potion_shop(update, context)


async def use_potion(update: Update, context: ContextTypes.DEFAULT_TYPE, potion_id: str) -> None:
    """Use a potion from inventory"""
    
    user_id = update.effective_user.id
    character = await db.get_character(user_id)
    
    if not character:
        await update.callback_query.answer("❌ Персонаж не знайдено!")
        return
    
    from game_logic.potion_manager import potion_manager
    
    potion = potion_manager.get_potion(potion_id)
    if not potion:
        await update.callback_query.answer("❌ Зілля не знайдено!")
        return
    
    # Check if player has this potion
    conn = await db.get_connection()
    async with conn.execute('''
        SELECT quantity FROM player_equipment 
        WHERE user_id = ? AND item_id = ? AND item_type = 'consumable'
    ''', (user_id, potion_id)) as cursor:
        row = await cursor.fetchone()
    
    has_potion = row and row['quantity'] > 0
    
    if not has_potion:
        await update.callback_query.answer("❌ У вас немає цього зілля!")
        return
    
    # Apply potion effects
    char_dict = character.to_dict() if hasattr(character, 'to_dict') else character
    effects_result = potion_manager.apply_potion_effects(char_dict, potion)
    
    # Update character
    if effects_result['updates']:
        await db.update_character_by_id(user_id, effects_result['updates'])
    
    # Store temporary effects in context
    if effects_result['temp_effects']:
        if 'temp_effects' not in context.user_data:
            context.user_data['temp_effects'] = {}
        context.user_data['temp_effects'].update(effects_result['temp_effects'])
    
    # Remove potion from inventory
    inventory_manager = InventoryManager(db)
    success = await inventory_manager.remove_potion_from_inventory(user_id, potion_id, 1)
    
    if not success:
        await update.callback_query.answer("❌ Помилка при видаленні зілля з інвентаря!")
        return
    
    # Update statistics
    await db.update_statistics_by_id(user_id, {'potions_used': 1})
    
    # Show effects message
    effects_text = "\n".join(effects_result['effects_text'])
    await update.callback_query.answer(
        f"🧪 Використано {potion.name}!\n{effects_text}",
        show_alert=True
    )
    
    # Show updated potions management
    await show_potions_management(update, context)


async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str) -> None:
    """Purchase an item"""
    
    user_id = update.effective_user.id
    character = await db.get_character(user_id)
    
    if not character:
        await update.callback_query.answer("❌ Персонаж не знайдено!")
        return
    
    equipment_manager = EquipmentManager(db)
    inventory_manager = InventoryManager(db)
    
    item = equipment_manager.get_equipment_by_id(item_id)
    if not item:
        await update.callback_query.answer("❌ Предмет не знайдено!")
        return
    
    # Check requirements
    if character.level < item.level_requirement:
        await update.callback_query.answer(
            f"❌ Потрібен рівень {item.level_requirement}!"
        )
        return
    
    if character.gold < item.base_price:
        await update.callback_query.answer("❌ Недостатньо золота!")
        return
    
    if not equipment_manager.check_equipment_compatibility(character.character_class, item_id):
        await update.callback_query.answer("❌ Цей предмет не підходить вашому класу!")
        return
    
    # Deduct gold and add item
    try:
        conn = await db.get_connection()
        
        # Update character gold
        await conn.execute('''
            UPDATE characters SET gold = gold - ? WHERE user_id = ?
        ''', (item.base_price, user_id))
        
        # Add item to inventory
        await inventory_manager.add_item_to_inventory(user_id, item_id)
        
        await conn.commit()
        
        purchase_text = f"""
✅ **Покупка успішна!**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви купили: **{item.name}**
💰 Заплачено: {item.base_price:,} золота
📦 Предмет додано до інвентаря

        💰 Залишилося золота: {int(character.gold - item.base_price):,}

Ви можете екіпірувати предмет через інвентар.
"""
        
        keyboard = [
            [InlineKeyboardButton("📦 Відкрити інвентар", callback_data="inventory_main")],
            [InlineKeyboardButton("🛒 Продовжити покупки", callback_data="merchant_main")],
            [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            purchase_text, reply_markup=reply_markup, parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error purchasing item: {e}")
        await update.callback_query.answer("❌ Помилка при покупці!")


async def show_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show character inventory and equipped items"""
    
    user_id = update.effective_user.id
    character = await db.get_character(user_id)
    
    if not character:
        await update.callback_query.answer("❌ Персонаж не знайдено!")
        return
    
    inventory_manager = InventoryManager(db)
    equipment_manager = EquipmentManager(db)
    
    # Get equipment and stats
    equipment = await inventory_manager.get_character_equipment(user_id)
    stats = await inventory_manager.calculate_character_stats(user_id)
    
    inventory_text = f"""
📦 **Інвентар {character.name}**
━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Золото: {int(character.gold):,}

👤 **Споряджено:**
"""
    
    # Show equipped weapon
    if equipment.equipped_weapon:
        weapon = equipment_manager.get_equipment_by_id(equipment.equipped_weapon)
        if weapon:
            upgrade_text = f" +{equipment.weapon_upgrade_level}" if equipment.weapon_upgrade_level > 0 else ""
            inventory_text += f"⚔️ Зброя: {weapon.name}{upgrade_text}\n"
            # Calculate stats with upgrade level from database
            current_attack = equipment_manager.calculate_upgrade_stats(weapon.base_stats.attack, equipment.weapon_upgrade_level)
            base_attack = weapon.base_stats.attack
            bonus_attack = current_attack - base_attack
            if bonus_attack > 0:
                inventory_text += f"   📊 Атака: {base_attack} + {bonus_attack}\n"
            else:
                inventory_text += f"   📊 Атака: {base_attack}\n"
    else:
        inventory_text += "⚔️ Зброя: Немає\n"
    
    # Show equipped armor
    if equipment.equipped_armor:
        armor = equipment_manager.get_equipment_by_id(equipment.equipped_armor)
        if armor:
            upgrade_text = f" +{equipment.armor_upgrade_level}" if equipment.armor_upgrade_level > 0 else ""
            inventory_text += f"🛡️ Броня: {armor.name}{upgrade_text}\n"
            # Calculate stats with upgrade level from database
            current_defense = equipment_manager.calculate_upgrade_stats(armor.base_stats.defense, equipment.armor_upgrade_level)
            base_defense = armor.base_stats.defense
            bonus_defense = current_defense - base_defense
            if bonus_defense > 0:
                inventory_text += f"   📊 Захист: {base_defense} + {bonus_defense}\n"
            else:
                inventory_text += f"   📊 Захист: {base_defense}\n"
    else:
        inventory_text += "🛡️ Броня: Немає\n"
    
    # Show total stats
    if stats:
        inventory_text += f"""
💪 **Загальні характеристики:**
🗡 Атака: {stats.total_attack} ({stats.base_attack} + {stats.weapon_attack})
🛡 Захист: {stats.total_defense} ({stats.base_defense} + {stats.armor_defense})
⚡ Швидкість: {stats.total_speed}
🎯 Критичний удар: {stats.total_crit_chance}%
🛡 Блокування: {stats.total_block_chance}%
"""
    
    # Show inventory items
    inventory_text += "\n📋 **Предмети в інвентарі:**\n"
    
    if equipment.weapons:
        inventory_text += "⚔️ **Зброя:**\n"
        for weapon_id, upgrade_level in equipment.weapons.items():
            weapon = equipment_manager.get_equipment_by_id(weapon_id)
            if weapon:
                upgrade_text = f" +{upgrade_level}" if upgrade_level > 0 else ""
                inventory_text += f"  • {weapon.name}{upgrade_text}\n"
    
    if equipment.armor:
        inventory_text += "🛡️ **Броня:**\n"
        for armor_id, upgrade_level in equipment.armor.items():
            armor = equipment_manager.get_equipment_by_id(armor_id)
            if armor:
                upgrade_text = f" +{upgrade_level}" if upgrade_level > 0 else ""
                inventory_text += f"  • {armor.name}{upgrade_text}\n"
    
    # Show materials
    if any(equipment.materials.values()):
        inventory_text += "\n🔧 **Матеріали для покращення:**\n"
        if equipment.materials["gods_stone"] > 0:
            inventory_text += f"💎 Каміння богів: {equipment.materials['gods_stone']}\n"
        if equipment.materials["mithril_dust"] > 0:
            inventory_text += f"✨ Мітрилова пил: {equipment.materials['mithril_dust']}\n"
        if equipment.materials["dragon_scale"] > 0:
            inventory_text += f"🐉 Драконяча луска: {equipment.materials['dragon_scale']}\n"
    
    if not equipment.weapons and not equipment.armor:
        inventory_text += "\n🔍 Інвентар порожній"
    
    # Add timestamp for message uniqueness
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    inventory_text += f"\n\n🕐 Оновлено: {timestamp}"
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Управління зброєю", callback_data="inventory_weapons")],
        [InlineKeyboardButton("🛡️ Управління бронею", callback_data="inventory_armor")],
        [InlineKeyboardButton("🧪 Управління зіллям", callback_data="inventory_potions")],
        [InlineKeyboardButton("⚒️ Кузня (покращення)", callback_data="blacksmith_main")],
        [InlineKeyboardButton("🛒 До торговця", callback_data="merchant_main")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            inventory_text, reply_markup=reply_markup, parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            inventory_text, reply_markup=reply_markup, parse_mode='Markdown'
        )


async def show_blacksmith(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show blacksmith upgrade menu"""
    
    user_id = update.effective_user.id
    character = await db.get_character(user_id)
    
    if not character:
        await update.callback_query.answer("❌ Персонаж не знайдено!")
        return
    
    inventory_manager = InventoryManager(db)
    equipment_manager = EquipmentManager(db)
    equipment = await inventory_manager.get_character_equipment(user_id)
    
    blacksmith_text = f"""
⚒️ **Кузня гнома Торіна**
━━━━━━━━━━━━━━━━━━━━━━━━━
💎 Каміння богів: {equipment.materials.get('gods_stone', 0)}
✨ Мітрилова пил: {equipment.materials.get('mithril_dust', 0)}
🐉 Драконяча луска: {equipment.materials.get('dragon_scale', 0)}
💰 Золото: {character.gold:,}

**Матеріали для покращення:**
Каміння богів: {equipment.materials.get('gods_stone', 0)}
Мітрилова пил: {equipment.materials.get('mithril_dust', 0)}
Драконяча луска: {equipment.materials.get('dragon_scale', 0)}

Оберіть предмет для покращення:
"""
    
    keyboard = []
    
    # Show equipped weapon
    if equipment.equipped_weapon:
        weapon = equipment_manager.get_equipment_by_id(equipment.equipped_weapon)
        if weapon and equipment.weapon_upgrade_level < 40:
            cost = equipment_manager.get_upgrade_cost(equipment.weapon_upgrade_level)
            
            blacksmith_text += f"\n🗡 **{weapon.name} +{equipment.weapon_upgrade_level}**\n"
            
            # Show current stats with upgrades
            current_attack = equipment_manager.calculate_upgrade_stats(weapon.base_stats.attack, equipment.weapon_upgrade_level)
            base_attack = weapon.base_stats.attack
            bonus_attack = current_attack - base_attack
            if bonus_attack > 0:
                blacksmith_text += f"   📊 Поточна атака: {base_attack} + {bonus_attack} = {current_attack}\n"
            else:
                blacksmith_text += f"   📊 Поточна атака: {base_attack}\n"
            
            # Show next level preview
            next_level = equipment.weapon_upgrade_level + 1
            next_attack = equipment_manager.calculate_upgrade_stats(base_attack, next_level)
            next_bonus = next_attack - base_attack
            blacksmith_text += f"   📈 Наступний рівень (+{next_level}): {base_attack} + {next_bonus} = {next_attack}\n"
            
            blacksmith_text += f"   💎 Потрібно: {cost.get('gods_stone', 0)} каміння богів (у вас: {equipment.materials.get('gods_stone', 0)})\n"
            blacksmith_text += f"   💰 Потрібно: {cost.get('gold', 0):,} золота (у вас: {character.gold:,})\n"
            blacksmith_text += f"   🎯 Шанс успіху: {cost.get('success_rate', 0)}%\n"
            
            can_upgrade = (equipment.materials.get('gods_stone', 0) >= cost.get('gods_stone', 0) and 
                          character.gold >= cost.get('gold', 0))
            
            if can_upgrade:
                keyboard.append([InlineKeyboardButton(
                    f"⚒️ Покращити зброю (+{equipment.weapon_upgrade_level + 1})",
                    callback_data=f"upgrade_weapon_{equipment.equipped_weapon}"
                )])
    
    # Show equipped armor
    if equipment.equipped_armor:
        armor = equipment_manager.get_equipment_by_id(equipment.equipped_armor)
        if armor and equipment.armor_upgrade_level < 40:
            cost = equipment_manager.get_upgrade_cost(equipment.armor_upgrade_level)
            
            blacksmith_text += f"\n🛡 **{armor.name} +{equipment.armor_upgrade_level}**\n"
            
            # Show current stats with upgrades
            current_defense = equipment_manager.calculate_upgrade_stats(armor.base_stats.defense, equipment.armor_upgrade_level)
            base_defense = armor.base_stats.defense
            bonus_defense = current_defense - base_defense
            if bonus_defense > 0:
                blacksmith_text += f"   📊 Поточний захист: {base_defense} + {bonus_defense} = {current_defense}\n"
            else:
                blacksmith_text += f"   📊 Поточний захист: {base_defense}\n"
            
            # Show next level preview
            next_level = equipment.armor_upgrade_level + 1
            next_defense = equipment_manager.calculate_upgrade_stats(base_defense, next_level)
            next_bonus = next_defense - base_defense
            blacksmith_text += f"   📈 Наступний рівень (+{next_level}): {base_defense} + {next_bonus} = {next_defense}\n"
            
            blacksmith_text += f"   💎 Потрібно: {cost.get('gods_stone', 0)} каміння богів (у вас: {equipment.materials.get('gods_stone', 0)})\n"
            blacksmith_text += f"   💰 Потрібно: {cost.get('gold', 0):,} золота (у вас: {character.gold:,})\n"
            blacksmith_text += f"   🎯 Шанс успіху: {cost.get('success_rate', 0)}%\n"
            
            can_upgrade = (equipment.materials.get('gods_stone', 0) >= cost.get('gods_stone', 0) and 
                          character.gold >= cost.get('gold', 0))
            
            if can_upgrade:
                keyboard.append([InlineKeyboardButton(
                    f"⚒️ Покращити броню (+{equipment.armor_upgrade_level + 1})",
                    callback_data=f"upgrade_armor_{equipment.equipped_armor}"
                )])
    
    if not keyboard:
        blacksmith_text += "\n🚫 Немає предметів для покращення або недостатньо матеріалів."
    
    # Add timestamp for message uniqueness
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    blacksmith_text += f"""

💡 **Як отримати матеріали:**
• 💎 Каміння богів: 15% шанс з усіх монстрів + до 3 за проходження підземелля
• ✨ Мітрилова пил: боси (25%), дракони (35%), рідкісні вороги (рівень 10+)
• 🐉 Драконяча луска: древні дракони (5% шанс)

🕐 Оновлено: {timestamp}
"""
    
    keyboard.extend([
        [InlineKeyboardButton("📦 Інвентар", callback_data="inventory_main")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        blacksmith_text, reply_markup=reply_markup, parse_mode='Markdown'
    )


async def equipment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle equipment-related callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "merchant_main":
        await show_merchant_menu(update, context)
    
    elif data == "merchant_weapons":
        await show_weapon_shop(update, context)
    
    elif data == "merchant_armor":
        await show_armor_shop(update, context)
    
    elif data == "merchant_potions":
        await show_potion_shop(update, context)
    
    elif data.startswith("buy_weapon_"):
        item_id = data.replace("buy_weapon_", "")
        await buy_item(update, context, item_id)
    
    elif data.startswith("buy_armor_"):
        item_id = data.replace("buy_armor_", "")
        await buy_item(update, context, item_id)
    
    elif data.startswith("buy_potion_"):
        potion_id = data.replace("buy_potion_", "")
        await buy_potion(update, context, potion_id)
    
    elif data.startswith("use_potion_"):
        potion_id = data.replace("use_potion_", "")
        await use_potion(update, context, potion_id)
    
    elif data == "inventory_main":
        await show_inventory(update, context)
    
    elif data == "inventory_weapons":
        await show_weapons_management(update, context)
    
    elif data == "inventory_armor":
        await show_armor_management(update, context)
    
    elif data == "inventory_potions":
        await show_potions_management(update, context)
    
    elif data.startswith("equip_weapon_"):
        item_id = data.replace("equip_weapon_", "")
        await equip_weapon(update, context, item_id)
    
    elif data.startswith("equip_armor_"):
        item_id = data.replace("equip_armor_", "")
        await equip_armor(update, context, item_id)
    
    elif data.startswith("unequip_weapon"):
        await unequip_weapon(update, context)
    
    elif data.startswith("unequip_armor"):
        await unequip_armor(update, context)
    
    elif data.startswith("sell_weapon_"):
        item_id = data.replace("sell_weapon_", "")
        await sell_weapon(update, context, item_id)
    
    elif data.startswith("sell_armor_"):
        item_id = data.replace("sell_armor_", "")
        await sell_armor(update, context, item_id)
    
    elif data == "blacksmith_main":
        await show_blacksmith(update, context)
    
    elif data == "tavern_blacksmith":
        await show_blacksmith(update, context)
    
    elif data.startswith("upgrade_weapon_"):
        item_id = data.replace("upgrade_weapon_", "")
        await upgrade_equipment(update, context, item_id, "weapon")
    
    elif data.startswith("upgrade_armor_"):
        item_id = data.replace("upgrade_armor_", "")
        await upgrade_equipment(update, context, item_id, "armor")
    
    else:
        await query.edit_message_text(f"🚧 Функція '{data}' в розробці!")


async def upgrade_equipment(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str, item_type: str) -> None:
    """Upgrade equipped item"""
    
    try:
        user_id = update.effective_user.id
        inventory_manager = InventoryManager(db)
        equipment_manager = EquipmentManager(db)
        
        # Add timeout protection
        import asyncio
        result = await asyncio.wait_for(
            inventory_manager.upgrade_item(user_id, item_id, item_type),
            timeout=10.0  # 10 second timeout
        )
        
        if result["success"]:
            item = equipment_manager.get_equipment_by_id(item_id)
            
            upgrade_text = f"""
✅ **ПОКРАЩЕННЯ УСПІШНЕ!**
━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 {item.name} покращено до рівня +{result["new_level"]}!

💎 Витрачено матеріалів:
• Каміння богів: {result["materials_used"]["gods_stone"]}
• Золото: {result["materials_used"]["gold"]:,}

✨ Ваш предмет став сильнішим!
"""
        else:
            reason_messages = {
                "character_not_found": "❌ Персонаж не знайдено!",
                "item_not_equipped": "❌ Предмет не екіпіровано!",
                "max_upgrade": "❌ Досягнуто максимальний рівень покращення (+40)!",
                "insufficient_gods_stone": "❌ Недостатньо каміння богів!",
                "insufficient_gold": "❌ Недостатньо золота!",
                "upgrade_failed": "💥 Покращення не вдалося!",
                "database_error": "❌ Помилка бази даних!"
            }
            
            upgrade_text = f"""
❌ **ПОКРАЩЕННЯ НЕ ВДАЛОСЯ**
━━━━━━━━━━━━━━━━━━━━━━━━━
{reason_messages.get(result["reason"], "❌ Невідома помилка")}
"""
            
            if result["reason"] == "upgrade_failed":
                upgrade_text += f"""
💔 На жаль, покращення провалилося...

💎 Витрачено матеріалів:
• Каміння богів: {result["materials_used"]["gods_stone"]}
• Золото: {result["materials_used"]["gold"]:,}

🍀 Спробуйте ще раз! Удача обов'язково усміхнеться!
"""
        
        keyboard = [
            [InlineKeyboardButton("⚒️ Спробувати ще раз", callback_data="blacksmith_main")],
            [InlineKeyboardButton("📦 Інвентар", callback_data="inventory_main")],
            [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            upgrade_text, reply_markup=reply_markup, parse_mode='Markdown'
        )
    
    except asyncio.TimeoutError:
        error_text = """
⏰ **ТАЙМАУТ ОПЕРАЦІЇ**
━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Операція покращення зайняла занадто багато часу.

🔄 Спробуйте ще раз або зверніться до адміністратора.
"""
        keyboard = [
            [InlineKeyboardButton("🔄 Спробувати ще раз", callback_data="blacksmith_main")],
            [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            error_text, reply_markup=reply_markup, parse_mode='Markdown'
        )
    
    except Exception as e:
        logger.error(f"Error upgrading equipment: {e}")
        error_text = f"""
❌ **ПОМИЛКА ПРИ ПОКРАЩЕННІ**
━━━━━━━━━━━━━━━━━━━━━━━━━
💥 Сталася непередбачена помилка: {str(e)}

🔄 Спробуйте ще раз або зверніться до адміністратора.
"""
        keyboard = [
            [InlineKeyboardButton("🔄 Спробувати ще раз", callback_data="blacksmith_main")],
            [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            error_text, reply_markup=reply_markup, parse_mode='Markdown'
        )


async def show_weapons_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show weapons management interface"""
    
    user_id = update.effective_user.id
    character = await db.get_character(user_id)
    
    if not character:
        await update.callback_query.answer("❌ Персонаж не знайдено!")
        return
    
    inventory_manager = InventoryManager(db)
    equipment_manager = EquipmentManager(db)
    equipment = await inventory_manager.get_character_equipment(user_id)
    
    weapons_text = f"""
⚔️ **Управління зброєю**
━━━━━━━━━━━━━━━━━━━━━━━━━
👤 Персонаж: {character.name}
💰 Золото: {int(character.gold):,}

"""
    
    keyboard = []
    
    # Show equipped weapon
    if equipment.equipped_weapon:
        weapon = equipment_manager.get_equipment_by_id(equipment.equipped_weapon)
        if weapon:
            upgrade_text = f" +{equipment.weapon_upgrade_level}" if equipment.weapon_upgrade_level > 0 else ""
            # Calculate stats with upgrade level from database
            current_attack = equipment_manager.calculate_upgrade_stats(weapon.base_stats.attack, equipment.weapon_upgrade_level)
            
            weapons_text += f"🗡️ **Споряджено:**\n"
            weapons_text += f"   **{weapon.name}{upgrade_text}**\n"
            base_attack = weapon.base_stats.attack
            bonus_attack = current_attack - base_attack
            if bonus_attack > 0:
                weapons_text += f"   📊 Атака: {base_attack} + {bonus_attack}\n"
            else:
                weapons_text += f"   📊 Атака: {base_attack}\n"
            weapons_text += f"   💰 Вартість продажу: {equipment_manager.calculate_sell_price(weapon.id, equipment.weapon_upgrade_level):,} золота\n\n"
            
            keyboard.append([InlineKeyboardButton("❌ Розекіпірувати зброю", callback_data="unequip_weapon")])
    else:
        weapons_text += "🗡️ **Споряджено:** Немає\n\n"
    
    # Show weapons in inventory
    if equipment.weapons:
        weapons_text += "📦 **Зброя в інвентарі:**\n"
        for weapon_id, upgrade_level in equipment.weapons.items():
            weapon = equipment_manager.get_equipment_by_id(weapon_id)
            if weapon:
                upgrade_text = f" +{upgrade_level}" if upgrade_level > 0 else ""
                sell_price = equipment_manager.calculate_sell_price(weapon_id, upgrade_level)
                
                weapons_text += f"   • **{weapon.name}{upgrade_text}**\n"
                # Calculate stats with upgrade level from database
                current_attack = equipment_manager.calculate_upgrade_stats(weapon.base_stats.attack, upgrade_level)
                base_attack = weapon.base_stats.attack
                bonus_attack = current_attack - base_attack
                if bonus_attack > 0:
                    weapons_text += f"     📊 Атака: {base_attack} + {bonus_attack}\n"
                else:
                    weapons_text += f"     📊 Атака: {base_attack}\n"
                weapons_text += f"     💰 Продажа: {sell_price:,} золота\n"
                
                # Add action buttons
                keyboard.append([
                    InlineKeyboardButton(f"✅ Екіпірувати {weapon.name}", callback_data=f"equip_weapon_{weapon_id}"),
                    InlineKeyboardButton(f"💰 Продати ({sell_price:,})", callback_data=f"sell_weapon_{weapon_id}")
                ])
        weapons_text += "\n"
    else:
        weapons_text += "📦 **Зброя в інвентарі:** Немає\n\n"
    
    # Add timestamp for message uniqueness
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    weapons_text += "💡 **Підказки:**\n"
    weapons_text += "• Екіпіруйте кращу зброю для підвищення атаки\n"
    weapons_text += "• Продавайте непотрібну зброю за золото\n"
    weapons_text += "• Покращуйте зброю в кузні для більшої сили\n"
    weapons_text += f"\n🕐 Оновлено: {timestamp}"
    
    keyboard.extend([
        [InlineKeyboardButton("🛡️ Управління бронею", callback_data="inventory_armor")],
        [InlineKeyboardButton("📦 Назад до інвентаря", callback_data="inventory_main")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        weapons_text, reply_markup=reply_markup, parse_mode='Markdown'
    )


async def show_armor_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show armor management interface"""
    
    user_id = update.effective_user.id
    character = await db.get_character(user_id)
    
    if not character:
        await update.callback_query.answer("❌ Персонаж не знайдено!")
        return
    
    inventory_manager = InventoryManager(db)
    equipment_manager = EquipmentManager(db)
    equipment = await inventory_manager.get_character_equipment(user_id)
    
    armor_text = f"""
🛡️ **Управління бронею**
━━━━━━━━━━━━━━━━━━━━━━━━━
👤 Персонаж: {character.name}
💰 Золото: {int(character.gold):,}

"""
    
    keyboard = []
    
    # Show equipped armor
    if equipment.equipped_armor:
        armor = equipment_manager.get_equipment_by_id(equipment.equipped_armor)
        if armor:
            upgrade_text = f" +{equipment.armor_upgrade_level}" if equipment.armor_upgrade_level > 0 else ""
            # Calculate stats with upgrade level from database
            current_defense = equipment_manager.calculate_upgrade_stats(armor.base_stats.defense, equipment.armor_upgrade_level)
            
            armor_text += f"🛡️ **Споряджено:**\n"
            armor_text += f"   **{armor.name}{upgrade_text}**\n"
            base_defense = armor.base_stats.defense
            bonus_defense = current_defense - base_defense
            if bonus_defense > 0:
                armor_text += f"   📊 Захист: {base_defense} + {bonus_defense}\n"
            else:
                armor_text += f"   📊 Захист: {base_defense}\n"
            armor_text += f"   💰 Вартість продажу: {equipment_manager.calculate_sell_price(armor.id, equipment.armor_upgrade_level):,} золота\n\n"
            
            keyboard.append([InlineKeyboardButton("❌ Розекіпірувати броню", callback_data="unequip_armor")])
    else:
        armor_text += "🛡️ **Споряджено:** Немає\n\n"
    
    # Show armor in inventory
    if equipment.armor:
        armor_text += "📦 **Броня в інвентарі:**\n"
        for armor_id, upgrade_level in equipment.armor.items():
            armor = equipment_manager.get_equipment_by_id(armor_id)
            if armor:
                upgrade_text = f" +{upgrade_level}" if upgrade_level > 0 else ""
                sell_price = equipment_manager.calculate_sell_price(armor_id, upgrade_level)
                
                armor_text += f"   • **{armor.name}{upgrade_text}**\n"
                # Calculate stats with upgrade level from database
                current_defense = equipment_manager.calculate_upgrade_stats(armor.base_stats.defense, upgrade_level)
                base_defense = armor.base_stats.defense
                bonus_defense = current_defense - base_defense
                if bonus_defense > 0:
                    armor_text += f"     📊 Захист: {base_defense} + {bonus_defense}\n"
                else:
                    armor_text += f"     📊 Захист: {base_defense}\n"
                armor_text += f"     💰 Продажа: {sell_price:,} золота\n"
                
                # Add action buttons
                keyboard.append([
                    InlineKeyboardButton(f"✅ Екіпірувати {armor.name}", callback_data=f"equip_armor_{armor_id}"),
                    InlineKeyboardButton(f"💰 Продати ({sell_price:,})", callback_data=f"sell_armor_{armor_id}")
                ])
        armor_text += "\n"
    else:
        armor_text += "📦 **Броня в інвентарі:** Немає\n\n"
    
    # Add timestamp for message uniqueness
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    armor_text += "💡 **Підказки:**\n"
    armor_text += "• Екіпіруйте кращу броню для підвищення захисту\n"
    armor_text += "• Продавайте непотрібну броню за золото\n"
    armor_text += "• Покращуйте броню в кузні для більшого захисту\n"
    armor_text += f"\n🕐 Оновлено: {timestamp}"
    
    keyboard.extend([
        [InlineKeyboardButton("⚔️ Управління зброєю", callback_data="inventory_weapons")],
        [InlineKeyboardButton("📦 Назад до інвентаря", callback_data="inventory_main")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        armor_text, reply_markup=reply_markup, parse_mode='Markdown'
    )


async def equip_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str) -> None:
    """Equip a weapon from inventory"""
    
    user_id = update.effective_user.id
    inventory_manager = InventoryManager(db)
    equipment_manager = EquipmentManager(db)
    
    # Get weapon details for better error messages
    weapon = equipment_manager.get_equipment_by_id(item_id)
    weapon_name = weapon.name if weapon else "предмет"
    
    result = await inventory_manager.equip_item(user_id, item_id)
    
    if result["success"]:
        await update.callback_query.answer(f"✅ {weapon_name} екіпіровано!", show_alert=True)
        await show_weapons_management(update, context)
    else:
        error_messages = {
            "item_not_found": f"❌ {weapon_name} не знайдено в базі даних!",
            "character_not_found": "❌ Персонаж не знайдено!",
            "class_incompatible": f"❌ {weapon_name} не підходить вашому класу персонажа!",
            "level_requirement": f"❌ {weapon_name} потребує вищий рівень!",
            "item_not_in_inventory": f"❌ {weapon_name} не знайдено в інвентарі!",
            "database_error": "❌ Помилка бази даних!"
        }
        
        error_msg = error_messages.get(result["reason"], f"❌ Невідома помилка з {weapon_name}!")
        await update.callback_query.answer(error_msg, show_alert=True)
        logger.warning(f"Equip weapon failed for user {user_id}, item {item_id}: {result}")


async def equip_armor(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str) -> None:
    """Equip armor from inventory"""
    
    user_id = update.effective_user.id
    inventory_manager = InventoryManager(db)
    equipment_manager = EquipmentManager(db)
    
    # Get armor details for better error messages
    armor = equipment_manager.get_equipment_by_id(item_id)
    armor_name = armor.name if armor else "предмет"
    
    result = await inventory_manager.equip_item(user_id, item_id)
    
    if result["success"]:
        await update.callback_query.answer(f"✅ {armor_name} екіпіровано!", show_alert=True)
        await show_armor_management(update, context)
    else:
        error_messages = {
            "item_not_found": f"❌ {armor_name} не знайдено в базі даних!",
            "character_not_found": "❌ Персонаж не знайдено!",
            "class_incompatible": f"❌ {armor_name} не підходить вашому класу персонажа!",
            "level_requirement": f"❌ {armor_name} потребує вищий рівень!",
            "item_not_in_inventory": f"❌ {armor_name} не знайдено в інвентарі!",
            "database_error": "❌ Помилка бази даних!"
        }
        
        error_msg = error_messages.get(result["reason"], f"❌ Невідома помилка з {armor_name}!")
        await update.callback_query.answer(error_msg, show_alert=True)
        logger.warning(f"Equip armor failed for user {user_id}, item {item_id}: {result}")


async def unequip_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unequip current weapon"""
    
    user_id = update.effective_user.id
    inventory_manager = InventoryManager(db)
    
    # Get current equipment
    equipment = await inventory_manager.get_character_equipment(user_id)
    
    if not equipment.equipped_weapon:
        await update.callback_query.answer("❌ Немає зброї для розекіпірування!")
        return
    
    try:
        # Add current weapon to inventory
        await inventory_manager.add_item_to_inventory(user_id, equipment.equipped_weapon, equipment.weapon_upgrade_level)
        
        # Remove weapon from character (update both old and new fields for compatibility)
        conn = await db.get_connection()
        await conn.execute('''
            UPDATE characters 
            SET weapon = NULL, weapon_upgrade_level = 0,
                equipped_weapon = NULL
            WHERE user_id = ?
        ''', (user_id,))
        await conn.commit()
        
        await update.callback_query.answer("✅ Зброю розекіпіровано!", show_alert=True)
        await show_weapons_management(update, context)
        
    except Exception as e:
        logger.error(f"Error unequipping weapon: {e}")
        await update.callback_query.answer("❌ Помилка при розекіпіровці!")


async def unequip_armor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unequip current armor"""
    
    user_id = update.effective_user.id
    inventory_manager = InventoryManager(db)
    
    # Get current equipment
    equipment = await inventory_manager.get_character_equipment(user_id)
    
    if not equipment.equipped_armor:
        await update.callback_query.answer("❌ Немає броні для розекіпірування!")
        return
    
    try:
        # Add current armor to inventory
        await inventory_manager.add_item_to_inventory(user_id, equipment.equipped_armor, equipment.armor_upgrade_level)
        
        # Remove armor from character (update both old and new fields for compatibility)
        conn = await db.get_connection()
        await conn.execute('''
            UPDATE characters 
            SET armor = NULL, armor_upgrade_level = 0,
                equipped_armor = NULL
            WHERE user_id = ?
        ''', (user_id,))
        await conn.commit()
        
        await update.callback_query.answer("✅ Броню розекіпіровано!", show_alert=True)
        await show_armor_management(update, context)
        
    except Exception as e:
        logger.error(f"Error unequipping armor: {e}")
        await update.callback_query.answer("❌ Помилка при розекіпіровці!")


async def sell_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str) -> None:
    """Sell a weapon from inventory"""
    
    user_id = update.effective_user.id
    inventory_manager = InventoryManager(db)
    
    result = await inventory_manager.sell_item(user_id, item_id)
    
    if result["success"]:
        gold_earned = result["gold_earned"]
        await update.callback_query.answer(f"✅ Продано за {gold_earned:,} золота!", show_alert=True)
        await show_weapons_management(update, context)
    else:
        error_messages = {
            "item_not_found": "❌ Предмет не знайдено в інвентарі!",
            "database_error": "❌ Помилка бази даних!"
        }
        
        error_msg = error_messages.get(result["reason"], "❌ Невідома помилка!")
        await update.callback_query.answer(error_msg)


async def sell_armor(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str) -> None:
    """Sell armor from inventory"""
    
    user_id = update.effective_user.id
    inventory_manager = InventoryManager(db)
    
    result = await inventory_manager.sell_item(user_id, item_id)
    
    if result["success"]:
        gold_earned = result["gold_earned"]
        await update.callback_query.answer(f"✅ Продано за {gold_earned:,} золота!", show_alert=True)
        await show_armor_management(update, context)
    else:
        error_messages = {
            "item_not_found": "❌ Предмет не знайдено в інвентарі!",
            "database_error": "❌ Помилка бази даних!"
        }
        
        error_msg = error_messages.get(result["reason"], "❌ Невідома помилка!")
        await update.callback_query.answer(error_msg)
