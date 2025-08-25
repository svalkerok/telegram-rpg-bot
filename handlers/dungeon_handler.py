"""
Dungeon handler - manages dungeon exploration
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import random
import datetime

from database.db_manager import DatabaseManager
import config

logger = logging.getLogger(__name__)
db = DatabaseManager(config.DATABASE_URL)


def roll_dungeon_gods_stone_drops() -> int:
    """Roll for gods stone drops from dungeon completion"""
    total_drops = 0
    
    # 1 stone with 80% chance
    if random.randint(1, 100) <= 80:
        total_drops += 1
    
    # 2 stones with 50% chance
    if random.randint(1, 100) <= 50:
        total_drops += 1
    
    # 3 stones with 15% chance
    if random.randint(1, 100) <= 15:
        total_drops += 1
    
    return total_drops


async def show_dungeons_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show available dungeons"""
    
    # Convert Character object to dict if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
    else:
        char_dict = character
    
    dungeons_text = f"""
🗡 **Підземелля Валгаллії**
━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Ваше золото: {char_dict['gold']}

Оберіть підземелля для дослідження:
"""
    
    keyboard = []
    
    # Crypt - Level 1-3
    if char_dict['level'] >= config.DUNGEON_MIN_LEVELS['crypt']:
        button_text = f"💀 Склеп Новачка (Рівень 1-3) - {config.DUNGEON_ENTRY_COSTS['crypt']} золота"
        if char_dict['gold'] >= config.DUNGEON_ENTRY_COSTS['crypt']:
            keyboard.append([InlineKeyboardButton(button_text, callback_data="dungeon_enter_crypt")])
        else:
            keyboard.append([InlineKeyboardButton(f"❌ {button_text}", callback_data="dungeon_locked")])
    else:
        button_text = f"🔒 Склеп Новачка (Рівень 1+) - Потрібен рівень {config.DUNGEON_MIN_LEVELS['crypt']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data="dungeon_locked")])
    
    # Orc Cave - Level 3-6
    if char_dict['level'] >= config.DUNGEON_MIN_LEVELS['orcs']:
        button_text = f"⚔️ Печера Орків (Рівень 3-6) - {config.DUNGEON_ENTRY_COSTS['orcs']} золота"
        if char_dict['gold'] >= config.DUNGEON_ENTRY_COSTS['orcs']:
            keyboard.append([InlineKeyboardButton(button_text, callback_data="dungeon_enter_orcs")])
        else:
            keyboard.append([InlineKeyboardButton(f"❌ {button_text}", callback_data="dungeon_locked")])
    else:
        button_text = f"🔒 Печера Орків (Рівень 3+) - Потрібен рівень {config.DUNGEON_MIN_LEVELS['orcs']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data="dungeon_locked")])
    
    # Wizard Tower - Level 6-9
    if char_dict['level'] >= config.DUNGEON_MIN_LEVELS['tower']:
        button_text = f"🔮 Вежа Чародія (Рівень 6-9) - {config.DUNGEON_ENTRY_COSTS['tower']} золота"
        if char_dict['gold'] >= config.DUNGEON_ENTRY_COSTS['tower']:
            keyboard.append([InlineKeyboardButton(button_text, callback_data="dungeon_enter_tower")])
        else:
            keyboard.append([InlineKeyboardButton(f"❌ {button_text}", callback_data="dungeon_locked")])
    else:
        button_text = f"🔒 Вежа Чародія (Рівень 6+) - Потрібен рівень {config.DUNGEON_MIN_LEVELS['tower']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data="dungeon_locked")])
    
    # Dragon Lair - Level 9+
    if char_dict['level'] >= config.DUNGEON_MIN_LEVELS['dragon']:
        button_text = f"🐉 Логово Дракона (Рівень 9+) - {config.DUNGEON_ENTRY_COSTS['dragon']} золота"
        if char_dict['gold'] >= config.DUNGEON_ENTRY_COSTS['dragon']:
            keyboard.append([InlineKeyboardButton(button_text, callback_data="dungeon_enter_dragon")])
        else:
            keyboard.append([InlineKeyboardButton(f"❌ {button_text}", callback_data="dungeon_locked")])
    else:
        button_text = f"🔒 Логово Дракона (Рівень 9+) - Потрібен рівень {config.DUNGEON_MIN_LEVELS['dragon']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data="dungeon_locked")])
    
    keyboard.append([InlineKeyboardButton("🏛 Повернутися до таверни", callback_data="tavern_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        dungeons_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def dungeon_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle dungeon callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Get character
    character = await db.get_character(user_id)
    if not character:
        await query.edit_message_text("❌ Персонаж не знайдений!")
        return
    
    if data == "dungeon_locked":
        await query.answer("❌ Недостатньо золота або рівня!", show_alert=True)
        return
    
    elif data.startswith("dungeon_enter_"):
        dungeon_type = data.replace("dungeon_enter_", "")
        await enter_dungeon(update, context, character, dungeon_type)
    
    elif data.startswith("dungeon_room_"):
        action = data.replace("dungeon_room_", "")
        await process_dungeon_room(update, context, character, action)
    
    elif data.startswith("dungeon_combat_"):
        action = data.replace("dungeon_combat_", "")
        await process_dungeon_combat(update, context, character, action)
    
    elif data.startswith("dungeon_use_potion_"):
        potion_id = data.replace("dungeon_use_potion_", "")
        await use_dungeon_potion(update, context, character, potion_id)


async def enter_dungeon(update: Update, context: ContextTypes.DEFAULT_TYPE, character, dungeon_type: str) -> None:
    """Enter a dungeon"""
    
    # Convert Character object to dict if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
    else:
        char_dict = character
    
    # Check gold
    cost = config.DUNGEON_ENTRY_COSTS[dungeon_type]
    if char_dict['gold'] < cost:
        await update.callback_query.answer("❌ Недостатньо золота!", show_alert=True)
        return
    
    # Pay entry cost
    char_dict['gold'] -= cost
    await db.update_character_by_id(char_dict['user_id'], {'gold': char_dict['gold']})
    
    # Initialize dungeon in context
    context.user_data['current_dungeon'] = dungeon_type
    context.user_data['dungeon_room'] = 1
    context.user_data['dungeon_enemies_defeated'] = 0
    
    # Show first room
    await show_dungeon_room(update, context, character, dungeon_type, 1)


async def show_dungeon_room(update: Update, context: ContextTypes.DEFAULT_TYPE, character, dungeon_type: str, room: int) -> None:
    """Show dungeon room"""
    
    # Convert Character object to dict if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
    else:
        char_dict = character
    
    dungeon_names = {
        'crypt': 'Склеп Новачка',
        'orcs': 'Печера Орків',
        'tower': 'Вежа Чародія',
        'dragon': 'Логово Дракона'
    }
    
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    # Get max rooms for this dungeon
    max_rooms = config.DUNGEON_MAX_ROOMS.get(dungeon_type, 5)
    progress = f"{room}/{max_rooms}"
    
    room_text = f"""
🗡 **{dungeon_names[dungeon_type]}** - Кімната {progress}
━━━━━━━━━━━━━━━━━━━━━━━━━
💚 Здоров'я: {char_dict['health']}/{char_dict['max_health']}

Ви входите в темну кімнату...
Що будете робити?

🕐 Оновлено: {timestamp}
"""
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Дослідити кімнату", callback_data="dungeon_room_explore")],
        [InlineKeyboardButton("🏃‍♂️ Втекти з підземелля", callback_data="dungeon_room_flee")]
    ]
    
    if char_dict['health'] < char_dict['max_health'] / 2:
        keyboard.insert(1, [InlineKeyboardButton("🧪 Випити зілля здоров'я", callback_data="dungeon_room_potion")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        room_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def process_dungeon_room(update: Update, context: ContextTypes.DEFAULT_TYPE, character, action: str) -> None:
    """Process dungeon room action"""
    
    # Convert Character object to dict if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
    else:
        char_dict = character
    
    if action == "explore":
        # Random encounter
        encounter = random.choice(['enemy', 'enemy', 'treasure', 'trap', 'empty'])
        
        if encounter == 'enemy':
            await start_dungeon_combat(update, context, character)
        elif encounter == 'treasure':
            await find_treasure(update, context, character)
        elif encounter == 'trap':
            await trigger_trap(update, context, character)
        else:
            await find_empty_room(update, context, character)
    
    elif action == "flee":
        # Exit dungeon
        context.user_data.clear()
        text = "🏃‍♂️ Ви втекли з підземелля!"
        keyboard = [[InlineKeyboardButton("🏛 Повернутися до таверни", callback_data="tavern_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    elif action == "potion":
        # Use health potion (simplified)
        heal_amount = 50
        char_dict['health'] = min(char_dict['max_health'], char_dict['health'] + heal_amount)
        await db.update_character_by_id(char_dict['user_id'], {'health': char_dict['health']})
        
        await update.callback_query.answer(f"💚 Відновлено {heal_amount} здоров'я!")
        
        # Continue room
        dungeon_type = context.user_data.get('current_dungeon')
        room = context.user_data.get('dungeon_room', 1)
        await show_dungeon_room(update, context, character, dungeon_type, room)
    
    elif action == "continue":
        # Continue to next room
        dungeon_type = context.user_data.get('current_dungeon')
        current_room = context.user_data.get('dungeon_room', 1)
        next_room = current_room + 1
        
        # Check if dungeon is completed
        max_rooms = config.DUNGEON_MAX_ROOMS.get(dungeon_type, 5)
        if next_room > max_rooms:
            # Dungeon completed!
            completion_bonus = max_rooms * 10  # Bonus gold for completing dungeon
            char_dict['gold'] += completion_bonus
            
            await db.update_character_by_id(char_dict['user_id'], {
                'gold': char_dict['gold']
            })
            
            # Roll for potion drop (10% chance)
            from game_logic.potion_manager import potion_manager
            potion_drop = potion_manager.roll_dungeon_potion_drop()
            
            potion_text = ""
            if potion_drop:
                potion = potion_manager.get_potion(potion_drop)
                from game_logic.inventory_manager import InventoryManager
                inventory_manager = InventoryManager(db)
                success = await inventory_manager.add_potion_to_inventory(char_dict['user_id'], potion_drop, 1)
                
                if success and potion:
                    potion_text = f"\n🧪 **Знайдено зілля:** {potion.name}!"
            
            # Roll for gods stone drops from dungeon completion
            gods_stone_drops = roll_dungeon_gods_stone_drops()
            gods_stone_text = ""
            if gods_stone_drops > 0:
                from game_logic.inventory_manager import InventoryManager
                inventory_manager = InventoryManager(db)
                await inventory_manager.add_materials(char_dict['user_id'], {"gods_stone": gods_stone_drops})
                gods_stone_text = f"\n💎 **Знайдено каміння богів:** +{gods_stone_drops}!"
            
            # Update statistics
            await db.update_statistics_by_id(char_dict['user_id'], {
                'dungeons_completed': 1
            })
            
            completion_text = f"""
🏆 **ПІДЗЕМЕЛЛЯ ЗАВЕРШЕНО!**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви успішно пройшли {config.DUNGEON_MIN_LEVELS.get(dungeon_type, 'підземелля')}!

Нагороди за завершення:
💰 +{completion_bonus} золота (бонус за завершення){potion_text}{gods_stone_text}

👤 {char_dict['name']}: {char_dict['health']}/{char_dict['max_health']} HP
💰 Золото: {char_dict['gold']}
"""
            
            keyboard = [[InlineKeyboardButton("🏛 Повернутися до таверни", callback_data="tavern_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                completion_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        # Update room number
        context.user_data['dungeon_room'] = next_room
        
        # Show next room
        await show_dungeon_room(update, context, character, dungeon_type, next_room)


async def start_dungeon_combat(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Start combat in dungeon"""
    
    # Convert Character object to dict if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
    else:
        char_dict = character
    
    # Get dungeon type and room number
    dungeon_type = context.user_data.get('current_dungeon')
    room = context.user_data.get('dungeon_room', 1)
    
    # Get enemy template for this dungeon
    enemy_template = config.DUNGEON_ENEMIES.get(dungeon_type, config.DUNGEON_ENEMIES['crypt'])
    
    # Calculate player power for scaling
    from game_logic.balance_system import BalanceSystem
    balance_system = BalanceSystem()
    player_power = balance_system.calculate_player_power({
        'level': char_dict['level'],
        'attack': char_dict['attack'],
        'defense': char_dict['defense'],
        'max_health': char_dict['max_health'],
        'speed': char_dict.get('speed', 10),
        'critical_chance': char_dict.get('critical_chance', 5)
    })
    
    # Scale enemy based on room number and player level
    difficulty = 'normal'
    if room > config.DUNGEON_MAX_ROOMS[dungeon_type] * 0.7:
        difficulty = 'hard'
    elif room > config.DUNGEON_MAX_ROOMS[dungeon_type] * 0.4:
        difficulty = 'normal'
    else:
        difficulty = 'easy'
    
    # Scale enemy using balance system
    scaled_enemy = balance_system.scale_enemy_stats(
        enemy_template, char_dict['level'], player_power, difficulty
    )
    
    context.user_data['current_enemy'] = scaled_enemy
    
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    combat_text = f"""
⚔️ **БІЙ!**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви зустріли: **{scaled_enemy['name']}**

👤 {char_dict['name']}: {char_dict['health']}/{char_dict['max_health']} HP
👹 {scaled_enemy['name']}: {scaled_enemy['health']} HP

Що будете робити?

🕐 Оновлено: {timestamp}
"""
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Атакувати", callback_data="dungeon_combat_attack")],
        [InlineKeyboardButton("🛡 Захищатися", callback_data="dungeon_combat_defend")],
        [InlineKeyboardButton("🧪 Використати зілля", callback_data="dungeon_combat_potion")],
        [InlineKeyboardButton("🏃‍♂️ Втекти", callback_data="dungeon_combat_flee")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        combat_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def process_dungeon_combat(update: Update, context: ContextTypes.DEFAULT_TYPE, character, action: str) -> None:
    """Process combat action"""
    
    # Convert Character object to dict if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
    else:
        char_dict = character
    
    enemy = context.user_data.get('current_enemy')
    if not enemy:
        return
    
    if action == "attack":
        # Player attacks with improved damage formula (from forest system)
        base_damage = max(char_dict['attack'] * 0.8, char_dict['attack'] - enemy['defense'] * 0.7)
        min_damage = max(1, char_dict['attack'] * 0.15)
        variance = random.uniform(0.9, 1.1)
        damage = int(max(min_damage, base_damage * variance))
        enemy['health'] -= damage
        
        combat_log = f"⚔️ Ви завдали {damage} урону!\n"
        
        if enemy['health'] <= 0:
            # Victory
            char_dict['experience'] += enemy['exp_reward']
            char_dict['gold'] += enemy['gold_reward']
            
            await db.update_character_by_id(char_dict['user_id'], {
                'experience': char_dict['experience'],
                'gold': char_dict['gold']
            })
            
            # Roll for material drops
            from game_logic.equipment import EquipmentManager
            from game_logic.inventory_manager import InventoryManager
            equipment_manager = EquipmentManager(db)
            inventory_manager = InventoryManager(db)
            
            # Determine enemy type for material drops
            enemy_type = "normal"
            enemy_name_lower = enemy['name'].lower()
            
            # Check for boss/dragon keywords
            if any(keyword in enemy_name_lower for keyword in ["бос", "дракон", "лицар", "ліч", "володар", "чемпіон", "воїн", "смерті"]):
                enemy_type = "boss"
            elif any(keyword in enemy_name_lower for keyword in ["древній", "легендарний", "міфічний", "божественний"]):
                enemy_type = "dragon"
            
            material_drops = equipment_manager.roll_material_drop(enemy_type, enemy.get('level', 1))
            
            # Add materials to player
            material_text = ""
            if any(material_drops.values()):
                await inventory_manager.add_materials(char_dict['user_id'], material_drops)
                
                # Create material drop text
                material_text = "\n\n💎 **Знайдено матеріали:**\n"
                if material_drops.get("gods_stone", 0) > 0:
                    material_text += f"💎 Каміння богів: +{material_drops['gods_stone']}\n"
                if material_drops.get("mithril_dust", 0) > 0:
                    material_text += f"✨ Мітрилова пил: +{material_drops['mithril_dust']}\n"
                if material_drops.get("dragon_scale", 0) > 0:
                    material_text += f"🐉 Драконяча луска: +{material_drops['dragon_scale']}\n"
            
            # Update statistics
            await db.update_statistics_by_id(char_dict['user_id'], {
                'enemies_killed': 1,
                'gold_earned': enemy['gold_reward']
            })
            
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            victory_text = f"""
🎉 **ПЕРЕМОГА!**
━━━━━━━━━━━━━━━━━━━━━━━━━
{combat_log}
Ви перемогли {enemy['name']}!

Нагороди:
💰 +{enemy['gold_reward']} золота
⚡ +{enemy['exp_reward']} досвіду{material_text}

🕐 Оновлено: {timestamp}
"""
            
            # Continue or exit
            keyboard = [
                [InlineKeyboardButton("➡️ Продовжити", callback_data="dungeon_room_continue")],
                [InlineKeyboardButton("🏛 Вийти до таверни", callback_data="tavern_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                victory_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        # Enemy attacks back with improved damage formula (from forest system)
        base_damage = max(enemy['attack'] * 0.8, enemy['attack'] - char_dict['defense'] * 0.7)
        min_damage = max(1, enemy['attack'] * 0.15)
        variance = random.uniform(0.9, 1.1)
        enemy_damage = int(max(min_damage, base_damage * variance))
        char_dict['health'] -= enemy_damage
        combat_log += f"👹 {enemy['name']} завдав {enemy_damage} урону!"
        
        await db.update_character_by_id(char_dict['user_id'], {'health': char_dict['health']})
        
        if char_dict['health'] <= 0:
            # Defeat
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            defeat_text = f"""
💀 **ПОРАЗКА!**
━━━━━━━━━━━━━━━━━━━━━━━━━
{combat_log}

Ви програли...
Повертаємося до таверни...

🕐 Оновлено: {timestamp}
"""
            
            # Respawn with 1 HP
            char_dict['health'] = 1
            await db.update_character_by_id(char_dict['user_id'], {'health': 1})
            
            keyboard = [[InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                defeat_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Continue combat
        combat_text = f"""
⚔️ **БІЙ ПРОДОВЖУЄТЬСЯ!**
━━━━━━━━━━━━━━━━━━━━━━━━━
{combat_log}

👤 {char_dict['name']}: {char_dict['health']}/{char_dict['max_health']} HP
👹 {enemy['name']}: {enemy['health']} HP

🕐 Оновлено: {timestamp}
"""
        
        keyboard = [
            [InlineKeyboardButton("⚔️ Атакувати", callback_data="dungeon_combat_attack")],
            [InlineKeyboardButton("🛡 Захищатися", callback_data="dungeon_combat_defend")],
            [InlineKeyboardButton("🏃‍♂️ Втекти", callback_data="dungeon_combat_flee")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            combat_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == "defend":
        # Defend reduces damage with improved formula (from forest system)
        reduced_attack = enemy['attack'] // 2
        base_damage = max(reduced_attack * 0.8, reduced_attack - char_dict['defense'] * 1.4)  # Extra defense bonus
        min_damage = max(0, reduced_attack * 0.1)
        variance = random.uniform(0.9, 1.1)
        enemy_damage = int(max(min_damage, base_damage * variance))
        char_dict['health'] -= enemy_damage
        
        await db.update_character_by_id(char_dict['user_id'], {'health': char_dict['health']})
        
        text = f"🛡 Ви захищаєтесь!\n👹 {enemy['name']} завдав {enemy_damage} урону (блоковано)!"
        await update.callback_query.answer(text)
        
        # Show combat status
        await start_dungeon_combat(update, context, character)
    
    elif action == "potion":
        # Show potion menu
        await show_dungeon_potion_menu(update, context, character)
    
    elif action == "flee":
        # Flee from combat
        if random.random() < 0.5:
            text = "🏃‍♂️ Ви втекли від бою!"
            context.user_data['current_enemy'] = None
            
            keyboard = [[InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.callback_query.answer("❌ Не вдалося втекти!")
            await start_dungeon_combat(update, context, character)


async def show_dungeon_potion_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show potion menu during dungeon combat"""
    
    user_id = update.effective_user.id
    
    from game_logic.potion_manager import potion_manager
    
    # Get player's potions from database
    conn = await db.get_connection()
    async with conn.execute('''
        SELECT item_id, quantity FROM player_equipment 
        WHERE user_id = ? AND item_type = 'consumable' AND quantity > 0
    ''', (user_id,)) as cursor:
        potion_rows = await cursor.fetchall()
    
    potion_text = f"""
🧪 **Використати зілля**
━━━━━━━━━━━━━━━━━━━━━━━━━
Оберіть зілля для використання:

"""
    
    keyboard = []
    has_potions = False
    
    for row in potion_rows:
        potion_id = row['item_id']
        quantity = row['quantity']
        
        potion = potion_manager.get_potion(potion_id)
        if potion and quantity > 0:
            has_potions = True
            
            # Show potion effects
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
            
            effects_text = " ".join(effects)
            button_text = f"{potion.name} x{quantity} ({effects_text})"
            
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"dungeon_use_potion_{potion.id}"
            )])
    
    if not has_potions:
        potion_text += "\n🔍 Немає доступних зілль"
    
    keyboard.append([InlineKeyboardButton("🔙 Назад до бою", callback_data="dungeon_combat_attack")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        potion_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def use_dungeon_potion(update: Update, context: ContextTypes.DEFAULT_TYPE, character, potion_id: str) -> None:
    """Use a potion during dungeon combat"""
    
    user_id = update.effective_user.id
    
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
    from game_logic.inventory_manager import InventoryManager
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
    
    # Continue combat (enemy gets a turn)
    enemy = context.user_data.get('current_enemy')
    if enemy:
        # Enemy attacks after potion use
        base_damage = max(enemy['attack'] * 0.8, enemy['attack'] - char_dict['defense'] * 0.7)
        min_damage = max(1, enemy['attack'] * 0.15)
        variance = random.uniform(0.9, 1.1)
        enemy_damage = int(max(min_damage, base_damage * variance))
        char_dict['health'] -= enemy_damage
        
        await db.update_character_by_id(user_id, {'health': char_dict['health']})
        
        # Show updated combat status
        await start_dungeon_combat(update, context, character)


async def find_treasure(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Find treasure in dungeon"""
    # Convert Character object to dict if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
    else:
        char_dict = character
    
    gold_found = random.randint(20, 50)
    char_dict['gold'] += gold_found
    
    await db.update_character_by_id(char_dict['user_id'], {'gold': char_dict['gold']})
    
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    text = f"""
💰 **Скарб знайдено!**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви знайшли скриню зі скарбами!
+{gold_found} золота

💰 Всього золота: {char_dict['gold']}

🕐 Оновлено: {timestamp}
"""
    
    keyboard = [
        [InlineKeyboardButton("➡️ Продовжити", callback_data="dungeon_room_continue")],
        [InlineKeyboardButton("🏛 Вийти до таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def trigger_trap(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Trigger a trap"""
    # Convert Character object to dict if needed
    if hasattr(character, 'to_dict'):
        char_dict = character.to_dict()
    else:
        char_dict = character
    
    damage = random.randint(5, 15)
    char_dict['health'] = max(1, char_dict['health'] - damage)
    
    await db.update_character_by_id(char_dict['user_id'], {'health': char_dict['health']})
    
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    text = f"""
⚠️ **Пастка!**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви потрапили в пастку!
-{damage} здоров'я

💚 Здоров'я: {char_dict['health']}/{char_dict['max_health']}

🕐 Оновлено: {timestamp}
"""
    
    keyboard = [
        [InlineKeyboardButton("➡️ Продовжити", callback_data="dungeon_room_continue")],
        [InlineKeyboardButton("🏛 Вийти до таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def find_empty_room(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Find empty room"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    text = f"""
🔍 **Порожня кімната**
━━━━━━━━━━━━━━━━━━━━━━━━━
Кімната порожня. Нічого цікавого.

🕐 Оновлено: {timestamp}
"""
    
    keyboard = [
        [InlineKeyboardButton("➡️ Продовжити", callback_data="dungeon_room_continue")],
        [InlineKeyboardButton("🏛 Вийти до таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )