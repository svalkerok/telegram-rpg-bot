"""
Character management logic
"""

import logging
from typing import Dict, Any, Optional, List
from database.database_models import Character
from database.db_manager import DatabaseManager
from game_logic.items import Item, ItemType
import config

logger = logging.getLogger(__name__)


class CharacterManager:
    """Manage character operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._item_manager = None
    
    @property
    def item_manager(self):
        """Lazy initialization of ItemManager"""
        if self._item_manager is None:
            from game_logic.items import ItemManager
            self._item_manager = ItemManager()
        return self._item_manager
    
    def get_class_base_stats(self, char_class: str) -> Dict[str, Any]:
        """Get base stats for character class"""
        if char_class not in config.CHARACTER_CLASSES:
            char_class = 'warrior'  # Default fallback
        
        class_config = config.CHARACTER_CLASSES[char_class]
        return {
            'base_stats': class_config['base_stats'].copy(),
            'level_bonus': class_config['level_bonus'].copy(),
            'start_equipment': class_config['start_equipment'].copy(),
            'name': class_config['name'],
            'emoji': class_config['emoji']
        }
    
    def create_character(self, user_id: int, name: str, char_class: str) -> Character:
        """Create a new character with base stats"""
        
        # Get class configuration
        if char_class not in config.CHARACTER_CLASSES:
            char_class = 'warrior'  # Default to warrior
        
        class_config = config.CHARACTER_CLASSES[char_class]
        base_stats = class_config['base_stats']
        
        # Create character instance
        character = Character(
            user_id=user_id,
            name=name,
            character_class=char_class,
            level=1,
            experience=0,
            experience_needed=config.BASE_EXP_REQUIRED,
            health=base_stats['health'],
            max_health=base_stats['max_health'],
            mana=base_stats.get('mana', 0),
            max_mana=base_stats.get('max_mana', 0),
            gold=50,  # Starting gold
            attack=base_stats['attack'],
            defense=base_stats['defense'],
            magic_power=base_stats.get('magic_power', 0),
            speed=base_stats['speed'],
            critical_chance=base_stats['critical_chance'],
            block_chance=base_stats['block_chance'],
            weapon=class_config['start_equipment']['weapon'],
            armor=class_config['start_equipment']['armor']
        )
        
        logger.info(f"Created character: {name} ({char_class}) for user {user_id}")
        return character
    
    def level_up(self, character: Character) -> bool:
        """Level up character if enough experience"""
        
        if character.experience < character.experience_needed:
            return False
        
        # Level up
        character.experience -= character.experience_needed
        character.level += 1
        character.experience_needed = int(character.experience_needed * config.EXP_MULTIPLIER)
        
        # Apply level bonuses
        self.apply_level_bonuses(character)
        
        logger.info(f"Character {character.name} leveled up to {character.level}")
        return True
    
    def apply_level_bonuses(self, character: Character):
        """Apply level bonuses based on class"""
        
        class_config = config.CHARACTER_CLASSES.get(character.character_class)
        if not class_config:
            return
        
        level_bonus = class_config['level_bonus']
        
        # Apply health bonus
        if 'health' in level_bonus:
            character.max_health += level_bonus['health']
            character.health = character.max_health  # Full heal on level up
        
        # Apply mana bonus
        if 'mana' in level_bonus:
            character.max_mana += level_bonus['mana']
            character.mana = character.max_mana
        
        # Apply other stat bonuses
        for stat in ['attack', 'defense', 'magic_power', 'speed', 'critical_chance', 'block_chance']:
            if stat in level_bonus and level_bonus[stat] > 0:
                current_value = getattr(character, stat, 0)
                setattr(character, stat, current_value + level_bonus[stat])
    
    def calculate_combat_power(self, character: Character) -> int:
        """Calculate character's combat power rating"""
        
        # Simple formula for combat power
        combat_power = (
            character.max_health * 0.5 +
            character.attack * 10 +
            character.defense * 8 +
            character.magic_power * 10 +
            character.speed * 5 +
            character.critical_chance * 3 +
            character.block_chance * 3 +
            character.level * 50
        )
        
        return int(combat_power)
    
    def get_class_name(self, char_class: str) -> str:
        """Get localized class name"""
        
        class_config = config.CHARACTER_CLASSES.get(char_class)
        if class_config:
            return class_config['name']
        return "Unknown"
    
    def get_class_emoji(self, char_class: str) -> str:
        """Get class emoji"""
        
        class_config = config.CHARACTER_CLASSES.get(char_class)
        if class_config:
            return class_config['emoji']
        return "👤"
    
    def validate_character_name(self, name: str) -> tuple[bool, str]:
        """Validate character name"""
        
        # Check length
        if len(name) < config.MIN_CHARACTER_NAME_LENGTH:
            return False, f"Ім'я занадто коротке! Мінімум {config.MIN_CHARACTER_NAME_LENGTH} символи."
        
        if len(name) > config.MAX_CHARACTER_NAME_LENGTH:
            return False, f"Ім'я занадто довге! Максимум {config.MAX_CHARACTER_NAME_LENGTH} символів."
        
        # Check characters
        if not all(c.isalnum() or c.isspace() or c in '-_' for c in name):
            return False, "Ім'я може містити тільки літери, цифри, пробіли, дефіс та підкреслення!"
        
        # Check for excessive spaces
        if '  ' in name:
            return False, "Ім'я не може містити подвійні пробіли!"
        
        # Check if starts/ends with space
        if name.startswith(' ') or name.endswith(' '):
            return False, "Ім'я не може починатися або закінчуватися пробілом!"
        
        return True, "OK"
    
    def get_stat_increase_text(self, character: Character, old_level: int) -> str:
        """Get text describing stat increases from leveling"""
        
        class_config = config.CHARACTER_CLASSES.get(character.character_class)
        if not class_config:
            return ""
        
        level_bonus = class_config['level_bonus']
        level_diff = character.level - old_level
        
        increases = []
        
        if level_bonus.get('health', 0) > 0:
            increases.append(f"💚 Здоров'я +{level_bonus['health'] * level_diff}")
        
        if level_bonus.get('mana', 0) > 0:
            increases.append(f"💙 Мана +{level_bonus['mana'] * level_diff}")
        
        if level_bonus.get('attack', 0) > 0:
            increases.append(f"⚔️ Атака +{level_bonus['attack'] * level_diff}")
        
        if level_bonus.get('defense', 0) > 0:
            increases.append(f"🛡 Захист +{level_bonus['defense'] * level_diff}")
        
        if level_bonus.get('magic_power', 0) > 0:
            increases.append(f"🔮 Магічна сила +{level_bonus['magic_power'] * level_diff}")
        
        if level_bonus.get('speed', 0) > 0:
            increases.append(f"⚡ Швидкість +{level_bonus['speed'] * level_diff}")
        
        return "\n".join(increases)
    
    def check_achievements(self, character: Character) -> list:
        """Check if character has earned any achievements"""
        
        # This would connect to an achievements system
        # For now, return empty list
        return []
    
    def get_equipment_bonuses(self, character: Character) -> Dict[str, int]:
        """Calculate stat bonuses from equipped items"""
        bonuses = {
            'attack': 0, 'defense': 0, 'magic_power': 0, 'health': 0,
            'mana': 0, 'speed': 0, 'critical_chance': 0, 'block_chance': 0
        }
        
        # Get weapon bonuses
        weapon = self.item_manager.get_item(character.weapon)
        if weapon:
            for stat, value in weapon.stats.items():
                if stat in bonuses:
                    bonuses[stat] += value
        
        # Get armor bonuses
        armor = self.item_manager.get_item(character.armor)
        if armor:
            for stat, value in armor.stats.items():
                if stat in bonuses:
                    bonuses[stat] += value
        
        return bonuses
    
    def get_total_stats(self, character: Character) -> Dict[str, int]:
        """Get character's total stats including equipment bonuses"""
        base_stats = {
            'health': character.health,
            'max_health': character.max_health,
            'mana': character.mana,
            'max_mana': character.max_mana,
            'attack': character.attack,
            'defense': character.defense,
            'magic_power': character.magic_power,
            'speed': character.speed,
            'critical_chance': character.critical_chance,
            'block_chance': character.block_chance
        }
        
        equipment_bonuses = self.get_equipment_bonuses(character)
        
        # Apply bonuses to relevant stats (not current health/mana)
        total_stats = base_stats.copy()
        for stat, bonus in equipment_bonuses.items():
            if stat in total_stats and stat not in ['health', 'mana']:
                total_stats[stat] += bonus
        
        # Special handling for max health/mana bonuses
        if equipment_bonuses.get('health', 0) > 0:
            total_stats['max_health'] += equipment_bonuses['health']
        if equipment_bonuses.get('mana', 0) > 0:
            total_stats['max_mana'] += equipment_bonuses['mana']
        
        return total_stats
    
    def equip_item(self, character: Character, item_id: str) -> tuple[bool, str]:
        """Equip an item to character"""
        item = self.item_manager.get_item(item_id)
        if not item:
            return False, "Предмет не знайдено!"
        
        if not item.can_use(character.level):
            return False, f"Потрібен {item.level_required} рівень для використання цього предмета!"
        
        # Check item type and equip appropriately
        if item.item_type == ItemType.WEAPON:
            old_weapon = character.weapon
            character.weapon = item_id
            return True, f"✅ Озброєно {item.name}!" + (f" Знято: {old_weapon}" if old_weapon != item_id else "")
        
        elif item.item_type == ItemType.ARMOR:
            old_armor = character.armor
            character.armor = item_id
            return True, f"✅ Одягнуто {item.name}!" + (f" Знято: {old_armor}" if old_armor != item_id else "")
        
        else:
            return False, "Цей предмет не можна одягнути!"
    
    def use_consumable_item(self, character: Character, item_id: str) -> tuple[bool, str]:
        """Use a consumable item on character"""
        item = self.item_manager.get_item(item_id)
        if not item:
            return False, "Предмет не знайдено!"
        
        if item.item_type != ItemType.CONSUMABLE:
            return False, "Цей предмет не можна використовувати!"
        
        result = self.item_manager.use_consumable(item, character)
        return result['success'], result['message']
    
    def get_character_display(self, character: Character, detailed: bool = True) -> str:
        """Get formatted character display with equipment info"""
        class_info = self.get_class_base_stats(character.character_class)
        total_stats = self.get_total_stats(character)
        
        lines = [
            f"{class_info['emoji']} **{character.name}** - {class_info['name']}",
            f"🎯 Рівень: {character.level}",
            f"⚡ Досвід: {character.experience}/{character.experience_needed}",
            f"💰 Золото: {character.gold}",
            ""
        ]
        
        # Health and mana
        lines.append(f"💚 Здоров'я: {character.health}/{total_stats['max_health']}")
        if character.max_mana > 0:
            lines.append(f"💙 Мана: {character.mana}/{total_stats['max_mana']}")
        
        if detailed:
            lines.extend([
                "",
                "⚔️ **Характеристики:**",
                f"🗡 Атака: {total_stats['attack']}",
                f"🛡 Захист: {total_stats['defense']}",
                f"⚡ Швидкість: {total_stats['speed']}",
                f"💥 Шанс криту: {total_stats['critical_chance']}%",
                f"🛡️ Шанс блоку: {total_stats['block_chance']}%"
            ])
            
            if character.magic_power > 0:
                lines.append(f"🔮 Магічна сила: {total_stats['magic_power']}")
            
            # Equipment
            lines.append("\n🎒 **Спорядження:**")
            weapon = self.item_manager.get_item(character.weapon)
            armor = self.item_manager.get_item(character.armor)
            
            weapon_name = weapon.name if weapon else "Не озброєно"
            armor_name = armor.name if armor else "Немає броні"
            
            lines.extend([
                f"⚔️ Зброя: {weapon_name}",
                f"🛡 Броня: {armor_name}"
            ])
            
            # Combat power
            combat_power = self.calculate_combat_power(character)
            lines.append(f"\n💪 Сила в бою: {combat_power}")
        
        return "\n".join(lines)
    
    def get_next_milestone(self, character: Character) -> Dict[str, Any]:
        """Get next milestone for character"""
        milestones = [5, 10, 20, 30, 40, 50]
        
        for milestone in milestones:
            if character.level < milestone:
                return {
                    'level': milestone,
                    'reward': f"Особливий титул на рівні {milestone}"
                }
        
        return {
            'level': config.MAX_LEVEL,
            'reward': "Максимальний рівень досягнуто!"
        }
    
    def get_available_equipment(self, character: Character, equipment_type: ItemType) -> List[Item]:
        """Get equipment available for character level"""
        if equipment_type == ItemType.WEAPON:
            return self.item_manager.get_weapons(1, character.level + 2)
        elif equipment_type == ItemType.ARMOR:
            return self.item_manager.get_armor(1, character.level + 2)
        else:
            return []
    
    def rest_character(self, character: Character) -> str:
        """Rest character to restore health and mana"""
        total_stats = self.get_total_stats(character)
        
        old_health = character.health
        old_mana = character.mana
        
        character.health = total_stats['max_health']
        character.mana = total_stats['max_mana']
        
        healed = character.health - old_health
        mana_restored = character.mana - old_mana
        
        messages = []
        if healed > 0:
            messages.append(f"💚 Здоров'я відновлено на {healed}")
        if mana_restored > 0:
            messages.append(f"💙 Мана відновлена на {mana_restored}")
        
        if not messages:
            return "😴 Ви добре відпочили, але вже були в повному здоров'ї!"
        
        return "😴 Відпочинок завершено!\n" + "\n".join(messages)
    
    def add_experience(self, character: Character, exp_amount: int) -> Dict[str, Any]:
        """Add experience to character and check for level ups"""
        character.experience += exp_amount
        
        levels_gained = 0
        old_level = character.level
        
        # Check for multiple level ups
        while character.experience >= character.experience_needed and character.level < config.MAX_LEVEL:
            if self.level_up(character):
                levels_gained += 1
            else:
                break
        
        result = {
            'exp_gained': exp_amount,
            'levels_gained': levels_gained,
            'old_level': old_level,
            'new_level': character.level,
            'level_up': levels_gained > 0
        }
        
        if levels_gained > 0:
            result['stat_increases'] = self.get_stat_increase_text(character, old_level)
        
        return result
    
    def get_class_description(self, char_class: str) -> str:
        """Get detailed class description"""
        class_info = self.get_class_base_stats(char_class)
        if not class_info:
            return "Невідомий клас"
        
        base_stats = class_info['base_stats']
        level_bonus = class_info['level_bonus']
        
        lines = [
            f"{class_info['emoji']} **{class_info['name']}**",
            "",
            "📊 **Базові характеристики:**",
            f"💚 Здоров'я: {base_stats['max_health']}",
            f"⚔️ Атака: {base_stats['attack']}",
            f"🛡 Захист: {base_stats['defense']}",
            f"⚡ Швидкість: {base_stats['speed']}",
            f"💥 Шанс криту: {base_stats['critical_chance']}%",
            f"🛡️ Шанс блоку: {base_stats['block_chance']}%"
        ]
        
        if base_stats.get('max_mana', 0) > 0:
            lines.insert(-4, f"💙 Мана: {base_stats['max_mana']}")
        
        if base_stats.get('magic_power', 0) > 0:
            lines.insert(-1, f"🔮 Магічна сила: {base_stats['magic_power']}")
        
        # Level bonuses
        lines.extend([
            "",
            "📈 **Бонус за рівень:**"
        ])
        
        for stat, bonus in level_bonus.items():
            if bonus > 0:
                stat_names = {
                    'health': '💚 Здоров\'я',
                    'mana': '💙 Мана',
                    'attack': '⚔️ Атака',
                    'defense': '🛡 Захист',
                    'magic_power': '🔮 Магічна сила',
                    'speed': '⚡ Швидкість',
                    'critical_chance': '💥 Шанс криту',
                    'block_chance': '🛡️ Шанс блоку'
                }
                
                stat_name = stat_names.get(stat, stat)
                lines.append(f"{stat_name}: +{bonus}")
        
        return "\n".join(lines)