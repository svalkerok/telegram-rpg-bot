"""
Arena handler - manages PvP battles
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import random

from database.db_manager import DatabaseManager
from game_logic.character import CharacterManager
from game_logic.inventory_manager import InventoryManager
from game_logic.balance_system import BalanceSystem
# Simple potion utility functions for arena
def apply_temp_effects(base_stats: dict, temp_effects: dict) -> dict:
    """Apply temporary effects to character stats"""
    modified_stats = base_stats.copy()
    if 'attack_boost' in temp_effects:
        modified_stats['attack'] = base_stats.get('attack', 0) + temp_effects['attack_boost']['value']
    return modified_stats
import config

logger = logging.getLogger(__name__)
db = DatabaseManager(config.DATABASE_URL)


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
                'speed': character_stats.total_speed,           # With equipment!
                'defense': character_stats.total_defense,       # With equipment!
                'gold': character.gold,
                'experience': character.experience,
                'attack': character_stats.total_attack          # With equipment!
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
                'speed': character.speed,
                'defense': character.defense,
                'gold': character.gold,
                'experience': character.experience,
                'attack': character.attack
            }
    else:
        return character


async def show_arena_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show arena menu"""
    
    char_data = await get_character_data(character)
    stats = await db.get_statistics(char_data['user_id'])
    
    arena_text = f"""
⚔️ **Арена Камінного Притулку**
━━━━━━━━━━━━━━━━━━━━━━━━━
Тут ви можете битися з іншими авантюристами!

👤 {char_data['name']} | Рівень: {char_data['level']}
💚 Здоров'я: {char_data['health']}/{char_data['max_health']}
"""
    
    if stats:
        arena_text += f"""
🏆 Перемог: {stats.arena_wins}
💀 Поразок: {stats.arena_losses}
"""
    
    arena_text += "\n🎯 Оберіть тип битви:"
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Швидкий бій", callback_data="arena_quick_fight")],
        [InlineKeyboardButton("🎯 Вибрати противника", callback_data="arena_choose_opponent")],
        [InlineKeyboardButton("🏆 Рейтинг арени", callback_data="arena_rating")],
        [InlineKeyboardButton("🏛 Повернутися до таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        arena_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def arena_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle arena callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Get character
    character = await db.get_character(user_id)
    if not character:
        await query.edit_message_text("❌ Персонаж не знайдений!")
        return
    
    if data == "arena_quick_fight":
        await start_quick_fight(update, context, character)
    
    elif data == "arena_choose_opponent":
        await show_opponent_list(update, context, character)
    
    elif data == "arena_combat_potion_menu":
        await show_combat_potion_menu(update, context, character)
    
    elif data.startswith("arena_combat_use_potion_"):
        potion_id = data.replace("arena_combat_use_potion_", "")
        await use_combat_potion(update, context, character, potion_id)
    
    elif data.startswith("arena_fight_"):
        opponent_level = int(data.replace("arena_fight_", ""))
        await start_arena_fight(update, context, character, opponent_level)
    
    elif data.startswith("arena_combat_"):
        action = data.replace("arena_combat_", "")
        await process_arena_combat(update, context, character, action)
    
    elif data == "arena_rating":
        await show_arena_rating(update, context)


async def start_quick_fight(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Start a quick arena fight with random opponent"""
    
    char_data = await get_character_data(character)
    
    # Generate opponent similar to player level
    opponent_level = char_data['level'] + random.randint(-1, 1)
    opponent_level = max(1, min(opponent_level, config.MAX_LEVEL))
    
    await start_arena_fight(update, context, character, opponent_level)


async def show_opponent_list(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show list of available opponents"""
    
    char_data = await get_character_data(character)
    
    opponents_text = f"""
🎯 **Вибір противника**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ваш рівень: {char_data['level']}

Доступні противники:
"""
    
    keyboard = []
    
    # Generate opponents of different levels
    for i in range(-2, 3):
        opponent_level = char_data['level'] + i
        if 1 <= opponent_level <= config.MAX_LEVEL:
            difficulty = ""
            if i < -1:
                difficulty = "😴 Легкий"
            elif i == -1:
                difficulty = "🟢 Простий"
            elif i == 0:
                difficulty = "🟡 Звичайний"
            elif i == 1:
                difficulty = "🟠 Складний"
            else:
                difficulty = "🔴 Дуже складний"
            
            button_text = f"{difficulty} - Рівень {opponent_level}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"arena_fight_{opponent_level}")])
    
    keyboard.append([InlineKeyboardButton("⚔️ Назад до арени", callback_data="tavern_arena")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        opponents_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def start_arena_fight(update: Update, context: ContextTypes.DEFAULT_TYPE, character, opponent_level: int) -> None:
    """Start arena fight"""
    
    char_data = await get_character_data(character)
    balance_system = BalanceSystem()
    
    # Generate opponent
    opponent_classes = ['warrior', 'mage', 'ranger']
    opponent_class = random.choice(opponent_classes)
    class_config = config.CHARACTER_CLASSES[opponent_class]
    
    # Generate opponent name
    warrior_names = ["Грім Залізний Кулак", "Торвальд Сокира", "Бьорн Громовержець"]
    mage_names = ["Елара Магічна", "Зорин Мудрий", "Селена Зоряна"]
    ranger_names = ["Ліра Швидкостріл", "Арагорн Лісовий", "Таліон Тінь"]
    
    name_lists = {
        'warrior': warrior_names,
        'mage': mage_names,
        'ranger': ranger_names
    }
    
    opponent_name = random.choice(name_lists[opponent_class])
    
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
    
    # Create base opponent template
    base_opponent = {
        'name': opponent_name,
        'health': class_config['base_stats']['max_health'],
        'attack': class_config['base_stats']['attack'],
        'defense': class_config['base_stats']['defense'],
        'speed': class_config['base_stats']['speed']
    }
    
    # Scale opponent using balance system (arena is 'normal' difficulty)
    scaled_opponent = balance_system.scale_enemy_stats(
        base_opponent, char_data['level'], player_power, 'normal'
    )
    
    # Create final opponent with scaled stats
    opponent = {
        'name': opponent_name,
        'class': opponent_class,
        'level': scaled_opponent['level'],
        'health': scaled_opponent['health'],
        'max_health': scaled_opponent['max_health'],
        'attack': scaled_opponent['attack'],
        'defense': scaled_opponent['defense'],
        'speed': scaled_opponent['speed']
    }
    
    # Store opponent in context for combat
    context.user_data['arena_opponent'] = opponent
    
    fight_text = f"""
⚔️ **Арена - Початок бою!**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ваш противник: **{opponent['name']}** ({class_config['name']})
Рівень: {opponent['level']}

👤 {char_data['name']}: {char_data['health']}/{char_data['max_health']} HP
🤖 {opponent['name']}: {opponent['health']}/{opponent['max_health']} HP

Що будете робити?
"""
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Атакувати", callback_data="arena_combat_attack")],
        [InlineKeyboardButton("🛡 Захищатися", callback_data="arena_combat_defend")],
        [InlineKeyboardButton("🏃 Втекти", callback_data="arena_combat_flee")]
    ]
    
    # Add potion button if available
    user_id = char_data['user_id']
    inventory = await db.get_inventory(user_id)
    if inventory and inventory.items:
        for item in inventory.items:
            if item.item_type == 'potion' and item.quantity > 0:
                from handlers.shop_handler import SHOP_ITEMS
                potion_info = None
                for category in SHOP_ITEMS.values():
                    if item.item_id in category:
                        potion_info = category[item.item_id]
                        break
                
                if potion_info and potion_info.get('usable_in_combat', False):
                    keyboard.append([InlineKeyboardButton("🧪 Використати зілля", callback_data="arena_combat_potion_menu")])
                    break
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        fight_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def process_arena_combat(update: Update, context: ContextTypes.DEFAULT_TYPE, character, action: str) -> None:
    """Process arena combat action"""
    
    char_data = await get_character_data(character)
    opponent = context.user_data.get('arena_opponent')
    
    if not opponent:
        await update.callback_query.answer("❌ Помилка бою!")
        return
    
    combat_text = ""
    
    if action == "attack":
        # Player attacks first if faster
        if char_data['speed'] >= opponent['speed']:
            # Player attacks - improved damage formula
            base_damage = max(char_data['attack'] * 0.8, char_data['attack'] - opponent['defense'] * 0.7)
            min_damage = max(1, char_data['attack'] * 0.15)
            variance = random.uniform(0.9, 1.1)
            damage = int(max(min_damage, base_damage * variance))
            
            # Debug logging
            logger.info(f"Arena combat - Player attack: base_damage={base_damage}, min_damage={min_damage}, final_damage={damage}")
            logger.info(f"Player stats: attack={char_data['attack']}, opponent defense={opponent['defense']}")
            
            opponent['health'] -= damage
            combat_text += f"⚔️ Ви завдали {damage} шкоди!\n"
            
            # Check if opponent is defeated
            if opponent['health'] <= 0:
                await handle_arena_victory(update, context, character, opponent)
                return
            
            # Opponent attacks back - improved damage formula
            base_damage = max(opponent['attack'] * 0.8, opponent['attack'] - char_data['defense'] * 0.7)
            min_damage = max(1, opponent['attack'] * 0.15)
            variance = random.uniform(0.9, 1.1)
            opponent_damage = int(max(min_damage, base_damage * variance))
            
            # Update both character object and database
            character.health -= opponent_damage
            char_data['health'] = character.health
            combat_text += f"💥 {opponent['name']} завдав вам {opponent_damage} шкоди!\n"
        else:
            # Opponent attacks first - improved damage formula
            base_damage = max(opponent['attack'] * 0.8, opponent['attack'] - char_data['defense'] * 0.7)
            min_damage = max(1, opponent['attack'] * 0.15)
            variance = random.uniform(0.9, 1.1)
            opponent_damage = int(max(min_damage, base_damage * variance))
            
            # Update both character object and database
            character.health -= opponent_damage
            char_data['health'] = character.health
            combat_text += f"💥 {opponent['name']} завдав вам {opponent_damage} шкоди!\n"
            
            # Check if player is defeated
            if char_data['health'] <= 0:
                await handle_arena_defeat(update, context, character)
                return
            
            # Player attacks back - improved damage formula
            base_damage = max(char_data['attack'] * 0.8, char_data['attack'] - opponent['defense'] * 0.7)
            min_damage = max(1, char_data['attack'] * 0.15)
            variance = random.uniform(0.9, 1.1)
            damage = int(max(min_damage, base_damage * variance))
            
            # Debug logging
            logger.info(f"Arena combat - Player counter-attack: base_damage={base_damage}, min_damage={min_damage}, final_damage={damage}")
            logger.info(f"Player stats: attack={char_data['attack']}, opponent defense={opponent['defense']}")
            
            opponent['health'] -= damage
            combat_text += f"⚔️ Ви завдали {damage} шкоди!\n"
            
            # Check if opponent is defeated
            if opponent['health'] <= 0:
                await handle_arena_victory(update, context, character, opponent)
                return
        
        # Update character health
        await db.update_character_by_id(char_data['user_id'], {'health': char_data['health']})
        
        # Check if player is defeated after counter-attack
        if char_data['health'] <= 0:
            await handle_arena_defeat(update, context, character)
            return
    
    elif action == "defend":
        combat_text += "🛡 Ви зайняли оборонну позицію!\n"
        
        # Opponent attacks with reduced damage - improved damage formula
        reduced_attack = opponent['attack'] // 2
        base_damage = max(reduced_attack * 0.8, reduced_attack - char_data['defense'] * 1.4)  # Extra defense bonus
        min_damage = max(0, reduced_attack * 0.1)
        variance = random.uniform(0.9, 1.1)
        opponent_damage = int(max(min_damage, base_damage * variance))
        
        # Update both character object and database
        character.health -= opponent_damage
        char_data['health'] = character.health
        combat_text += f"💥 {opponent['name']} завдав вам {opponent_damage} шкоди (блоковано)!\n"
        
        await db.update_character_by_id(char_data['user_id'], {'health': char_data['health']})
        
        # Check if player is defeated
        if char_data['health'] <= 0:
            await handle_arena_defeat(update, context, character)
            return
    
    elif action == "flee":
        await handle_arena_flee(update, context, character)
        return
    
    # Continue combat with turn counter for uniqueness
    arena_turn = context.user_data.get('arena_turn', 0) + 1
    context.user_data['arena_turn'] = arena_turn
    
    fight_text = f"""
⚔️ **Арена - Бій триває!** (Хід {arena_turn})
━━━━━━━━━━━━━━━━━━━━━━━━━
{combat_text}

👤 {char_data['name']}: {char_data['health']}/{char_data['max_health']} HP
🤖 {opponent['name']}: {opponent['health']}/{opponent['max_health']} HP

Що будете робити далі?
"""
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Атакувати", callback_data="arena_combat_attack")],
        [InlineKeyboardButton("🛡 Захищатися", callback_data="arena_combat_defend")],
        [InlineKeyboardButton("🏃 Втекти", callback_data="arena_combat_flee")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        fight_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_arena_victory(update: Update, context: ContextTypes.DEFAULT_TYPE, character, opponent: dict) -> None:
    """Handle arena victory"""
    
    char_data = await get_character_data(character)
    
    # Calculate rewards (reduced for better balance)
    base_gold = random.randint(15, 35)  # Reduced from config values
    base_exp = random.randint(10, 25)   # Reduced from config values
    
    # Bonus for higher level opponent (also reduced)
    if opponent['level'] > char_data['level']:
        level_diff = opponent['level'] - char_data['level']
        base_gold += level_diff * 5   # Reduced from 10
        base_exp += level_diff * 8    # Reduced from 15
    
    # Get character object for level up system
    character_obj = await db.get_character(char_data['user_id'])
    if not character_obj:
        return
    
    # Update gold
    character_obj.gold += base_gold
    
    # Add experience with proper level up handling
    character_manager = CharacterManager(db)
    exp_result = character_manager.add_experience(character_obj, base_exp)
    
    # Update character in database
    await db.update_character(character_obj)
    
    await db.update_statistics_by_id(char_data['user_id'], {
        'arena_wins': 1,
        'enemies_killed': 1
    })
    
    # Update quest progress for arena champion and battle damage
    from handlers.daily_quests_handler import update_quest_progress, notify_quest_completion
    completed_quests_arena = await update_quest_progress(char_data['user_id'], 'arena', 1)
    completed_quests_damage = await update_quest_progress(char_data['user_id'], 'damage', random.randint(20, 35))
    completed_quests = completed_quests_arena + completed_quests_damage
    quest_text = await notify_quest_completion(update, context, completed_quests)
    
    victory_text = f"""
🏆 **ПЕРЕМОГА В АРЕНІ!**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви перемогли {opponent['name']}!

🎁 Нагороди:
💰 Золото: +{base_gold}
⚡ Досвід: +{base_exp}

💚 Здоров'я: {character_obj.health}/{character_obj.max_health}
💰 Золото: {character_obj.gold}
{quest_text}"""

    # Add level up message if leveled up
    if exp_result['level_up']:
        victory_text += f"""
🎉 **ПІДВИЩЕННЯ РІВНЯ!**
📈 Рівень: {exp_result['old_level']} → {exp_result['new_level']}
💪 Ваші характеристики покращились!
"""
    
    victory_text += "\nВітаємо з перемогою!"
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Ще один бій", callback_data="arena_quick_fight")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Clear opponent data
    context.user_data.pop('arena_opponent', None)
    context.user_data.pop('arena_turn', None)
    
    await update.callback_query.edit_message_text(
        victory_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_arena_defeat(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Handle arena defeat"""
    
    char_data = await get_character_data(character)
    
    # Set health to 25% of max
    char_data['health'] = max(1, char_data['max_health'] // 4)
    await db.update_character_by_id(char_data['user_id'], {'health': char_data['health']})
    
    await db.update_statistics_by_id(char_data['user_id'], {'arena_losses': 1})
    
    defeat_text = f"""
💀 **ПОРАЗКА В АРЕНІ**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви програли бій...

💚 Ви відновили трохи здоров'я: {char_data['health']}/{char_data['max_health']}

Не засмучуйтесь! Тренуйтесь і повертайтесь сильнішими!
"""
    
    keyboard = [
        [InlineKeyboardButton("🏥 Відпочити в таверні", callback_data="tavern_rest")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Clear opponent data
    context.user_data.pop('arena_opponent', None)
    context.user_data.pop('arena_turn', None)
    
    await update.callback_query.edit_message_text(
        defeat_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_arena_flee(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Handle fleeing from arena"""
    
    flee_text = """
🏃 **Втеча з арени**
━━━━━━━━━━━━━━━━━━━━━━━━━
Ви втекли з поля бою!

Іноді розсудливість важливіша за хоробрість.
"""
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Спробувати знову", callback_data="arena_quick_fight")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Clear opponent data
    context.user_data.pop('arena_opponent', None)
    context.user_data.pop('arena_turn', None)
    
    await update.callback_query.edit_message_text(
        flee_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_arena_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show arena rating/leaderboard"""
    
    rating_text = """
🏆 **Рейтинг Арени**
━━━━━━━━━━━━━━━━━━━━━━━━━
Топ-10 найкращих бійців:

🥇 Торвальд Громобій - 47 перемог
🥈 Елара Вогняна - 42 перемоги  
🥉 Грім Залізний - 38 перемог
4️⃣ Селена Місячна - 35 перемог
5️⃣ Арагорн Швидкий - 32 перемоги
6️⃣ Бьорн Ведмідь - 29 перемог
7️⃣ Ліра Стрілок - 26 перемог
8️⃣ Зорин Мудрець - 23 перемоги
9️⃣ Таліон Тінь - 20 перемог
🔟 Кейра Клинок - 18 перемог

💡 Продовжуйте битися, щоб потрапити в рейтинг!
"""
    
    keyboard = [
        [InlineKeyboardButton("⚔️ До арени", callback_data="tavern_arena")],
        [InlineKeyboardButton("🏛 До таверни", callback_data="tavern_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        rating_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_combat_potion_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, character) -> None:
    """Show available potions during arena combat"""
    
    if hasattr(character, 'user_id'):
        user_id = character.user_id
    else:
        user_id = character['user_id']
    
    inventory = await db.get_inventory(user_id)
    
    potion_text = """
🧪 **Бойові зілля на арені**
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
                        callback_data=f"arena_combat_use_potion_{item.item_id}"
                    )])
    
    if not keyboard:
        potion_text += "\n🔍 Немає доступних бойових зілль"
    
    keyboard.append([InlineKeyboardButton("🔙 Назад до бою", callback_data="arena_quick_fight")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        potion_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def use_combat_potion(update: Update, context: ContextTypes.DEFAULT_TYPE, character, potion_id: str) -> None:
    """Use a potion during arena combat"""
    
    # Simple implementation for arena - just apply effects and continue
    char_data = character.to_dict() if hasattr(character, 'to_dict') else character
    
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
    
    # Apply instant effects
    updates = {}
    effects_text = "🧪 Ви використали зілля в бою!\n"
    
    if 'health' in potion_info:
        new_health = min(char_data['max_health'], char_data['health'] + potion_info['health'])
        health_gained = new_health - char_data['health']
        updates['health'] = new_health
        effects_text += f"💚 Відновлено {health_gained} здоров'я\n"
    
    # Store temporary effects
    temp_effects = context.user_data.get('temp_effects', {})
    if 'attack_boost' in potion_info:
        temp_effects['attack_boost'] = {
            'value': potion_info['attack_boost'],
            'duration': potion_info.get('duration', 1)
        }
        effects_text += f"⚔️ Атака +{potion_info['attack_boost']} на {potion_info.get('duration', 1)} ходів\n"
    
    context.user_data['temp_effects'] = temp_effects
    
    # Update character and remove potion
    if updates:
        await db.update_character_by_id(char_data['user_id'], updates)
    await db.remove_item_from_inventory(char_data['user_id'], potion_id, 1)
    await db.update_statistics_by_id(char_data['user_id'], {'potions_used': 1})
    
    # Show effects message
    keyboard = [[InlineKeyboardButton("⚔️ Продовжити бій", callback_data="arena_quick_fight")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        f"🏟 **Арена**\n━━━━━━━━━━━━━━━━━━━━━━━━━\n{effects_text}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
