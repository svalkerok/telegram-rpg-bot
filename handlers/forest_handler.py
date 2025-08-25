"""
Forest handler - manages forest hunting with new combat system
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import random

from database.db_manager import DatabaseManager
from game_logic.combat import CombatManager, CombatAction, CombatResult, calculate_combat_power, get_combat_recommendation
from game_logic.character import CharacterManager
from game_logic.inventory_manager import InventoryManager
from game_logic.enemies import EnemyManager, EnemyType
from game_logic.items import ItemManager
from game_logic.balance_system import BalanceSystem
from database.database_models import Character
# Potion utility functions
def apply_temp_effects(base_stats: dict, temp_effects: dict) -> dict:
    """Apply temporary effects to character stats"""
    modified_stats = base_stats.copy()
    if 'attack_boost' in temp_effects:
        modified_stats['attack'] = base_stats.get('attack', 0) + temp_effects['attack_boost']['value']
    if 'defense_boost' in temp_effects:
        modified_stats['defense'] = base_stats.get('defense', 0) + temp_effects['defense_boost']['value']
    return modified_stats

def process_temp_effects(context, character_dict: dict) -> tuple:
    """Process temporary effects for one combat turn"""
    temp_effects = context.user_data.get('temp_effects', {})
    effects_text = ""
    
    if 'health_regen' in temp_effects:
        regen_value = temp_effects['health_regen']['value']
        new_health = min(character_dict['max_health'], character_dict['health'] + regen_value)
        health_gain = new_health - character_dict['health']
        character_dict['health'] = new_health
        if health_gain > 0:
            effects_text += f"💚 Регенерація: +{health_gain} HP\n"
    
    # Reduce duration
    expired_effects = []
    for effect_name, effect_data in temp_effects.items():
        effect_data['duration'] -= 1
        if effect_data['duration'] <= 0:
            expired_effects.append(effect_name)
    
    for effect_name in expired_effects:
        del temp_effects[effect_name]
    
    context.user_data['temp_effects'] = temp_effects
    return character_dict, effects_text

def get_active_effects_display(temp_effects: dict) -> str:
    """Get display text for active temporary effects"""
    if not temp_effects:
        return ""
    
    effects_display = "\n🧪 **Активні ефекти:**\n"
    for effect_name, effect_data in temp_effects.items():
        value = effect_data['value']
        duration = effect_data['duration']
        
        if effect_name == 'attack_boost':
            effects_display += f"⚔️ Сила +{value} ({duration} ходів)\n"
        elif effect_name == 'defense_boost':
            effects_display += f"🛡️ Захист +{value} ({duration} ходів)\n"
        elif effect_name == 'health_regen':
            effects_display += f"💚 Регенерація {value} HP/хід ({duration} ходів)\n"
    
    return effects_display

def get_combat_potions_keyboard(inventory):
    """Get keyboard with usable combat potions"""
    from handlers.shop_handler import SHOP_ITEMS
    
    keyboard = []
    if inventory and inventory.items:
        for item in inventory.items:
            if item.item_type == 'potion' and item.quantity > 0:
                potion_info = None
                for category in SHOP_ITEMS.values():
                    if item.item_id in category:
                        potion_info = category[item.item_id]
                        break
                
                if potion_info and potion_info.get('usable_in_combat', False):
                    keyboard.append([InlineKeyboardButton("🧪 Використати зілля", callback_data="combat_potion_menu")])
                    break
    
    return keyboard
import config

logger = logging.getLogger(__name__)
db = DatabaseManager(config.DATABASE_URL)

# Initialize game managers
item_manager = ItemManager()
enemy_manager = EnemyManager()
character_manager = CharacterManager(db)
combat_manager = CombatManager(character_manager, item_manager)


async def get_character_data(character):
    """Helper function to extract character data with equipment bonuses"""
    if hasattr(character, 'to_dict'):
        # Get full stats with equipment bonuses
        inventory_manager = InventoryManager(db)
        try:
            character_stats = await inventory_manager.calculate_character_stats(character.user_id)
            
            return {
                'user_id': character.user_id,
                'name': character.name,
                'character_class': character.character_class,
                'level': character.level,
                'health': character.health,
                'max_health': character.max_health,
                'gold': character.gold,
                'attack': character_stats.total_attack,      # With equipment!
                'defense': character_stats.total_defense,    # With equipment!
                'experience': character.experience
            }
        except Exception as e:
            logger.error(f"Error calculating character stats: {e}")
            # Fallback to base stats
            return {
                'user_id': character.user_id,
                'name': character.name,
                'character_class': character.character_class,
                'level': character.level,
                'health': character.health,
                'max_health': character.max_health,
                'gold': character.gold,
                'attack': character.attack,
                'defense': character.defense,
                'experience': character.experience
            }
    else:
        return character


def calculate_level_difficulty(player_level: int, enemy_level: int) -> str:
    """Calculate difficulty based on level difference"""
    level_diff = enemy_level - player_level
    
    if level_diff <= -3:
        return 'very_easy'
    elif level_diff <= -1:
        return 'easy'
    elif level_diff <= 1:
        return 'normal'
    elif level_diff <= 3:
        return 'hard'
    elif level_diff <= 5:
        return 'very_hard'
    else:
        return 'impossible'


async def show_forest_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show forest menu with updated interface"""
    
    char_data = await get_character_data(character)
    
    # Convert dict to Character object for new system
    char_obj = Character(**char_data)
    
    # Get character power
    char_power = calculate_combat_power(char_obj, character_manager)
    
    forest_text = f"""
🌲 **Темний ліс**
━━━━━━━━━━━━━━━━━━━━━━━━━
Величезний ліс, повний небезпечних створінь та скарбів.

👤 {char_data['name']} | Рівень: {char_data['level']}
💚 Здоров'я: {char_data['health']}/{char_data['max_health']}
💪 Сила в бою: {char_power}

🌿 **Доступні зони лісу:**
"""
    
    keyboard = []
    
    for zone_id, zone_data in config.FOREST_ZONES.items():
        if char_data['level'] >= zone_data['min_level']:
            # Calculate difficulty
            avg_enemy_level = (zone_data['min_level'] + zone_data['max_level']) // 2
            difficulty = calculate_level_difficulty(char_data['level'], avg_enemy_level)
            
            difficulty_emoji = {
                'very_easy': '😴',
                'easy': '🟢', 
                'normal': '🟡',
                'hard': '🟠',
                'very_hard': '🔴',
                'impossible': '💀'
            }.get(difficulty, '🟡')
            
            zone_button = f"{difficulty_emoji} {zone_data['name']} (Рівень {zone_data['min_level']}-{zone_data['max_level']})"
            keyboard.append([InlineKeyboardButton(zone_button, callback_data=f"forest_hunt_{zone_id}")])
        else:
            locked_button = f"🔒 {zone_data['name']} (Потрібен рівень {zone_data['min_level']})"
            keyboard.append([InlineKeyboardButton(locked_button, callback_data="forest_locked")])
    
    keyboard.extend([
        [InlineKeyboardButton("📊 Статистика полювання", callback_data="forest_stats")],
        [InlineKeyboardButton("🏛 Повернутися до таверни", callback_data="tavern_main")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        forest_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def forest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle forest callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Get character
    character = await db.get_character(user_id)
    if not character:
        await query.edit_message_text("❌ Персонаж не знайдений!")
        return
    
    if data.startswith("forest_hunt_"):
        zone = data.replace("forest_hunt_", "")
        await start_forest_hunt(update, context, character, zone)
    
    elif data.startswith("forest_combat_"):
        action = data.replace("forest_combat_", "")
        await process_forest_combat(update, context, character, action)
    
    elif data == "forest_stats":
        await show_forest_stats(update, context, character)
    
    elif data == "combat_potion_menu":
        await show_combat_potion_menu(update, context, character)
    
    elif data.startswith("combat_use_potion_"):
        potion_id = data.replace("combat_use_potion_", "")
        await use_combat_potion(update, context, character, potion_id)
    
    elif data == "forest_continue":
        await continue_forest_hunt(update, context, character)
    
    elif data == "forest_return":
        await show_forest_menu(update, context, character)
    
    elif data == "forest_locked":
        await query.answer("❌ Ваш рівень занадто низький для цієї зони!", show_alert=True)


async def show_forest_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show forest hunting statistics"""
    
    char_data = await get_character_data(character)
    stats = await db.get_statistics(char_data['user_id'])
    
    stats_text = f"""
📊 **Статистика полювання**
━━━━━━━━━━━━━━━━━━━━━━━━━
👤 {char_data['name']}

🏹 Убито ворогів: {stats.enemies_killed if stats else 0}
💰 Зароблено золота: {stats.gold_earned if stats else 0}
⚡ Отримано досвіду: {stats.experience_gained if stats else 0}
🏆 Перемог у лісі: {stats.forest_wins if stats else 0}

Продовжуйте полювати, щоб покращити статистику!
"""
    
    keyboard = [
        [InlineKeyboardButton("🌲 Назад до лісу", callback_data="forest_return")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def start_forest_hunt(update: Update, context: ContextTypes.DEFAULT_TYPE, character, zone: str) -> None:
    """Start hunting in selected forest zone"""
    
    char_data = await get_character_data(character)
    balance_system = BalanceSystem()
    
    if zone not in config.FOREST_ZONES:
        await update.callback_query.answer("❌ Невідома зона лісу!")
        return
    
    zone_data = config.FOREST_ZONES[zone]
    
    # Check level requirement
    if char_data['level'] < zone_data['min_level']:
        await update.callback_query.answer("❌ Ваш рівень занадто низький!", show_alert=True)
        return
    
    # Generate enemy for this zone with balance scaling
    # Create Character object with updated stats for power calculation
    char_obj = Character(
        user_id=char_data['user_id'],
        name=char_data['name'],
        character_class=char_data['character_class'],
        level=char_data['level'],
        health=char_data['health'],
        max_health=char_data['max_health'],
        attack=char_data['attack'],  # With equipment bonuses
        defense=char_data['defense'],  # With equipment bonuses
        gold=char_data['gold'],
        experience=char_data['experience']
    )
    
    # Get base enemy template from enemy manager
    base_enemy = enemy_manager.get_random_enemy_for_location(EnemyType.FOREST, char_data['level'])
    
    # Calculate player power for scaling
    player_power = balance_system.calculate_player_power({
        'level': char_data['level'],
        'attack': char_data['attack'],
        'defense': char_data['defense'],
        'max_health': char_data['max_health'],
        'speed': char_data.get('speed', 10),
        'critical_chance': char_data.get('critical_chance', 5),
        'magic_power': char_data.get('magic_power', 0)
    })
    
    # Create base enemy dict for scaling
    base_enemy_dict = {
        'name': base_enemy.name,
        'health': base_enemy.max_health,
        'attack': base_enemy.attack,
        'defense': base_enemy.defense,
        'speed': base_enemy.speed
    }
    
    # Determine difficulty based on zone level
    avg_zone_level = (zone_data['min_level'] + zone_data['max_level']) // 2
    if avg_zone_level <= char_data['level'] - 2:
        difficulty = 'easy'
    elif avg_zone_level >= char_data['level'] + 2:
        difficulty = 'hard'
    else:
        difficulty = 'normal'
    
    # Scale enemy using balance system
    scaled_enemy_dict = balance_system.scale_enemy_stats(
        base_enemy_dict, char_data['level'], player_power, difficulty
    )
    
    # Apply scaled stats to enemy object
    base_enemy.max_health = scaled_enemy_dict['max_health']
    base_enemy.health = scaled_enemy_dict['health']
    base_enemy.attack = scaled_enemy_dict['attack']
    base_enemy.defense = scaled_enemy_dict['defense']
    base_enemy.speed = scaled_enemy_dict['speed']
    base_enemy.level = scaled_enemy_dict['level']
    base_enemy.experience_reward = scaled_enemy_dict['exp_reward']
    base_enemy.gold_min = max(1, scaled_enemy_dict['gold_reward'] - 5)
    base_enemy.gold_max = scaled_enemy_dict['gold_reward'] + 5
    
    # Use the scaled enemy
    enemy = base_enemy
    
    # Store combat data
    context.user_data['forest_combat'] = {
        'enemy': enemy,
        'zone': zone,
        'char_obj': char_obj
    }
    
    # Calculate difficulty and get recommendation
    difficulty = calculate_level_difficulty(char_data['level'], enemy.level)
    char_power = calculate_combat_power(char_obj, character_manager)
    enemy_difficulty = enemy.max_health + enemy.attack * 10 + enemy.defense * 5  # Simple calculation
    recommendation = get_combat_recommendation(char_power, enemy_difficulty)
    
    difficulty_text = {
        'very_easy': '😴 Дуже легко',
        'easy': '🟢 Легко',
        'normal': '🟡 Нормально',
        'hard': '🟠 Складно',
        'very_hard': '🔴 Дуже складно',
        'impossible': '💀 Неможливо'
    }.get(difficulty, '🟡 Нормально')
    
    hunt_text = f"""
🌲 **Полювання в лісі - {zone_data['name']}**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви зустріли: **{enemy.name}** (Рівень {enemy.level})

👤 Ви: {char_data['health']}/{char_data['max_health']} HP
👹 {enemy.name}: {enemy.health}/{enemy.max_health} HP

📈 Складність: {difficulty_text}
💡 Рекомендація: {recommendation}

Що будете робити?
"""
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Атакувати", callback_data="forest_combat_attack")],
        [InlineKeyboardButton("🛡 Захищатися", callback_data="forest_combat_defend")],
        [InlineKeyboardButton("🔮 Магічна атака", callback_data="forest_combat_magic")],
        [InlineKeyboardButton("🏃 Втекти", callback_data="forest_combat_flee")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        hunt_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def process_forest_combat(update: Update, context: ContextTypes.DEFAULT_TYPE, character, action: str) -> None:
    """Process forest combat with simple combat system"""
    
    char_data = await get_character_data(character)
    combat_data = context.user_data.get('forest_combat')
    
    if not combat_data:
        await update.callback_query.answer("❌ Помилка бою!")
        return
    
    enemy = combat_data['enemy']
    
    combat_text = ""
    
    if action == "attack":
        # Apply temporary effects to attack
        modified_stats = apply_temp_effects(char_data, context.user_data.get('temp_effects', {}))
        
        # Player attacks with modified stats - improved damage formula
        base_damage = max(modified_stats['attack'] * 0.8, modified_stats['attack'] - enemy.defense * 0.7)
        min_damage = max(1, modified_stats['attack'] * 0.15)
        variance = random.uniform(0.9, 1.1)
        damage = int(max(min_damage, base_damage * variance))
        enemy.health -= damage
        combat_text += f"⚔️ Ви завдали {damage} шкоди!\n"
        
        # Check if enemy is defeated
        if enemy.health <= 0:
            await handle_forest_victory(update, context, character, enemy)
            return
        
        # Enemy attacks back (use modified defense) - improved damage formula
        base_damage = max(enemy.attack * 0.8, enemy.attack - modified_stats['defense'] * 0.7)
        min_damage = max(1, enemy.attack * 0.15)
        variance = random.uniform(0.9, 1.1)
        enemy_damage = int(max(min_damage, base_damage * variance))
        
        # Update both character object and database
        character.health -= enemy_damage
        char_data['health'] = character.health
        combat_text += f"💥 {enemy.name} завдав вам {enemy_damage} шкоди!\n"
        
        # Update character health in database
        await db.update_character_by_id(char_data['user_id'], {'health': character.health})
        
        # Check if player is defeated
        if char_data['health'] <= 0:
            await handle_forest_defeat(update, context, character)
            return
    
    elif action == "defend":
        combat_text += "🛡 Ви зайняли оборонну позицію!\n"
        
        # Enemy attacks with reduced damage - improved damage formula
        reduced_attack = enemy.attack // 2
        base_damage = max(reduced_attack * 0.8, reduced_attack - char_data['defense'] * 1.4)  # Extra defense bonus
        min_damage = max(0, reduced_attack * 0.1)
        variance = random.uniform(0.9, 1.1)
        enemy_damage = int(max(min_damage, base_damage * variance))
        
        # Update both character object and database
        character.health -= enemy_damage
        char_data['health'] = character.health
        combat_text += f"💥 {enemy.name} завдав вам {enemy_damage} шкоди (блоковано)!\n"
        
        await db.update_character_by_id(char_data['user_id'], {'health': character.health})
        
        # Check if player is defeated
        if char_data['health'] <= 0:
            await handle_forest_defeat(update, context, character)
            return
    
    elif action == "magic":
        # Magic attack (if character has mana)
        if char_data.get('mana', 0) > 0:
            # Magic damage ignores more defense - improved formula
            magic_power = char_data.get('magic_power', 5)
            base_damage = max(magic_power * 0.9, magic_power - enemy.defense * 0.3)  # Magic ignores more defense
            min_damage = max(1, magic_power * 0.2)
            variance = random.uniform(0.9, 1.1)
            magic_damage = int(max(min_damage, base_damage * variance))
            enemy.health -= magic_damage
            combat_text += f"🔮 Ви завдали {magic_damage} магічної шкоди!\n"
            
            # Check if enemy is defeated
            if enemy.health <= 0:
                await handle_forest_victory(update, context, character, enemy)
                return
        else:
            # No mana, regular attack - improved damage formula
            base_damage = max(char_data['attack'] * 0.8, char_data['attack'] - enemy.defense * 0.7)
            min_damage = max(1, char_data['attack'] * 0.15)
            variance = random.uniform(0.9, 1.1)
            damage = int(max(min_damage, base_damage * variance))
            enemy.health -= damage
            combat_text += f"⚔️ Немає мани! Ви завдали {damage} фізичної шкоди!\n"
            
            # Check if enemy is defeated
            if enemy.health <= 0:
                await handle_forest_victory(update, context, character, enemy)
                return
        
        # Enemy attacks back - improved damage formula
        base_damage = max(enemy.attack * 0.8, enemy.attack - char_data['defense'] * 0.7)
        min_damage = max(1, enemy.attack * 0.15)
        variance = random.uniform(0.9, 1.1)
        enemy_damage = int(max(min_damage, base_damage * variance))
        
        # Update both character object and database
        character.health -= enemy_damage
        char_data['health'] = character.health
        combat_text += f"💥 {enemy.name} завдав вам {enemy_damage} шкоди!\n"
        
        await db.update_character_by_id(char_data['user_id'], {'health': character.health})
        
        # Check if player is defeated
        if char_data['health'] <= 0:
            await handle_forest_defeat(update, context, character)
            return
    
    elif action == "flee":
        await handle_forest_flee(update, context, character)
        return
    
    # Continue combat
    await continue_forest_combat(update, context, character, enemy, combat_text)


async def continue_forest_combat(update: Update, context: ContextTypes.DEFAULT_TYPE, character, enemy, combat_description) -> None:
    """Continue forest combat"""
    
    char_data = await get_character_data(character)
    
    # Process temporary effects
    char_data, effects_text = process_temp_effects(context, char_data)
    
    # Add turn counter to avoid duplicate messages
    turn_counter = context.user_data.get('combat_turn', 0) + 1
    context.user_data['combat_turn'] = turn_counter
    
    # Get active effects display
    active_effects = get_active_effects_display(context.user_data.get('temp_effects', {}))
    
    combat_text = f"""
🌲 **Бій триває!** (Хід {turn_counter})
━━━━━━━━━━━━━━━━━━━━━━━━━
{combat_description}
{effects_text if effects_text else ""}
👤 Ви: {char_data['health']}/{char_data['max_health']} HP
👹 {enemy.name}: {enemy.health}/{enemy.max_health} HP
{active_effects}
Що будете робити далі?
"""
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Атакувати", callback_data="forest_combat_attack")],
        [InlineKeyboardButton("🛡 Захищатися", callback_data="forest_combat_defend")],
        [InlineKeyboardButton("🔮 Магічна атака", callback_data="forest_combat_magic")],
        [InlineKeyboardButton("🏃 Втекти", callback_data="forest_combat_flee")]
    ]
    
    # Add potion button if available
    if hasattr(character, 'user_id'):
        user_id = character.user_id
    else:
        user_id = character['user_id']
    
    inventory = await db.get_inventory(user_id)
    potion_buttons = get_combat_potions_keyboard(inventory)
    if potion_buttons:
        keyboard.extend(potion_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        combat_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_forest_victory(update: Update, context: ContextTypes.DEFAULT_TYPE, character, enemy) -> None:
    """Handle victory in forest combat"""
    
    char_data = await get_character_data(character)
    
    # Calculate rewards (reduced experience for better balance)
    gold_reward = random.randint(8, 20) + enemy.level * 2
    exp_reward = random.randint(8, 18) + enemy.level * 2  # Reduced from 15-40 + level*3
    
    # Get character object for level up system
    character_obj = await db.get_character(char_data['user_id'])
    if not character_obj:
        return
    
    # Update gold
    character_obj.gold += gold_reward
    
    # Add experience with proper level up handling
    character_manager = CharacterManager(db)
    exp_result = character_manager.add_experience(character_obj, exp_reward)
    
    # Update character in database
    await db.update_character(character_obj)
    
    # Update statistics
    await db.update_statistics_by_id(char_data['user_id'], {
        'enemies_killed': 1,
        'gold_earned': gold_reward,
        'experience_gained': exp_reward,
        'forest_wins': 1
    })
    
    # Update quest progress for forest clearing, battle damage, and gold collection
    from handlers.daily_quests_handler import update_quest_progress, notify_quest_completion
    completed_quests_forest = await update_quest_progress(char_data['user_id'], 'forest', 1)
    completed_quests_damage = await update_quest_progress(char_data['user_id'], 'damage', random.randint(15, 25))
    completed_quests_gold = await update_quest_progress(char_data['user_id'], 'gold', gold_reward)
    completed_quests = completed_quests_forest + completed_quests_damage + completed_quests_gold
    quest_text = await notify_quest_completion(update, context, completed_quests)
    
    # Roll for material drops
    from game_logic.equipment import EquipmentManager
    from game_logic.inventory_manager import InventoryManager
    equipment_manager = EquipmentManager(db)
    inventory_manager = InventoryManager(db)
    
    # Handle both dict and Enemy object types
    if hasattr(enemy, 'name'):
        enemy_name = enemy.name
        enemy_level = getattr(enemy, 'level', 1)
    else:
        enemy_name = enemy.get('name', 'enemy')
        enemy_level = enemy.get('level', 1)
    
    # Determine enemy type for material drops
    enemy_type = "normal"
    enemy_name_lower = enemy_name.lower()
    
    # Check for boss/dragon keywords
    if any(keyword in enemy_name_lower for keyword in ["бос", "дракон", "лицар", "ліч", "володар", "чемпіон", "воїн", "смерті"]):
        enemy_type = "boss"
    elif any(keyword in enemy_name_lower for keyword in ["древній", "легендарний", "міфічний", "божественний"]):
        enemy_type = "dragon"
    
    material_drops = equipment_manager.roll_material_drop(enemy_type, enemy_level)
    
    # Add materials to player
    if any(material_drops.values()):
        await inventory_manager.add_materials(char_data['user_id'], material_drops)
        
        # Create material drop text
        material_text = "\n\n💎 **Знайдено матеріали:**\n"
        if material_drops.get("gods_stone", 0) > 0:
            material_text += f"💎 Каміння богів: +{material_drops['gods_stone']}\n"
        if material_drops.get("mithril_dust", 0) > 0:
            material_text += f"✨ Мітрилова пил: +{material_drops['mithril_dust']}\n"
        if material_drops.get("dragon_scale", 0) > 0:
            material_text += f"🐉 Драконяча луска: +{material_drops['dragon_scale']}\n"
    else:
        material_text = ""
    
    # Check for new achievements
    from game_logic.achievements import AchievementManager
    achievement_manager = AchievementManager(db)
    new_achievements = await achievement_manager.check_achievements(char_data['user_id'])
    
    achievement_text = ""
    if new_achievements:
        achievement_text = "\n🏆 **НОВІ ДОСЯГНЕННЯ!**\n"
        for achievement in new_achievements:
            reward_text = await achievement_manager.give_achievement_reward(char_data['user_id'], achievement)
            achievement_text += f"{achievement.icon} **{achievement.name}**\n"
            achievement_text += f"🎁 {reward_text}\n"
    
    victory_text = f"""
🏆 **ПЕРЕМОГА!**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви перемогли {enemy.name}!

🎁 Нагороди:
💰 Золото: +{gold_reward}
⚡ Досвід: +{exp_reward}

💚 Здоров'я: {character_obj.health}/{character_obj.max_health}
💰 Золото: {int(character_obj.gold)}
{material_text}{quest_text}{achievement_text}"""

    # Add level up message if leveled up
    if exp_result['level_up']:
        victory_text += f"""
🎉 **ПІДВИЩЕННЯ РІВНЯ!**
📈 Рівень: {exp_result['old_level']} → {exp_result['new_level']}
💪 Ваші характеристики покращились!
"""
    
    # Check for critical health
    if char_data['health'] <= 0:
        victory_text += "\n⚠️ Ваше здоров'я критично низьке!"
    
    # Clear combat data
    context.user_data.pop('forest_combat', None)
    context.user_data.pop('combat_turn', None)
    
    keyboard = [
        [InlineKeyboardButton("🌲 Продовжити полювання", callback_data="forest_continue")],
        [InlineKeyboardButton("🏛 Повернутися до таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        victory_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_forest_defeat(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Handle defeat in forest"""
    
    char_data = await get_character_data(character)
    
    # Set health to 1
    char_data['health'] = 1
    await db.update_character_by_id(char_data['user_id'], {'health': 1})
    
    defeat_text = f"""
💀 **ПОРАЗКА**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви програли бій і втратили свідомість...

💚 Здоров'я відновлено до 1
🏥 Рекомендуємо відпочити в таверні

Не засмучуйтесь! Тренуйтесь і повертайтесь сильнішими!
"""
    
    # Clear combat data
    context.user_data.pop('forest_combat', None)
    context.user_data.pop('combat_turn', None)
    
    keyboard = [
        [InlineKeyboardButton("🏥 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        defeat_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_forest_flee(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Handle fleeing from forest combat"""
    
    char_data = await get_character_data(character)
    
    flee_text = f"""
🏃 **Втеча**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви втекли з бою!

• Здоров'я: {char_data['health']}/{char_data['max_health']}

Іноді розсудливість важливіша за хоробрість!
"""
    
    # Clear combat data
    context.user_data.pop('forest_combat', None)
    context.user_data.pop('combat_turn', None)
    
    keyboard = [
        [InlineKeyboardButton("🌲 Спробувати знову", callback_data="forest_continue")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        flee_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def continue_forest_hunt(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Continue hunting in the forest"""
    
    char_data = await get_character_data(character)
    
    continue_text = f"""
🌲 **Темний ліс**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви продовжуєте блукати лісом у пошуках пригод...

💚 Здоров'я: {char_data['health']}/{char_data['max_health']}
💰 Золото: {int(char_data['gold'])}

Оберіть зону для полювання:
"""
    
    keyboard = []
    
    for zone_id, zone_data in config.FOREST_ZONES.items():
        if char_data['level'] >= zone_data['min_level']:
            zone_button = f"🌿 {zone_data['name']} (Рівень {zone_data['min_level']}-{zone_data['max_level']})"
            keyboard.append([InlineKeyboardButton(zone_button, callback_data=f"forest_hunt_{zone_id}")])
        else:
            locked_button = f"🔒 {zone_data['name']} (Потрібен рівень {zone_data['min_level']})"
            keyboard.append([InlineKeyboardButton(locked_button, callback_data="forest_locked")])
    
    keyboard.append([InlineKeyboardButton("🏛 Повернутися до таверни", callback_data="tavern_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        continue_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_combat_potion_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show available potions during combat"""
    
    if hasattr(character, 'user_id'):
        user_id = character.user_id
    else:
        user_id = character['user_id']
    
    inventory = await db.get_inventory(user_id)
    
    potion_text = """
🧪 **Бойові зілля**
━━━━━━━━━━━━━━━━━━━━━━━━━
Оберіть зілля для використання:
"""
    
    keyboard = []
    
    if inventory and inventory.items:
        from handlers.shop_handler import SHOP_ITEMS
        
        for item in inventory.items:
            if item.item_type == 'potion' and item.quantity > 0:
                # Check if potion is usable in combat
                potion_info = None
                for category in SHOP_ITEMS.values():
                    if item.item_id in category:
                        potion_info = category[item.item_id]
                        break
                
                if potion_info and potion_info.get('usable_in_combat', False):
                    # Show potion effects
                    effects = []
                    if 'health' in potion_info:
                        effects.append(f"💚+{potion_info['health']} HP")
                    if 'mana' in potion_info:
                        effects.append(f"⚡+{potion_info['mana']} MP")
                    if 'attack_boost' in potion_info:
                        effects.append(f"⚔️+{potion_info['attack_boost']} атака")
                    if 'defense_boost' in potion_info:
                        effects.append(f"🛡️+{potion_info['defense_boost']} захист")
                    if 'health_regen' in potion_info:
                        effects.append(f"💚{potion_info['health_regen']} HP/хід")
                    
                    effects_text = " ".join(effects)
                    button_text = f"{item.name} x{item.quantity} ({effects_text})"
                    
                    keyboard.append([InlineKeyboardButton(
                        button_text,
                        callback_data=f"combat_use_potion_{item.item_id}"
                    )])
    
    if not keyboard:
        potion_text += "\n🔍 Немає доступних бойових зілль"
    
    keyboard.append([InlineKeyboardButton("🔙 Назад до бою", callback_data="forest_combat_attack")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        potion_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def use_combat_potion(update: Update, context: ContextTypes.DEFAULT_TYPE, character, potion_id: str) -> None:
    """Use a potion during combat"""
    
    char_data = await get_character_data(character)
    combat_data = context.user_data.get('forest_combat')
    
    if not combat_data:
        await update.callback_query.answer("❌ Помилка бою!")
        return
    
    # Get potion info
    from handlers.shop_handler import SHOP_ITEMS
    potion_info = None
    for category in SHOP_ITEMS.values():
        if potion_id in category:
            potion_info = category[potion_id]
            break
    
    if not potion_info:
        await update.callback_query.answer("❌ Зілля не знайдено!")
        return
    
    # Check if player has this potion
    inventory = await db.get_inventory(char_data['user_id'])
    has_potion = False
    for item in inventory.items:
        if item.item_id == potion_id and item.quantity > 0:
            has_potion = True
            break
    
    if not has_potion:
        await update.callback_query.answer("❌ У вас немає цього зілля!")
        return
    
    # Apply potion effects
    updates = {}
    effects_text = "🧪 Ви використали зілля!\n"
    
    # Instant effects
    if 'health' in potion_info:
        new_health = min(char_data['max_health'], char_data['health'] + potion_info['health'])
        health_gained = new_health - char_data['health']
        char_data['health'] = new_health
        updates['health'] = new_health
        effects_text += f"💚 Відновлено {health_gained} здоров'я\n"
    
    if 'mana' in potion_info:
        new_mana = min(char_data['max_mana'], char_data['mana'] + potion_info['mana'])
        mana_gained = new_mana - char_data['mana']
        char_data['mana'] = new_mana
        updates['mana'] = new_mana
        effects_text += f"⚡ Відновлено {mana_gained} мани\n"
    
    # Temporary effects
    temp_effects = context.user_data.get('temp_effects', {})
    
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
    
    if 'health_regen' in potion_info:
        temp_effects['health_regen'] = {
            'value': potion_info['health_regen'],
            'duration': potion_info.get('duration', 1)
        }
        effects_text += f"💚 Регенерація {potion_info['health_regen']} HP/хід на {potion_info.get('duration', 1)} ходів\n"
    
    # Store effects
    context.user_data['temp_effects'] = temp_effects
    
    # Update character
    if updates:
        await db.update_character_by_id(char_data['user_id'], updates)
    
    # Remove potion from inventory
    await db.remove_item_from_inventory(char_data['user_id'], potion_id, 1)
    
    # Update statistics
    await db.update_statistics_by_id(char_data['user_id'], {'potions_used': 1})
    
    # Continue combat (enemy gets a turn)
    enemy = combat_data['enemy']
    
    # Enemy attacks (using potion takes your turn)
    modified_stats = apply_temp_effects(char_data, temp_effects)
    # Enemy attacks after potion use - improved damage formula
    base_damage = max(enemy.attack * 0.8, enemy.attack - modified_stats['defense'] * 0.7)
    min_damage = max(1, enemy.attack * 0.15)
    variance = random.uniform(0.9, 1.1)
    enemy_damage = int(max(min_damage, base_damage * variance))
    char_data['health'] -= enemy_damage
    effects_text += f"💥 {enemy.name} завдав вам {enemy_damage} шкоди!\n"
    
    # Update character health after enemy attack
    await db.update_character_by_id(char_data['user_id'], {'health': char_data['health']})
    
    # Check if player is defeated
    if char_data['health'] <= 0:
        await handle_forest_defeat(update, context, character)
        return
    
    # Continue combat
    await continue_forest_combat(update, context, character, enemy, effects_text)
