"""
ПОКРАЩЕНА БОЙОВА СИСТЕМА V2.0 з інтегрованим балансом
Telegram RPG Bot "Легенди Валгаллії"
"""

import random
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from database.database_models import Character
from game_logic.character import CharacterManager
from game_logic.items import ItemType
from game_logic.enemies import Enemy, EnemyAbilities

logger = logging.getLogger(__name__)


class CombatAction(Enum):
    """Available combat actions"""
    ATTACK = "attack"
    DEFEND = "defend" 
    MAGIC_ATTACK = "magic_attack"
    USE_ITEM = "use_item"
    FLEE = "flee"
    SPECIAL_ABILITY = "special_ability"


class CombatResult(Enum):
    """Combat outcomes"""
    VICTORY = "victory"
    DEFEAT = "defeat"
    FLEE_SUCCESS = "flee_success"
    FLEE_FAILED = "flee_failed"
    ONGOING = "ongoing"


@dataclass
class CombatTurn:
    """Data for a single combat turn"""
    actor_name: str
    action: CombatAction
    target_name: str
    damage_dealt: int = 0
    damage_taken: int = 0
    is_critical: bool = False
    is_blocked: bool = False
    is_missed: bool = False
    special_effect: str = ""
    message: str = ""


@dataclass
class CombatState:
    """Current state of combat"""
    character: Character
    enemy: Enemy
    turn_number: int = 0
    character_effects: Dict[str, Dict] = None
    enemy_effects: Dict[str, Dict] = None
    combat_log: List[CombatTurn] = None
    
    def __post_init__(self):
        if self.character_effects is None:
            self.character_effects = {}
        if self.enemy_effects is None:
            self.enemy_effects = {}
        if self.combat_log is None:
            self.combat_log = []


class BalancedCombatSystem:
    """Покращена збалансована бойова система"""
    
    def __init__(self):
        # Нова збалансована формула урону
        self.damage_config = {
            'base_multiplier': 0.85,
            'defense_efficiency': 0.6, 
            'minimum_damage_ratio': 0.2,
            'maximum_damage_reduction': 0.8,
            'variance': 0.15,
            'critical_multiplier': 1.75,
            'magic_defense_penetration': 0.5
        }
        
        # Константи бою
        self.FLEE_BASE_CHANCE = 0.5
    
    def calculate_balanced_damage(self, attacker_power: int, defender_defense: int, 
                                is_critical: bool = False, is_magic: bool = False) -> int:
        """Нова збалансована формула розрахунку урону"""
        
        # Магія ігнорує частину захисту
        if is_magic:
            effective_defense = defender_defense * self.damage_config['magic_defense_penetration']
        else:
            effective_defense = defender_defense
        
        # Основна формула
        base_damage = (attacker_power * self.damage_config['base_multiplier'] - 
                      effective_defense * self.damage_config['defense_efficiency'])
        
        # Мінімальний урон (завжди проходить певний відсоток)
        minimum_damage = attacker_power * self.damage_config['minimum_damage_ratio']
        
        # Застосовуємо мінімум
        final_damage = max(base_damage, minimum_damage)
        
        # Максимальне зменшення урону
        max_reduced_damage = attacker_power * (1 - self.damage_config['maximum_damage_reduction'])
        final_damage = max(final_damage, max_reduced_damage)
        
        # Варіативність
        variance = random.uniform(1 - self.damage_config['variance'], 
                                1 + self.damage_config['variance'])
        final_damage *= variance
        
        # Критичний урон  
        if is_critical:
            final_damage *= self.damage_config['critical_multiplier']
        
        return max(1, int(final_damage))
    
    def scale_enemy_for_player(self, base_enemy: Dict, character: Character, 
                             location_difficulty: str = 'dungeon_floor_1') -> Enemy:
        """Масштабує ворога під конкретного гравця для збалансованого бою"""
        
        # Отримуємо характеристики гравця
        from game_logic.character import CharacterManager
        char_manager = CharacterManager(None)
        player_stats = char_manager.get_total_stats(character)
        
        # Розраховуємо силу гравця
        player_power = self._calculate_player_power(player_stats, character.level)
        
        # Множники складності локацій
        location_multipliers = {
            'forest_easy': 0.8,
            'forest_normal': 1.0,
            'dungeon_floor_1': 1.1,
            'dungeon_floor_2': 1.25, 
            'dungeon_floor_3': 1.4,
            'arena': 1.3,
            'boss': 1.8
        }
        
        location_mult = location_multipliers.get(location_difficulty, 1.1)
        
        # Цільова сила ворога (85% від сили гравця з модифікатором локації)
        target_enemy_power = player_power * 0.85 * location_mult
        
        # Рівень ворога
        enemy_level = max(1, character.level + random.randint(-1, 1))
        
        # Створюємо збалансованого ворога
        scaled_enemy = Enemy(
            enemy_id=base_enemy.get('enemy_id', 'scaled_enemy'),
            name=base_enemy.get('name', 'Масштабований ворог'),
            description=base_enemy.get('description', ''),
            level=enemy_level,
            enemy_type=base_enemy.get('enemy_type', 'dungeon'),
            behavior=base_enemy.get('behavior', 'balanced'),
            
            # Розподіляємо силу по характеристиках
            max_health=int(target_enemy_power * 0.35),
            attack=int(target_enemy_power * 0.4),
            defense=int(target_enemy_power * 0.25),
            
            # Інші характеристики
            speed=base_enemy.get('speed', 10) + enemy_level,
            critical_chance=base_enemy.get('critical_chance', 5),
            block_chance=base_enemy.get('block_chance', 10),
            
            # Спеціальні здібності та опір
            special_abilities=base_enemy.get('special_abilities', []),
            magic_resistance=base_enemy.get('magic_resistance', 0),
            physical_resistance=base_enemy.get('physical_resistance', 0),
            
            # Винагороди
            experience_reward=self._calculate_experience_reward(enemy_level, character.level, location_mult),
            gold_min=int(enemy_level * 12 * location_mult * 0.8),
            gold_max=int(enemy_level * 12 * location_mult * 1.2),
            drop_table=base_enemy.get('drop_table', []),
            emoji=base_enemy.get('emoji', '👹')
        )
        
        # Корекція для різних типів ворогів
        behavior = base_enemy.get('behavior', 'balanced')
        
        if behavior == 'aggressive':
            scaled_enemy.attack = int(scaled_enemy.attack * 1.2)
            scaled_enemy.defense = int(scaled_enemy.defense * 0.85)
            scaled_enemy.max_health = int(scaled_enemy.max_health * 0.85)
        elif behavior == 'defensive':
            scaled_enemy.defense = int(scaled_enemy.defense * 1.2)
            scaled_enemy.max_health = int(scaled_enemy.max_health * 1.2)
            scaled_enemy.attack = int(scaled_enemy.attack * 0.85)
        elif behavior == 'berserker':
            scaled_enemy.attack = int(scaled_enemy.attack * 1.3)
            scaled_enemy.defense = int(scaled_enemy.defense * 0.8)
        
        # Мінімальні значення
        scaled_enemy.max_health = max(20, scaled_enemy.max_health)
        scaled_enemy.attack = max(5, scaled_enemy.attack)
        scaled_enemy.defense = max(1, scaled_enemy.defense)
        scaled_enemy.health = scaled_enemy.max_health
        
        logger.info(f"Scaled enemy {scaled_enemy.name} for player level {character.level}: "
                   f"HP={scaled_enemy.max_health}, ATK={scaled_enemy.attack}, DEF={scaled_enemy.defense}")
        
        return scaled_enemy
    
    def _calculate_player_power(self, player_stats: Dict, level: int) -> int:
        """Розраховує загальну бойову силу гравця"""
        
        attack = player_stats.get('attack', 10)
        defense = player_stats.get('defense', 5)
        max_health = player_stats.get('max_health', 100) 
        speed = player_stats.get('speed', 10)
        crit_chance = player_stats.get('critical_chance', 5)
        
        power = (
            level * 20 +           # Базова сила від рівня
            attack * 8 +           # Атака дуже важлива
            defense * 6 +          # Захист важливий  
            max_health * 0.4 +     # Здоров'я
            speed * 2 +            # Швидкість
            crit_chance * 3        # Критичний шанс
        )
        
        return int(power)
    
    def _calculate_experience_reward(self, enemy_level: int, player_level: int, 
                                   difficulty_mult: float) -> int:
        """Розраховує досвід з урахуванням різниці рівнів"""
        base_exp = enemy_level * 25
        
        level_diff = enemy_level - player_level
        if level_diff <= -2:
            level_mult = 0.5
        elif level_diff <= 0:
            level_mult = 0.8
        elif level_diff <= 2:
            level_mult = 1.0
        else:
            level_mult = 1.2
        
        return int(base_exp * level_mult * difficulty_mult)


class CombatManager:
    """Покращений менеджер бойової системи з балансом"""
    
    def __init__(self, character_manager: CharacterManager = None, item_manager = None):
        self.character_manager = character_manager or CharacterManager(None)
        self._item_manager = item_manager
        self._enemy_manager = None
        self.balance_system = BalancedCombatSystem()
        
        # Константи бою
        self.FLEE_BASE_CHANCE = 0.5
    
    @property
    def item_manager(self):
        """Lazy initialization of ItemManager"""
        if self._item_manager is None:
            from game_logic.items import ItemManager
            self._item_manager = ItemManager()
        return self._item_manager
    
    @property  
    def enemy_manager(self):
        """Lazy initialization of EnemyManager"""
        if self._enemy_manager is None:
            from game_logic.enemies import EnemyManager
            self._enemy_manager = EnemyManager()
        return self._enemy_manager
    
    async def start_combat(self, character: Character, enemy: Enemy, 
                          auto_combat: bool = False, location_difficulty: str = 'dungeon_floor_1') -> Dict[str, Any]:
        """Розпочати збалансований бій"""
        
        # Масштабуємо ворога під гравця для збалансованого бою
        if hasattr(enemy, 'enemy_id'):
            base_enemy_data = {
                'enemy_id': enemy.enemy_id,
                'name': enemy.name, 
                'description': enemy.description,
                'enemy_type': enemy.enemy_type.value if hasattr(enemy.enemy_type, 'value') else 'dungeon',
                'behavior': enemy.behavior.value if hasattr(enemy.behavior, 'value') else 'balanced',
                'speed': enemy.speed,
                'critical_chance': enemy.critical_chance,
                'block_chance': enemy.block_chance,
                'special_abilities': enemy.special_abilities,
                'magic_resistance': enemy.magic_resistance,
                'physical_resistance': enemy.physical_resistance,
                'drop_table': enemy.drop_table,
                'emoji': enemy.emoji
            }
            
            balanced_enemy = self.balance_system.scale_enemy_for_player(
                base_enemy_data, character, location_difficulty
            )
        else:
            balanced_enemy = enemy
        
        # Ініціалізуємо стан бою
        combat_state = CombatState(character, balanced_enemy)
        
        logger.info(f"Balanced combat started: {character.name} vs {balanced_enemy.name}")
        
        # Цикл бою
        while True:
            combat_state.turn_number += 1
            
            # Перевіряємо умови завершення бою
            if not character.is_alive():
                return self._end_combat(combat_state, CombatResult.DEFEAT)
            
            if not balanced_enemy.is_alive():
                return self._end_combat(combat_state, CombatResult.VICTORY)
            
            # Запобігаємо безкінечному бою
            if combat_state.turn_number > 50:
                logger.warning(f"Combat timeout after {combat_state.turn_number} turns")
                return self._end_combat(combat_state, CombatResult.DEFEAT)
            
            # Обробляємо ефекти ходу
            self._process_turn_effects(combat_state)
            
            # Визначаємо порядок ходів по швидкості
            char_stats = self.character_manager.get_total_stats(character)
            char_speed = char_stats['speed']
            enemy_speed = balanced_enemy.speed
            
            if auto_combat:
                # Автоматичний бій
                if char_speed >= enemy_speed:
                    await self._player_auto_turn(combat_state)
                    if balanced_enemy.is_alive():
                        await self._enemy_turn(combat_state)
                else:
                    await self._enemy_turn(combat_state)
                    if character.is_alive():
                        await self._player_auto_turn(combat_state)
            else:
                # Ручний бій - повертаємо стан для вводу гравця
                combat_state.next_actor = 'player' if char_speed >= enemy_speed else 'enemy'
                return {
                    'result': CombatResult.ONGOING,
                    'state': combat_state,
                    'next_turn': combat_state.next_actor,
                    'options': self._get_combat_options(combat_state)
                }
    
    async def process_player_action(self, combat_state: CombatState, action: CombatAction, 
                                  target: str = None, item_id: str = None) -> Dict[str, Any]:
        """Обробити дію гравця"""
        
        if action == CombatAction.ATTACK:
            turn = await self._player_attack(combat_state, False)
        elif action == CombatAction.MAGIC_ATTACK:
            turn = await self._player_attack(combat_state, True)
        elif action == CombatAction.DEFEND:
            turn = await self._player_defend(combat_state)
        elif action == CombatAction.USE_ITEM:
            turn = await self._player_use_item(combat_state, item_id)
        elif action == CombatAction.FLEE:
            return await self._player_flee(combat_state)
        else:
            turn = CombatTurn("", CombatAction.ATTACK, "", message="Невідома дія!")
        
        combat_state.combat_log.append(turn)
        
        # Хід ворога, якщо він ще живий
        if combat_state.enemy.is_alive() and combat_state.character.is_alive():
            enemy_turn = await self._enemy_turn(combat_state)
            combat_state.combat_log.append(enemy_turn)
        
        # Перевіряємо завершення бою
        if not combat_state.character.is_alive():
            return self._end_combat(combat_state, CombatResult.DEFEAT)
        elif not combat_state.enemy.is_alive():
            return self._end_combat(combat_state, CombatResult.VICTORY)
        
        # Продовжуємо бій
        return {
            'result': CombatResult.ONGOING,
            'state': combat_state,
            'last_turns': combat_state.combat_log[-2:],
            'options': self._get_combat_options(combat_state)
        }
    
    async def _player_attack(self, combat_state: CombatState, is_magic_attack: bool = False) -> CombatTurn:
        """Обробити атаку гравця з новою формулою урону"""
        character = combat_state.character
        enemy = combat_state.enemy
        
        # Отримуємо загальні характеристики персонажа
        total_stats = self.character_manager.get_total_stats(character)
        
        # Визначаємо силу атаки
        if is_magic_attack and total_stats['magic_power'] > 0:
            attack_power = total_stats['magic_power']
            action_type = CombatAction.MAGIC_ATTACK
        else:
            attack_power = total_stats['attack']
            action_type = CombatAction.ATTACK
            is_magic_attack = False
        
        # Перевіряємо критичний удар
        crit_chance = total_stats['critical_chance']
        is_critical = random.randint(1, 100) <= crit_chance
        
        # Розраховуємо урон за новою формулою
        damage = self.balance_system.calculate_balanced_damage(
            attack_power, enemy.defense, is_critical, is_magic_attack
        )
        
        # Застосовуємо урон до ворога
        actual_damage = enemy.take_damage(damage, "magic" if is_magic_attack else "physical")
        
        # Створюємо запис ходу
        turn = CombatTurn(
            actor_name=character.name,
            action=action_type,
            target_name=enemy.name,
            damage_dealt=actual_damage,
            is_critical=is_critical
        )
        
        # Генеруємо повідомлення
        if is_critical:
            turn.message = f"💥 **КРИТИЧНИЙ УДАР!** {character.name} завдає {actual_damage} урону!"
        elif is_magic_attack:
            turn.message = f"🔮 {character.name} використовує магічну атаку та завдає {actual_damage} урону!"
        else:
            turn.message = f"⚔️ {character.name} атакує та завдає {actual_damage} урону!"
        
        return turn
    
    async def _player_defend(self, combat_state: CombatState) -> CombatTurn:
        """Обробити захист гравця"""
        character = combat_state.character
        
        # Додаємо тимчасовий бонус до захисту
        self._add_effect(combat_state.character_effects, 'defense_stance', {
            'type': 'defense_bonus',
            'value': 10,
            'duration': 1
        })
        
        return CombatTurn(
            actor_name=character.name,
            action=CombatAction.DEFEND,
            target_name=character.name,
            message=f"🛡️ {character.name} займає оборонну позицію (+10 захисту до наступного ходу)!"
        )
    
    async def _player_use_item(self, combat_state: CombatState, item_id: str) -> CombatTurn:
        """Обробити використання предмета"""
        character = combat_state.character
        
        if not item_id:
            return CombatTurn(
                actor_name=character.name,
                action=CombatAction.USE_ITEM,
                target_name=character.name,
                message="❌ Предмет не вказано!"
            )
        
        # Використовуємо предмет
        result = self.character_manager.use_consumable_item(character, item_id)
        
        return CombatTurn(
            actor_name=character.name,
            action=CombatAction.USE_ITEM,
            target_name=character.name,
            message=result[1] if result[0] else f"❌ Не вдалося використати предмет: {result[1]}"
        )
    
    async def _player_flee(self, combat_state: CombatState) -> Dict[str, Any]:
        """Обробити спробу втечі"""
        character = combat_state.character
        enemy = combat_state.enemy
        
        total_stats = self.character_manager.get_total_stats(character)
        char_speed = total_stats['speed']
        
        # Розраховуємо шанс втечі
        flee_chance = self._calculate_flee_chance(char_speed, enemy.speed)
        success = random.random() < flee_chance
        
        turn = CombatTurn(
            actor_name=character.name,
            action=CombatAction.FLEE,
            target_name="",
            message=f"💨 {character.name} намагається втекти..."
        )
        
        combat_state.combat_log.append(turn)
        
        if success:
            return self._end_combat(combat_state, CombatResult.FLEE_SUCCESS)
        else:
            turn.message += " але не вдається втекти!"
            enemy_turn = await self._enemy_turn(combat_state)
            combat_state.combat_log.append(enemy_turn)
            
            if not character.is_alive():
                return self._end_combat(combat_state, CombatResult.DEFEAT)
            
            return {
                'result': CombatResult.ONGOING,
                'state': combat_state,
                'flee_failed': True,
                'options': self._get_combat_options(combat_state)
            }
    
    async def _player_auto_turn(self, combat_state: CombatState) -> CombatTurn:
        """Автоматичний хід гравця для симуляцій"""
        character = combat_state.character
        total_stats = self.character_manager.get_total_stats(character)
        
        if total_stats['magic_power'] > total_stats['attack']:
            return await self._player_attack(combat_state, True)
        else:
            return await self._player_attack(combat_state, False)
    
    async def _enemy_turn(self, combat_state: CombatState) -> CombatTurn:
        """Обробити хід ворога"""
        character = combat_state.character
        enemy = combat_state.enemy
        
        # Перевіряємо чи повинен ворог використати спеціальну здібність
        if enemy.special_abilities and enemy.should_use_ability():
            return await self._enemy_special_ability(combat_state)
        
        # Перевіряємо спробу блоку ворога
        if random.randint(1, 100) <= enemy.block_chance:
            return self._enemy_defend(combat_state)
        
        # Звичайна атака
        return await self._enemy_attack(combat_state)
    
    async def _enemy_attack(self, combat_state: CombatState) -> CombatTurn:
        """Обробити атаку ворога з новою формулою урону"""
        character = combat_state.character
        enemy = combat_state.enemy
        total_stats = self.character_manager.get_total_stats(character)
        
        # Перевіряємо блок персонажа
        block_chance = total_stats['block_chance']
        is_blocked = random.randint(1, 100) <= block_chance
        
        if is_blocked:
            return CombatTurn(
                actor_name=enemy.name,
                action=CombatAction.ATTACK,
                target_name=character.name,
                is_blocked=True,
                message=f"🛡️ {character.name} блокує атаку {enemy.name}!"
            )
        
        # Перевіряємо критичний удар ворога
        is_critical = random.randint(1, 100) <= enemy.critical_chance
        
        # Розраховуємо урон за новою формулою
        damage = self.balance_system.calculate_balanced_damage(
            enemy.attack, total_stats['defense'], is_critical, False
        )
        
        # Застосовуємо урон до персонажа
        self._damage_character(character, damage)
        
        turn = CombatTurn(
            actor_name=enemy.name,
            action=CombatAction.ATTACK,
            target_name=character.name,
            damage_dealt=damage,
            is_critical=is_critical
        )
        
        if is_critical:
            turn.message = f"💥 **КРИТИЧНИЙ УДАР!** {enemy.name} завдає {damage} урону!"
        else:
            turn.message = f"👹 {enemy.name} завдає {damage} урону!"
        
        return turn
    
    def _enemy_defend(self, combat_state: CombatState) -> CombatTurn:
        """Обробити захист ворога"""
        enemy = combat_state.enemy
        
        self._add_effect(combat_state.enemy_effects, 'defense_stance', {
            'type': 'defense_bonus',
            'value': 8,
            'duration': 1
        })
        
        return CombatTurn(
            actor_name=enemy.name,
            action=CombatAction.DEFEND,
            target_name=enemy.name,
            message=f"🛡️ {enemy.name} займає оборонну позицію!"
        )
    
    async def _enemy_special_ability(self, combat_state: CombatState) -> CombatTurn:
        """Обробити спеціальну здібність ворога"""
        enemy = combat_state.enemy
        character = combat_state.character
        
        if not enemy.special_abilities:
            return await self._enemy_attack(combat_state)
        
        ability = random.choice(enemy.special_abilities)
        
        # Виконуємо здібність (спрощена реалізація)
        if ability == "poison_bite":
            damage = self.balance_system.calculate_balanced_damage(
                enemy.attack + 5, 0, False, False  # Отруйна атака ігнорує захист
            )
            self._damage_character(character, damage)
            self._add_effect(combat_state.character_effects, 'poison', {
                'type': 'damage_over_time',
                'value': 3,
                'duration': 3
            })
            message = f"☠️ {enemy.name} кусає отруйними зубами! {damage} урону + отруєння!"
        
        elif ability == "regeneration":
            heal_amount = enemy.max_health // 10
            enemy.heal(heal_amount)
            message = f"💚 {enemy.name} регенерує {heal_amount} здоров'я!"
        
        else:
            # За замовчуванням - звичайна атака
            return await self._enemy_attack(combat_state)
        
        return CombatTurn(
            actor_name=enemy.name,
            action=CombatAction.SPECIAL_ABILITY,
            target_name=character.name,
            special_effect=ability,
            message=message
        )
    
    def _damage_character(self, character: Character, damage: int):
        """Застосувати урон до персонажа"""
        character.health = max(0, character.health - damage)
    
    def _calculate_flee_chance(self, character_speed: int, enemy_speed: int) -> float:
        """Розрахувати шанс успішної втечі"""
        speed_diff = character_speed - enemy_speed
        flee_chance = self.FLEE_BASE_CHANCE + (speed_diff * 0.02)
        return max(0.1, min(0.9, flee_chance))
    
    def _process_turn_effects(self, combat_state: CombatState):
        """Обробити поточні ефекти (отруєння, бафи тощо)"""
        # Обробляємо ефекти персонажа
        for effect_id, effect in list(combat_state.character_effects.items()):
            if effect['type'] == 'damage_over_time':
                damage = effect['value']
                self._damage_character(combat_state.character, damage)
            
            effect['duration'] -= 1
            if effect['duration'] <= 0:
                del combat_state.character_effects[effect_id]
        
        # Обробляємо ефекти ворога  
        for effect_id, effect in list(combat_state.enemy_effects.items()):
            if effect['type'] == 'damage_over_time':
                damage = effect['value']
                combat_state.enemy.take_damage(damage)
            
            effect['duration'] -= 1
            if effect['duration'] <= 0:
                del combat_state.enemy_effects[effect_id]
    
    def _add_effect(self, effects: Dict[str, Dict], effect_id: str, effect_data: Dict):
        """Додати ефект до словника ефектів"""
        effects[effect_id] = effect_data
    
    def _get_combat_options(self, combat_state: CombatState) -> List[Dict[str, str]]:
        """Отримати доступні опції бою для гравця"""
        total_stats = self.character_manager.get_total_stats(combat_state.character)
        
        options = [
            {'id': 'attack', 'name': '⚔️ Атакувати', 'description': 'Фізична атака'},
            {'id': 'defend', 'name': '🛡️ Захищатися', 'description': '+10 захисту на наступний хід'},
            {'id': 'flee', 'name': '💨 Втекти', 'description': 'Спробувати втекти з бою'}
        ]
        
        # Додаємо магічну атаку якщо є магічна сила
        if total_stats['magic_power'] > 0:
            options.insert(1, {
                'id': 'magic_attack',
                'name': '🔮 Магічна атака', 
                'description': 'Ігнорує частину захисту'
            })
        
        # Додаємо використання предмета
        options.insert(-1, {
            'id': 'use_item',
            'name': '🎒 Використати предмет',
            'description': 'Використати зілля або інший предмет'
        })
        
        return options
    
    def _end_combat(self, combat_state: CombatState, result: CombatResult) -> Dict[str, Any]:
        """Завершити бій та розрахувати результати"""
        character = combat_state.character
        enemy = combat_state.enemy
        
        combat_result = {
            'result': result,
            'turn_count': combat_state.turn_number,
            'combat_log': combat_state.combat_log,
            'character_health': character.health,
            'enemy_health': enemy.health,
            'experience_gained': 0,
            'gold_gained': 0,
            'items_dropped': [],
            'level_up': False
        }
        
        if result == CombatResult.VICTORY:
            # Розраховуємо винагороди
            combat_result['experience_gained'] = enemy.experience_reward
            combat_result['gold_gained'] = random.randint(enemy.gold_min, enemy.gold_max)
            
            # Розраховуємо випадання предметів
            if enemy.drop_table:
                dropped_items = self.enemy_manager.calculate_loot_drops(enemy)
                combat_result['items_dropped'] = dropped_items
            
            # Застосовуємо винагороди до персонажа
            character.gold += combat_result['gold_gained']
            
            # Додаємо досвід та перевіряємо підвищення рівня
            exp_result = self.character_manager.add_experience(character, combat_result['experience_gained'])
            combat_result.update(exp_result)
            
            logger.info(f"Combat victory: {character.name} defeats {enemy.name}")
        
        elif result == CombatResult.DEFEAT:
            logger.info(f"Combat defeat: {character.name} defeated by {enemy.name}")
        
        elif result == CombatResult.FLEE_SUCCESS:
            logger.info(f"Combat fled: {character.name} escapes from {enemy.name}")
        
        return combat_result
    
    def get_combat_summary(self, combat_result: Dict[str, Any]) -> str:
        """Сформувати відформатоване резюме бою"""
        result_type = combat_result['result']
        
        if result_type == CombatResult.VICTORY:
            lines = [
                "🎉 **ПЕРЕМОГА!**",
                "",
                f"⭐ Отримано досвіду: {combat_result['experience_gained']}",
                f"💰 Отримано золота: {combat_result['gold_gained']}"
            ]
            
            if combat_result.get('level_up'):
                lines.extend([
                    "",
                    f"🎊 **ПІДВИЩЕННЯ РІВНЯ!** Тепер {combat_result['new_level']} рівень!",
                    combat_result.get('stat_increases', '')
                ])
            
            if combat_result['items_dropped']:
                lines.extend([
                    "",
                    "🎁 **Знайдені предмети:**"
                ])
                for item_id in combat_result['items_dropped']:
                    lines.append(f"• {item_id}")
        
        elif result_type == CombatResult.DEFEAT:
            lines = [
                "💀 **ПОРАЗКА!**",
                "",
                "Ви були переможені в бою...",
                "Спробуйте покращити своє спорядження та повертайтеся!"
            ]
        
        elif result_type == CombatResult.FLEE_SUCCESS:
            lines = [
                "💨 **ВТЕЧА ВДАЛАСЯ!**",
                "",
                "Ви успішно втекли з бою."
            ]
        
        else:
            lines = ["Бій завершено."]
        
        lines.extend([
            "",
            f"⚔️ Ходів у бою: {combat_result['turn_count']}",
            f"❤️ Здоров'я: {combat_result['character_health']}"
        ])
        
        return "\n".join(lines)


# Утилітарні функції для розрахунків бою
def calculate_combat_power(character: Character, character_manager: CharacterManager) -> int:
    """Розрахувати загальну бойову силу персонажа"""
    total_stats = character_manager.get_total_stats(character)
    
    power = (
        total_stats['max_health'] * 0.4 +
        total_stats['attack'] * 8 +
        total_stats['defense'] * 6 +
        total_stats['magic_power'] * 8 +
        total_stats['speed'] * 2 +
        total_stats['critical_chance'] * 3 +
        total_stats['block_chance'] * 2 +
        character.level * 20
    )
    
    return int(power)


def get_combat_recommendation(character_power: int, enemy_difficulty: int) -> str:
    """Отримати рекомендацію для бою на основі порівняння сили"""
    ratio = character_power / max(1, enemy_difficulty)
    
    if ratio >= 1.5:
        return "🟢 Легка перемога"
    elif ratio >= 1.2:
        return "🟡 Хороші шанси"
    elif ratio >= 0.8:
        return "🟠 Рівний бій"
    elif ratio >= 0.6:
        return "🔴 Складний бій"
    else:
        return "🔴 Дуже небезпечно!"
