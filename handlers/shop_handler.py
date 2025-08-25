"""
Shop handler - manages shop and trading
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from database.db_manager import DatabaseManager
import config

logger = logging.getLogger(__name__)
db = DatabaseManager(config.DATABASE_URL)


# Shop items data (simplified version)
SHOP_ITEMS = {
    'weapons': {
        'iron_sword': {'name': 'Залізний меч', 'price': 100, 'attack': 15, 'level_req': 1},
        'steel_sword': {'name': 'Сталевий меч', 'price': 250, 'attack': 22, 'level_req': 3},
        'magic_staff': {'name': 'Магічний посох', 'price': 200, 'attack': 12, 'magic_power': 20, 'level_req': 1},
        'elven_bow': {'name': 'Ельфійський лук', 'price': 300, 'attack': 18, 'critical_chance': 5, 'level_req': 3}
    },
    'armor': {
        'leather_armor': {'name': 'Шкіряна броня', 'price': 60, 'defense': 6, 'level_req': 1},
        'chainmail': {'name': 'Кольчуга', 'price': 150, 'defense': 12, 'level_req': 3},
        'plate_armor': {'name': 'Латна броня', 'price': 300, 'defense': 20, 'level_req': 5},
        'mage_robe': {'name': 'Мантія мага', 'price': 180, 'defense': 8, 'mana': 40, 'level_req': 1}
    },
    'potions': {
        'health_potion_small': {'name': 'Мале зілля здоров\'я', 'price': 20, 'health': 40, 'consumable': True},
        'health_potion': {'name': 'Зілля здоров\'я', 'price': 50, 'health': 80, 'consumable': True},
        'health_potion_large': {'name': 'Велике зілля здоров\'я', 'price': 100, 'health': 150, 'consumable': True},
        'mana_potion': {'name': 'Зілля мани', 'price': 40, 'mana': 60, 'consumable': True}
    }
}


async def show_shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, character: dict) -> None:
    """Show shop menu"""
    
    shop_text = f"""
🛒 **Торговець Торін Кам'янобород**
━━━━━━━━━━━━━━━━━━━━━━━━━
"Ласкаво просимо до мого магазину, воїне!"

💰 Ваше золото: {character['gold']}

Що вас цікавить?
"""
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Зброя", callback_data="shop_category_weapons")],
        [InlineKeyboardButton("🛡 Броня", callback_data="shop_category_armor")],
        [InlineKeyboardButton("🧪 Зілля", callback_data="shop_category_potions")],
        [InlineKeyboardButton("💰 Продати предмети", callback_data="shop_sell")],
        [InlineKeyboardButton("🏛 Повернутися до таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        shop_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle shop callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Get character
    character = await db.get_character(user_id)
    if not character:
        await query.edit_message_text("❌ Персонаж не знайдений!")
        return
    
    if data == "shop_main":
        await show_shop_menu(update, context, character)
    
    elif data.startswith("shop_category_"):
        category = data.replace("shop_category_", "")
        await show_shop_category(update, context, character, category)
    
    elif data.startswith("shop_buy_"):
        item_data = data.replace("shop_buy_", "")
        category, item_id = item_data.split("_", 1)
        await buy_item(update, context, character, category, item_id)
    
    elif data == "shop_sell":
        await show_sell_menu(update, context, character)


async def show_shop_category(update: Update, context: ContextTypes.DEFAULT_TYPE, character: dict, category: str) -> None:
    """Show items in category"""
    
    category_names = {
        'weapons': '⚔️ Зброя',
        'armor': '🛡 Броня',
        'potions': '🧪 Зілля'
    }
    
    if category not in SHOP_ITEMS:
        return
    
    category_text = f"""
🛒 **{category_names[category]}**
━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Ваше золото: {character['gold']}

Доступні товари:
"""
    
    keyboard = []
    items = SHOP_ITEMS[category]
    
    for item_id, item_data in items.items():
        # Check level requirement
        level_req = item_data.get('level_req', 1)
        can_use = character['level'] >= level_req
        can_afford = character['gold'] >= item_data['price']
        
        # Build item description
        item_desc = f"{item_data['name']} - {item_data['price']}💰"
        
        if 'attack' in item_data:
            item_desc += f" (Атака +{item_data['attack']})"
        if 'defense' in item_data:
            item_desc += f" (Захист +{item_data['defense']})"
        if 'health' in item_data:
            item_desc += f" (Здоров'я +{item_data['health']})"
        if 'mana' in item_data:
            item_desc += f" (Мана +{item_data['mana']})"
        
        if not can_use:
            item_desc = f"🔒 {item_desc} (Рівень {level_req})"
        elif not can_afford:
            item_desc = f"❌ {item_desc}"
        else:
            item_desc = f"✅ {item_desc}"
        
        if can_use and can_afford:
            keyboard.append([InlineKeyboardButton(
                item_desc,
                callback_data=f"shop_buy_{category}_{item_id}"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                item_desc,
                callback_data="shop_locked"
            )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад до магазину", callback_data="shop_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        category_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE, character: dict, category: str, item_id: str) -> None:
    """Buy an item"""
    
    if category not in SHOP_ITEMS or item_id not in SHOP_ITEMS[category]:
        await update.callback_query.answer("❌ Предмет не знайдений!")
        return
    
    item = SHOP_ITEMS[category][item_id]
    
    # Check gold
    if character['gold'] < item['price']:
        await update.callback_query.answer("❌ Недостатньо золота!", show_alert=True)
        return
    
    # Check level requirement
    level_req = item.get('level_req', 1)
    if character['level'] < level_req:
        await update.callback_query.answer(f"❌ Потрібен рівень {level_req}!", show_alert=True)
        return
    
    # Process purchase
    character['gold'] -= item['price']
    
    # Apply item effects
    updates = {'gold': character['gold']}
    
    if item.get('consumable'):
        # Add to inventory for consumables
        await db.add_to_inventory(character['user_id'], item_id, 1)
        purchase_type = "додано в інвентар"
    else:
        # Equip weapon/armor
        if category == 'weapons':
            old_weapon = character['weapon']
            character['weapon'] = item_id
            updates['weapon'] = item_id
            
            # Apply stat bonuses
            if 'attack' in item:
                character['attack'] += item['attack']
                updates['attack'] = character['attack']
            if 'magic_power' in item:
                character['magic_power'] += item['magic_power']
                updates['magic_power'] = character['magic_power']
            if 'critical_chance' in item:
                character['critical_chance'] += item['critical_chance']
                updates['critical_chance'] = character['critical_chance']
            
            purchase_type = "екіпіровано"
            
        elif category == 'armor':
            old_armor = character['armor']
            character['armor'] = item_id
            updates['armor'] = item_id
            
            # Apply stat bonuses
            if 'defense' in item:
                character['defense'] += item['defense']
                updates['defense'] = character['defense']
            if 'mana' in item:
                character['max_mana'] += item['mana']
                character['mana'] = character['max_mana']
                updates['max_mana'] = character['max_mana']
                updates['mana'] = character['mana']
            
            purchase_type = "екіпіровано"
    
    # Update character
    await db.update_character(character['user_id'], updates)
    
    # Update statistics
    await db.update_statistics(character['user_id'], {'gold_spent': item['price']})
    
    purchase_text = f"""
✅ **Покупка успішна!**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви купили: **{item['name']}**
Заплачено: {item['price']} золота
Статус: {purchase_type}

💰 Залишилося золота: {character['gold']}
"""
    
    keyboard = [
        [InlineKeyboardButton("🛒 Продовжити покупки", callback_data=f"shop_category_{category}")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        purchase_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_sell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, character: dict) -> None:
    """Show sell menu"""
    
    inventory = await db.get_inventory(character['user_id'])
    
    sell_text = f"""
💰 **Продаж предметів**
━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Ваше золото: {character['gold']}

Що бажаєте продати?
"""
    
    keyboard = []
    
    if inventory:
        for item_data in inventory:
            item_id = item_data['item_id']
            quantity = item_data['quantity']
            
            # Find item in shop data
            item_info = None
            for category in SHOP_ITEMS.values():
                if item_id in category:
                    item_info = category[item_id]
                    break
            
            if item_info:
                sell_price = item_info['price'] // 2  # Sell for half price
                button_text = f"{item_info['name']} x{quantity} - {sell_price}💰"
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"shop_sell_item_{item_id}"
                )])
    else:
        sell_text += "\n🔍 У вас немає предметів для продажу"
    
    keyboard.append([InlineKeyboardButton("🔙 Назад до магазину", callback_data="shop_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        sell_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )