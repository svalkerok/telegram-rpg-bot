"""
ОНОВЛЕНИЙ DUNGEON HANDLER з інтегрованою системою балансу V2.0
Використовує покращену бойову систему для збалансованих боїв
"""

import logging
from typing import Dict, Any, Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from database.database_models import Character
from database.db_manager import DatabaseManager
from game_logic.character import CharacterManager
from game_logic.combat_v2 import CombatManager, CombatAction, CombatResult  # НОВА СИСТЕМА!
from game_logic.enemies import EnemyManager, EnemyType
from game_logic.items import ItemManager
from handlers.character_handler import character_required
import random

logger = logging.getLogger(__name__)

class BalancedDungeonHandler:
    """Оновлений обробник підземелля з збалансованою бойовою системою"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.character_manager = CharacterManager(self.db_manager)
        self.enemy_manager = EnemyManager()
        self.item_manager = ItemManager()
        self.combat_manager = CombatManager(self.character_manager, self.item_manager)  # НОВИЙ МЕНЕДЖЕР!
        
        # Рівні складності підземелля
        self.difficulty_levels = {
            1: 'dungeon_floor_1',   # 110% складності
            2: 'dungeon_floor_2',   # 125% складності  
            3: 'dungeon_floor_3'    # 140% складності
        }
        
        # Прогресія підземелля
        self.floor_progression = {
            1: {"enemies": 3, "boss": False, "min_level": 1},
            2: {"enemies": 4, "boss": False, "min_level": 3},
            3: {"enemies": 5, "boss": True, "min_level": 5}
        }
    
    @character_required
    async def dungeon_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, character: Character):
        """Показати меню підземелля з рекомендаціями складності"""
        
        # Розраховуємо силу персонажа для рекомендацій
        total_stats = self.character_manager.get_total_stats(character)
        player_power = self._calculate_player_power(total_stats, character.level)
        
        # Формуємо повідомлення з рекомендаціями
        text = "🏰 **ПІДЗЕМЕЛЛЯ ТІНЕЙ**\n\n"
        text += f"🧙 {character.name} (рівень {character.level})\n"
        text += f"💪 Бойова сила: {player_power}\n\n"
        
        text += "Оберіть поверх підземелля:\n\n"
        
        # Генеруємо кнопки з рекомендаціями  
        keyboard = []
        
        for floor, config in self.floor_progression.items():
            # Розраховуємо рекомендацію
            if character.level >= config["min_level"]:
                if character.level >= config["min_level"] + 3:
                    difficulty_emoji = "🟢"
                    difficulty_text = "Легко"
                elif character.level >= config["min_level"] + 1:
                    difficulty_emoji = "🟡"
                    difficulty_text = "Рекомендовано"
                else:
                    difficulty_emoji = "🟠"
                    difficulty_text = "Виклик"
            else:
                difficulty_emoji = "🔴"
                difficulty_text = "Небезпечно"
            
            button_text = f"{difficulty_emoji} Поверх {floor} ({difficulty_text})"
            keyboard.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"dungeon_floor_{floor}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text += "\n💡 **Підказка:** Зелений колір означає легкий бій, жовтий - збалансований, помаранчевий - складний, червоний - дуже небезпечно!"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    @character_required
    async def enter_dungeon_floor(self, update: Update, context: ContextTypes.DEFAULT_TYPE, character: Character):
        """Увійти на поверх підземелля"""
        
        query = update.callback_query
        floor = int(query.data.split('_')[-1])
        
        # Ініціалізуємо стан підземелля
        context.user_data['dungeon'] = {
            'floor': floor,
            'enemies_defeated': 0,
            'total_enemies': self.floor_progression[floor]['enemies'],
            'has_boss': self.floor_progression[floor]['boss'],
            'difficulty': self.difficulty_levels[floor]
        }
        
        text = f"🏰 **ПОВЕРХ {floor} ПІДЗЕМЕЛЛЯ**\n\n"
        text += "Ви входите в темні коридори підземелля...\n"
        text += "Десь попереду чується скрегіт кісток і рипіння старих механізмів.\n\n"
        
        if floor == 1:
            text += "💀 На цьому поверсі мешкають скелети та зомбі\n"
        elif floor == 2:
            text += "👹 Тут панують орки та темні лицарі\n"
        else:
            text += "☠️ Найглибший поверх. Тут править сам Ліч!\n"
        
        text += f"⚔️ Ворогів до битви: {self.floor_progression[floor]['enemies']}\n"
        
        if self.floor_progression[floor]['boss']:
            text += "👑 На цьому поверсі є БОС!\n"
        
        keyboard = [
            [InlineKeyboardButton("⚔️ Почати дослідження", callback_data="dungeon_explore")],
            [InlineKeyboardButton("🔙 Повернутися", callback_data="dungeon_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    @character_required  
    async def explore_dungeon(self, update: Update, context: ContextTypes.DEFAULT_TYPE, character: Character):
        """Дослідити підземелля та зустріти ворога"""
        
        query = update.callback_query
        dungeon_state = context.user_data.get('dungeon', {})
        
        if not dungeon_state:
            await self.dungeon_menu(update, context, character)
            return
        
        floor = dungeon_state['floor']
        difficulty = dungeon_state['difficulty']
        
        # Вибираємо ворога для поточного поверху
        if dungeon_state['enemies_defeated'] < dungeon_state['total_enemies']:
            # Звичайний ворог
            enemy = self.enemy_manager.get_random_enemy_for_location(
                EnemyType.DUNGEON, 
                character.level
            )
            
            if not enemy:
                # Fallback на скелета-воїна
                enemy = self.enemy_manager.get_enemy('skeleton_warrior')
            
            is_boss = False
            
        elif dungeon_state['has_boss'] and dungeon_state['enemies_defeated'] == dungeon_state['total_enemies']:
            # Бос поверху
            boss_enemies = ['death_knight', 'lich', 'dungeon_overlord']
            boss_id = boss_enemies[min(floor-1, len(boss_enemies)-1)]
            enemy = self.enemy_manager.get_enemy(boss_id)
            is_boss = True
            difficulty = 'boss'  # Боси складніші
            
        else:
            # Підземелля пройдено
            await self.complete_dungeon(update, context, character)
            return
        
        if not enemy:
            await query.edit_message_text("❌ Помилка: не вдалося створити ворога!")
            return
        
        # Масштабуємо ворога під гравця з новою системою балансу!
        try:
            scaled_enemy = self.combat_manager.balance_system.scale_enemy_for_player(
                enemy.to_dict(),
                character, 
                difficulty
            )
            
            # Формуємо повідомлення про зустріч
            encounter_text = self._generate_encounter_text(scaled_enemy, floor, is_boss)
            
            # Аналіз балансу для інформації
            total_stats = self.character_manager.get_total_stats(character)
            player_power = self.combat_manager.balance_system._calculate_player_power(total_stats, character.level)
            enemy_power = scaled_enemy.max_health + scaled_enemy.attack * 8 + scaled_enemy.defense * 6
            
            encounter_text += f"\n📊 **Аналіз бою:**\n"
            encounter_text += f"💪 Ваша сила: {player_power}\n"
            encounter_text += f"👹 Сила ворога: {enemy_power}\n"
            
            # Прогноз бою
            if player_power > enemy_power * 1.3:
                prediction = "🟢 Легка перемога"
            elif player_power > enemy_power:
                prediction = "🟡 Хороші шанси"
            elif player_power * 1.2 > enemy_power:
                prediction = "🟠 Рівний бій"
            else:
                prediction = "🔴 Складний бій"
            
            encounter_text += f"🎯 Прогноз: {prediction}\n"
            
            keyboard = [
                [InlineKeyboardButton("⚔️ Атакувати", callback_data="dungeon_combat_attack")],
                [InlineKeyboardButton("🛡️ Захищатися", callback_data="dungeon_combat_defend")],
                [InlineKeyboardButton("💨 Спробувати втекти", callback_data="dungeon_combat_flee")]
            ]
            
            # Додаємо магічну атаку якщо є магічна сила
            if total_stats.get('magic_power', 0) > 0:
                keyboard.insert(1, [InlineKeyboardButton("🔮 Магічна атака", callback_data="dungeon_combat_magic")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Зберігаємо ворога та стан бою
            context.user_data['combat'] = {
                'enemy': scaled_enemy,
                'is_boss': is_boss,
                'location': 'dungeon'
            }
            
            await query.edit_message_text(encounter_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error scaling enemy for player: {e}")
            # Fallback на стандартну систему
            await self._fallback_combat(query, character, enemy, is_boss)
    
    def _generate_encounter_text(self, enemy, floor: int, is_boss: bool) -> str:
        """Генерує текст зустрічі з ворогом"""
        
        if is_boss:
            text = f"👑 **БОС ПОВЕРХУ {floor}!**\n\n"
            text += f"{enemy.emoji} **{enemy.name}**\n"
            text += f"_{enemy.description}_\n\n"
            text += "Повелитель цього поверху блокує вам шлях!\n"
            text += "Це буде епічна битва!\n\n"
        else:
            encounter_scenarios = [
                "Ви чуєте кроки в темряві...",
                "З-за кута виринає постать...", 
                "Раптово щось атакує вас!",
                "Перед вами з'являється ворог!",
                "Ви потрапляєте в засідку!"
            ]
            
            text = f"🏰 **ПОВЕРХ {floor} - ЗУСТРІЧ!**\n\n"
            text += f"{random.choice(encounter_scenarios)}\n\n"
            text += f"{enemy.emoji} **{enemy.name}**\n"
            text += f"_{enemy.description}_\n\n"
        
        # Характеристики ворога (збалансовані)
        text += f"📊 **Характеристики:**\n"
        text += f"⭐ Рівень: {enemy.level}\n"
        text += f"❤️ Здоров'я: {enemy.max_health}\n"
        text += f"⚔️ Атака: {enemy.attack}\n"
        text += f"🛡️ Захист: {enemy.defense}\n"
        
        return text
    
    @character_required
    async def process_combat_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, character: Character):
        """Обробити дію в бою з використанням нової системи"""
        
        query = update.callback_query
        combat_state = context.user_data.get('combat', {})
        
        if not combat_state:
            await self.dungeon_menu(update, context, character)
            return
        
        # Визначаємо дію
        action_map = {
            'dungeon_combat_attack': CombatAction.ATTACK,
            'dungeon_combat_defend': CombatAction.DEFEND, 
            'dungeon_combat_magic': CombatAction.MAGIC_ATTACK,
            'dungeon_combat_flee': CombatAction.FLEE
        }
        
        action = action_map.get(query.data, CombatAction.ATTACK)
        enemy = combat_state['enemy']
        
        try:
            # Запускаємо новий збалансований бій!
            dungeon_difficulty = context.user_data['dungeon'].get('difficulty', 'dungeon_floor_1')
            
            combat_result = await self.combat_manager.start_combat(
                character, 
                enemy, 
                auto_combat=False,
                location_difficulty=dungeon_difficulty
            )
            
            if combat_result['result'] == CombatResult.ONGOING:
                # Обробляємо дію гравця
                turn_result = await self.combat_manager.process_player_action(
                    combat_result['state'], 
                    action
                )
                
                # Формуємо повідомлення про хід
                combat_text = self._format_combat_turn(turn_result, character, enemy)
                
                if turn_result['result'] == CombatResult.ONGOING:
                    # Бій триває
                    keyboard = self._get_combat_keyboard(character)
                    await query.edit_message_text(combat_text, reply_markup=keyboard, parse_mode='Markdown')
                    
                    # Оновлюємо стан
                    context.user_data['combat']['state'] = turn_result['state']
                else:
                    # Бій завершено
                    await self._handle_combat_end(query, context, character, turn_result)
            else:
                # Бій завершено одразу (втеча)
                await self._handle_combat_end(query, context, character, combat_result)
                
        except Exception as e:
            logger.error(f"Combat processing error: {e}")
            await query.edit_message_text(
                "❌ Помилка в бойовій системі. Повертаємося в підземелля...",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏰 Підземелля", callback_data="dungeon_menu")]])
            )
    
    def _format_combat_turn(self, turn_result: Dict[str, Any], character: Character, enemy) -> str:
        """Форматує результат ходу бою"""
        
        text = f"⚔️ **БІЙ ТРИВАЄ!**\n\n"
        
        # Повідомлення про останні ходи
        if 'last_turns' in turn_result:
            for turn in turn_result['last_turns']:
                text += f"{turn.message}\n"
        
        text += f"\n📊 **Стан учасників:**\n"
        text += f"👤 {character.name}: {character.health}/{character.max_health} HP\n"
        text += f"{enemy.emoji} {enemy.name}: {enemy.health}/{enemy.max_health} HP\n\n"
        
        # Смугки здоров'я
        char_hp_percent = character.health / character.max_health
        enemy_hp_percent = enemy.health / enemy.max_health
        
        char_bar = self._create_health_bar(char_hp_percent)
        enemy_bar = self._create_health_bar(enemy_hp_percent)
        
        text += f"👤 {char_bar} {character.health} HP\n"
        text += f"{enemy.emoji} {enemy_bar} {enemy.health} HP\n"
        
        return text
    
    def _create_health_bar(self, percentage: float, length: int = 10) -> str:
        """Створює візуальну смугу здоров'я"""
        filled = int(percentage * length)
        empty = length - filled
        
        if percentage > 0.6:
            bar_char = "🟩"
        elif percentage > 0.3:
            bar_char = "🟨" 
        else:
            bar_char = "🟥"
            
        return bar_char * filled + "⬜" * empty
    
    def _get_combat_keyboard(self, character: Character) -> InlineKeyboardMarkup:
        """Генерує клавіатуру для бою"""
        
        total_stats = self.character_manager.get_total_stats(character)
        
        keyboard = [
            [InlineKeyboardButton("⚔️ Атакувати", callback_data="dungeon_combat_attack")],
            [InlineKeyboardButton("🛡️ Захищатися", callback_data="dungeon_combat_defend")]
        ]
        
        # Додаємо магічну атаку якщо є магічна сила
        if total_stats.get('magic_power', 0) > 0:
            keyboard.insert(1, [InlineKeyboardButton("🔮 Магічна атака", callback_data="dungeon_combat_magic")])
        
        keyboard.append([InlineKeyboardButton("💨 Втекти", callback_data="dungeon_combat_flee")])
        
        return InlineKeyboardMarkup(keyboard)
    
    async def _handle_combat_end(self, query, context, character: Character, combat_result: Dict[str, Any]):
        """Обробити завершення бою"""
        
        result_type = combat_result['result']
        
        if result_type == CombatResult.VICTORY:
            # Перемога!
            dungeon_state = context.user_data['dungeon']
            dungeon_state['enemies_defeated'] += 1
            
            text = "🎉 **ПЕРЕМОГА!**\n\n"
            text += f"⭐ Отримано досвіду: {combat_result['experience_gained']}\n"
            text += f"💰 Отримано золота: {combat_result['gold_gained']}\n"
            
            if combat_result.get('level_up'):
                text += f"\n🎊 **ПІДВИЩЕННЯ РІВНЯ!** Тепер {combat_result['new_level']} рівень!\n"
            
            if combat_result['items_dropped']:
                text += "\n🎁 **Знайдені предмети:**\n"
                for item_id in combat_result['items_dropped']:
                    text += f"• {item_id}\n"
            
            # Прогрес підземелля
            remaining = dungeon_state['total_enemies'] - dungeon_state['enemies_defeated']
            if remaining > 0:
                text += f"\n🏰 Залишилося ворогів: {remaining}"
                if dungeon_state['has_boss'] and remaining == 0:
                    text += " + БОС"
            
            keyboard = []
            if remaining > 0 or (dungeon_state['has_boss'] and dungeon_state['enemies_defeated'] == dungeon_state['total_enemies']):
                keyboard.append([InlineKeyboardButton("⚔️ Продовжити дослідження", callback_data="dungeon_explore")])
            else:
                keyboard.append([InlineKeyboardButton("🎊 Завершити підземелля", callback_data="dungeon_complete")])
            
            keyboard.append([InlineKeyboardButton("🚪 Вийти з підземелля", callback_data="dungeon_menu")])
            
        elif result_type == CombatResult.DEFEAT:
            # Поразка
            character.health = 1  # Залишаємо 1 HP замість смерті
            text = "💀 **ПОРАЗКА!**\n\n"
            text += "Ви були переможені, але встигли втекти...\n"
            text += "Здоров'я відновлено до 1 HP.\n\n"
            text += "💡 Спробуйте покращити спорядження та повертайтеся!"
            
            keyboard = [
                [InlineKeyboardButton("🏰 Повернутися в підземелля", callback_data="dungeon_menu")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
            ]
            
        else:  # FLEE_SUCCESS
            # Успішна втеча
            text = "💨 **ВТЕЧА ВДАЛАСЯ!**\n\n"
            text += "Ви успішно втекли з бою.\n"
            text += "Іноді відступ - найкраща стратегія."
            
            keyboard = [
                [InlineKeyboardButton("⚔️ Продовжити дослідження", callback_data="dungeon_explore")],
                [InlineKeyboardButton("🚪 Вийти з підземелля", callback_data="dungeon_menu")]
            ]
        
        # Очищаємо стан бою
        if 'combat' in context.user_data:
            del context.user_data['combat']
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def complete_dungeon(self, update: Update, context: ContextTypes.DEFAULT_TYPE, character: Character):
        """Завершити підземелля"""
        
        query = update.callback_query
        dungeon_state = context.user_data.get('dungeon', {})
        floor = dungeon_state.get('floor', 1)
        
        # Бонусна винагорода за завершення поверху
        bonus_exp = floor * 50
        bonus_gold = floor * 25
        
        character.experience += bonus_exp
        character.gold += bonus_gold
        
        text = f"🎊 **ПОВЕРХ {floor} ЗАВЕРШЕНО!**\n\n"
        text += "Ви успішно очистили цей поверх підземелля!\n\n"
        text += f"🎁 **Бонусна винагорода:**\n"
        text += f"⭐ Досвід: +{bonus_exp}\n"
        text += f"💰 Золото: +{bonus_gold}\n\n"
        
        if floor < 3:
            text += f"🔓 Відкрито доступ до поверху {floor + 1}!\n"
        else:
            text += "🏆 Ви повністю очистили підземелля! Вітаємо!"
        
        keyboard = [
            [InlineKeyboardButton("🏰 Повернутися в підземелля", callback_data="dungeon_menu")],
            [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ]
        
        # Очищаємо стан підземелля
        if 'dungeon' in context.user_data:
            del context.user_data['dungeon']
        
        # Зберігаємо персонажа
        self.character_manager.save_character(character)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    def _calculate_player_power(self, player_stats: Dict, level: int) -> int:
        """Розраховує загальну бойову силу гравця (дублює з balance_system)"""
        
        attack = player_stats.get('attack', 10)
        defense = player_stats.get('defense', 5)
        max_health = player_stats.get('max_health', 100)
        speed = player_stats.get('speed', 10)
        crit_chance = player_stats.get('critical_chance', 5)
        
        power = (
            level * 20 +
            attack * 8 +
            defense * 6 +
            max_health * 0.4 +
            speed * 2 +
            crit_chance * 3
        )
        
        return int(power)
    
    async def _fallback_combat(self, query, character: Character, enemy, is_boss: bool):
        """Запасний варіант бою якщо нова система не працює"""
        
        text = f"⚠️ Використовується запасна бойова система\n\n"
        text += f"{enemy.emoji} **{enemy.name}**\n"
        text += f"❤️ Здоров'я: {enemy.max_health}\n"
        text += f"⚔️ Атака: {enemy.attack}\n\n"
        text += "Виберіть дію:"
        
        keyboard = [
            [InlineKeyboardButton("⚔️ Атакувати", callback_data="dungeon_explore")],
            [InlineKeyboardButton("🚪 Повернутися", callback_data="dungeon_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


# Ініціалізація обробника
balanced_dungeon_handler = BalancedDungeonHandler()
