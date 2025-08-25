"""
Item system for Telegram RPG Bot "Легенди Валгаллії"
Contains item classes and item management
"""

import logging
import json
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


class ItemType(Enum):
    """Item type enumeration"""
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    QUEST = "quest"
    ACCESSORY = "accessory"


class ItemRarity(Enum):
    """Item rarity levels"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class Item:
    """Item data class"""
    item_id: str
    name: str
    description: str
    item_type: ItemType
    rarity: ItemRarity = ItemRarity.COMMON
    price: int = 0
    level_required: int = 1
    stats: Dict[str, int] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    stackable: bool = False
    max_stack: int = 1
    consumable_effects: Dict[str, int] = field(default_factory=dict)
    
    def get_stat_bonus(self, stat_name: str) -> int:
        """Get stat bonus from item"""
        return self.stats.get(stat_name, 0)
    
    def get_display_stats(self) -> str:
        """Get formatted stat display"""
        if not self.stats:
            return ""
        
        stat_strings = []
        stat_icons = {
            'attack': '⚔️',
            'defense': '🛡',
            'magic_power': '🔮',
            'health': '💚',
            'mana': '💙',
            'speed': '⚡',
            'critical_chance': '💥',
            'block_chance': '🛡️'
        }
        
        for stat, value in self.stats.items():
            if value > 0:
                icon = stat_icons.get(stat, '📊')
                stat_strings.append(f"{icon} +{value}")
        
        return " | ".join(stat_strings)
    
    def get_rarity_emoji(self) -> str:
        """Get emoji for item rarity"""
        rarity_emojis = {
            ItemRarity.COMMON: "⚪",
            ItemRarity.UNCOMMON: "🟢",
            ItemRarity.RARE: "🔵",
            ItemRarity.EPIC: "🟣",
            ItemRarity.LEGENDARY: "🟡"
        }
        return rarity_emojis.get(self.rarity, "⚪")
    
    def can_use(self, character_level: int) -> bool:
        """Check if character can use this item"""
        return character_level >= self.level_required
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'item_id': self.item_id,
            'name': self.name,
            'description': self.description,
            'item_type': self.item_type.value,
            'rarity': self.rarity.value,
            'price': self.price,
            'level_required': self.level_required,
            'stats': self.stats,
            'effects': self.effects,
            'stackable': self.stackable,
            'max_stack': self.max_stack,
            'consumable_effects': self.consumable_effects
        }


class ItemManager:
    """Manage all game items"""
    
    def __init__(self):
        self.items: Dict[str, Item] = {}
        self.weapons: Dict[str, Item] = {}
        self.armor: Dict[str, Item] = {}
        self.consumables: Dict[str, Item] = {}
        self.accessories: Dict[str, Item] = {}
        self._initialize_items()
    
    def _initialize_items(self):
        """Initialize all game items"""
        # Load from JSON files if they exist, otherwise create defaults
        try:
            self.load_items_from_file()
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("Creating default item catalog...")
            self._create_default_items()
            self.save_items_to_file()
    
    def _create_default_items(self):
        """Create default item catalog"""
        
        # === WEAPONS ===
        weapons_data = [
            # Common weapons
            Item("basic_sword", "Дерев'яний меч", "Простий тренувальний меч", ItemType.WEAPON, ItemRarity.COMMON, 25, 1, {'attack': 5}),
            Item("iron_sword", "Залізний меч", "Надійний залізний меч для початківців", ItemType.WEAPON, ItemRarity.COMMON, 100, 1, {'attack': 15}),
            Item("wooden_staff", "Дерев'яний посох", "Простий магічний посох", ItemType.WEAPON, ItemRarity.COMMON, 80, 1, {'magic_power': 12, 'mana': 20}),
            Item("hunting_bow", "Мисливський лук", "Легкий лук для полювання", ItemType.WEAPON, ItemRarity.COMMON, 90, 1, {'attack': 10, 'critical_chance': 5}),
            Item("bronze_dagger", "Бронзовий кинджал", "Швидкий бронзовий кинджал", ItemType.WEAPON, ItemRarity.COMMON, 60, 1, {'attack': 8, 'speed': 3}),
            
            # Uncommon weapons
            Item("steel_sword", "Сталевий меч", "Міцний сталевий меч", ItemType.WEAPON, ItemRarity.UNCOMMON, 300, 3, {'attack': 25, 'critical_chance': 5}),
            Item("war_hammer", "Бойовий молот", "Важкий дворучний молот", ItemType.WEAPON, ItemRarity.UNCOMMON, 350, 4, {'attack': 35, 'defense': 5}),
            Item("crystal_staff", "Кристалічний посох", "Посох з магічним кристалом", ItemType.WEAPON, ItemRarity.UNCOMMON, 400, 3, {'magic_power': 30, 'mana': 40}),
            Item("elven_bow", "Ельфійський лук", "Витончений ельфійський лук", ItemType.WEAPON, ItemRarity.UNCOMMON, 380, 4, {'attack': 20, 'critical_chance': 15, 'speed': 5}),
            Item("poisoned_dagger", "Отруйний кинджал", "Кинджал змащений отрутою", ItemType.WEAPON, ItemRarity.UNCOMMON, 250, 3, {'attack': 18, 'speed': 8}),
            
            # Rare weapons
            Item("flame_sword", "Полум'яний меч", "Меч палаючий магічним вогнем", ItemType.WEAPON, ItemRarity.RARE, 800, 6, {'attack': 40, 'magic_power': 15, 'critical_chance': 10}),
            Item("shadow_blade", "Клинок Тіней", "Загадковий клинок з темної магії", ItemType.WEAPON, ItemRarity.RARE, 900, 7, {'attack': 35, 'speed': 15, 'critical_chance': 20}),
            Item("arcane_staff", "Арканний посох", "Потужний магічний посох", ItemType.WEAPON, ItemRarity.RARE, 1200, 8, {'magic_power': 50, 'mana': 80, 'critical_chance': 15}),
            Item("dragon_slayer", "Вбивця Драконів", "Легендарний меч для боротьби з драконами", ItemType.WEAPON, ItemRarity.EPIC, 2500, 15, {'attack': 80, 'defense': 20, 'critical_chance': 25}),
            Item("staff_of_eternity", "Посох Вічності", "Артефакт з безмежною магічною силою", ItemType.WEAPON, ItemRarity.LEGENDARY, 5000, 20, {'magic_power': 100, 'mana': 200, 'health': 50})
        ]
        
        # === ARMOR ===
        armor_data = [
            # Common armor
            Item("basic_clothes", "Проста одежа", "Звичайний одяг мандрівника", ItemType.ARMOR, ItemRarity.COMMON, 20, 1, {'defense': 2}),
            Item("leather_armor", "Шкіряна броня", "Легка та зручна шкіряна броня", ItemType.ARMOR, ItemRarity.COMMON, 60, 1, {'defense': 6, 'speed': 2}),
            Item("apprentice_robe", "Роба учня", "Проста роба для початківців магів", ItemType.ARMOR, ItemRarity.COMMON, 70, 1, {'defense': 3, 'mana': 30, 'magic_power': 5}),
            Item("padded_armor", "Стьобана броня", "Легка стьобана броня", ItemType.ARMOR, ItemRarity.COMMON, 80, 2, {'defense': 8, 'health': 20}),
            Item("scout_vest", "Жилет розвідника", "Легкий жилет для швидкого пересування", ItemType.ARMOR, ItemRarity.COMMON, 90, 1, {'defense': 4, 'speed': 8}),
            
            # Uncommon armor
            Item("chainmail", "Кольчуга", "Надійна металева кольчуга", ItemType.ARMOR, ItemRarity.UNCOMMON, 250, 3, {'defense': 15, 'health': 40}),
            Item("scale_armor", "Лускова броня", "Броня з металевих лусок", ItemType.ARMOR, ItemRarity.UNCOMMON, 300, 4, {'defense': 18, 'block_chance': 10}),
            Item("mage_robes", "Роби мага", "Якісні роби з магічними вставками", ItemType.ARMOR, ItemRarity.UNCOMMON, 350, 3, {'defense': 8, 'mana': 70, 'magic_power': 15}),
            Item("ranger_cloak", "Плащ рейнджера", "Камуфльований плащ", ItemType.ARMOR, ItemRarity.UNCOMMON, 280, 3, {'defense': 10, 'speed': 12, 'critical_chance': 5}),
            Item("reinforced_leather", "Підсилена шкіра", "Шкіряна броня з металевими вставками", ItemType.ARMOR, ItemRarity.UNCOMMON, 320, 4, {'defense': 12, 'speed': 5, 'health': 30}),
            
            # Rare armor
            Item("plate_armor", "Латна броня", "Повна латна броня лицаря", ItemType.ARMOR, ItemRarity.RARE, 1000, 6, {'defense': 35, 'health': 80, 'block_chance': 20}),
            Item("dragon_scale", "Драконяча луска", "Броня з драконячих лусок", ItemType.ARMOR, ItemRarity.RARE, 1500, 8, {'defense': 30, 'magic_power': 20, 'health': 100}),
            Item("archmage_robes", "Роби архімага", "Елітні магічні роби", ItemType.ARMOR, ItemRarity.RARE, 1200, 7, {'defense': 15, 'mana': 150, 'magic_power': 35}),
            Item("shadow_cloak", "Плащ тіней", "Таємничий плащ убивці", ItemType.ARMOR, ItemRarity.EPIC, 2000, 12, {'defense': 20, 'speed': 25, 'critical_chance': 20}),
            Item("divine_armor", "Божественна броня", "Броня благословлена богами", ItemType.ARMOR, ItemRarity.LEGENDARY, 4000, 18, {'defense': 60, 'health': 200, 'block_chance': 30})
        ]
        
        # === CONSUMABLES ===
        consumables_data = [
            # Health potions
            Item("small_health_potion", "Мале зілля здоров'я", "Відновлює 50 HP", ItemType.CONSUMABLE, ItemRarity.COMMON, 30, 1, {}, {}, True, 10, {'health': 50}),
            Item("health_potion", "Зілля здоров'я", "Відновлює 100 HP", ItemType.CONSUMABLE, ItemRarity.COMMON, 50, 1, {}, {}, True, 10, {'health': 100}),
            Item("greater_health_potion", "Велике зілля здоров'я", "Відновлює 200 HP", ItemType.CONSUMABLE, ItemRarity.UNCOMMON, 120, 3, {}, {}, True, 5, {'health': 200}),
            Item("supreme_health_potion", "Найкраще зілля здоров'я", "Відновлює 400 HP", ItemType.CONSUMABLE, ItemRarity.RARE, 300, 8, {}, {}, True, 3, {'health': 400}),
            
            # Mana potions
            Item("small_mana_potion", "Мале зілля мани", "Відновлює 30 мани", ItemType.CONSUMABLE, ItemRarity.COMMON, 25, 1, {}, {}, True, 10, {'mana': 30}),
            Item("mana_potion", "Зілля мани", "Відновлює 60 мани", ItemType.CONSUMABLE, ItemRarity.COMMON, 45, 1, {}, {}, True, 10, {'mana': 60}),
            Item("greater_mana_potion", "Велике зілля мани", "Відновлює 120 мани", ItemType.CONSUMABLE, ItemRarity.UNCOMMON, 100, 3, {}, {}, True, 5, {'mana': 120}),
            
            # Buff potions
            Item("strength_potion", "Зілля сили", "Тимчасово +10 до атаки на 5 боїв", ItemType.CONSUMABLE, ItemRarity.UNCOMMON, 80, 2, {}, {}, True, 3, {'temp_attack': 10}),
            Item("defense_potion", "Зілля захисту", "Тимчасово +8 до захисту на 5 боїв", ItemType.CONSUMABLE, ItemRarity.UNCOMMON, 70, 2, {}, {}, True, 3, {'temp_defense': 8}),
            Item("speed_potion", "Зілля швидкості", "Тимчасово +15 до швидкості на 3 бої", ItemType.CONSUMABLE, ItemRarity.UNCOMMON, 90, 3, {}, {}, True, 3, {'temp_speed': 15}),
            Item("luck_potion", "Зілля удачі", "Тимчасово +20% до критичних ударів на 3 бої", ItemType.CONSUMABLE, ItemRarity.RARE, 150, 5, {}, {}, True, 2, {'temp_critical': 20}),
            
            # Food and utility
            Item("bread", "Хліб", "Простий хліб, відновлює 20 HP", ItemType.CONSUMABLE, ItemRarity.COMMON, 10, 1, {}, {}, True, 20, {'health': 20}),
            Item("cheese", "Сир", "Смачний сир, відновлює 30 HP", ItemType.CONSUMABLE, ItemRarity.COMMON, 15, 1, {}, {}, True, 15, {'health': 30}),
            Item("magic_scroll", "Магічний сувій", "Відновлює всю ману", ItemType.CONSUMABLE, ItemRarity.UNCOMMON, 200, 4, {}, {}, True, 3, {'mana_full': True}),
            Item("phoenix_feather", "Перо фенікса", "Воскрешає з 50% здоров'я", ItemType.CONSUMABLE, ItemRarity.EPIC, 1000, 10, {}, {}, True, 1, {'resurrect': 0.5})
        ]
        
        # Add all items to catalog
        for weapon in weapons_data:
            self.add_item(weapon)
        
        for armor_piece in armor_data:
            self.add_item(armor_piece)
        
        for consumable in consumables_data:
            self.add_item(consumable)
    
    def add_item(self, item: Item):
        """Add item to catalog"""
        self.items[item.item_id] = item
        
        # Categorize by type
        if item.item_type == ItemType.WEAPON:
            self.weapons[item.item_id] = item
        elif item.item_type == ItemType.ARMOR:
            self.armor[item.item_id] = item
        elif item.item_type == ItemType.CONSUMABLE:
            self.consumables[item.item_id] = item
        elif item.item_type == ItemType.ACCESSORY:
            self.accessories[item.item_id] = item
    
    def get_item(self, item_id: str) -> Optional[Item]:
        """Get item by ID"""
        return self.items.get(item_id)
    
    def get_items_by_type(self, item_type: ItemType) -> List[Item]:
        """Get all items of specific type"""
        return [item for item in self.items.values() if item.item_type == item_type]
    
    def get_items_by_rarity(self, rarity: ItemRarity) -> List[Item]:
        """Get all items of specific rarity"""
        return [item for item in self.items.values() if item.rarity == rarity]
    
    def get_weapons(self, min_level: int = 1, max_level: int = 50) -> List[Item]:
        """Get weapons within level range"""
        return [
            weapon for weapon in self.weapons.values()
            if min_level <= weapon.level_required <= max_level
        ]
    
    def get_armor(self, min_level: int = 1, max_level: int = 50) -> List[Item]:
        """Get armor within level range"""
        return [
            armor for armor in self.armor.values()
            if min_level <= armor.level_required <= max_level
        ]
    
    def get_consumables(self) -> List[Item]:
        """Get all consumables"""
        return list(self.consumables.values())
    
    def get_shop_items(self, character_level: int, item_type: Optional[ItemType] = None) -> List[Item]:
        """Get items available in shop for character level"""
        available_items = []
        
        for item in self.items.values():
            # Skip quest items and check level requirements
            if item.item_type == ItemType.QUEST:
                continue
            
            if item.level_required <= character_level + 2:  # Allow slightly higher level items
                if item_type is None or item.item_type == item_type:
                    available_items.append(item)
        
        # Sort by level requirement, then by price
        available_items.sort(key=lambda x: (x.level_required, x.price))
        return available_items
    
    def use_consumable(self, item: Item, character) -> Dict[str, Any]:
        """Use a consumable item and return effects"""
        if item.item_type != ItemType.CONSUMABLE:
            return {'success': False, 'message': "Цей предмет не можна використовувати!"}
        
        if not item.consumable_effects:
            return {'success': False, 'message': "У цього предмета немає ефектів!"}
        
        results = {'success': True, 'effects': [], 'message': ""}
        
        # Apply effects
        for effect_type, value in item.consumable_effects.items():
            if effect_type == 'health':
                old_health = character.health
                character.health = min(character.health + value, character.max_health)
                healed = character.health - old_health
                if healed > 0:
                    results['effects'].append(f"💚 Відновлено {healed} здоров'я")
            
            elif effect_type == 'mana':
                old_mana = character.mana
                character.mana = min(character.mana + value, character.max_mana)
                restored = character.mana - old_mana
                if restored > 0:
                    results['effects'].append(f"💙 Відновлено {restored} мани")
            
            elif effect_type == 'mana_full':
                if character.max_mana > 0:
                    character.mana = character.max_mana
                    results['effects'].append(f"💙 Мана повністю відновлена!")
            
            elif effect_type == 'resurrect':
                if character.health <= 0:
                    character.health = int(character.max_health * value)
                    results['effects'].append(f"🔥 Воскресіння! Здоров'я відновлено до {character.health}")
            
            elif effect_type.startswith('temp_'):
                # Temporary effects would be handled by combat system
                stat_name = effect_type.replace('temp_', '')
                results['effects'].append(f"⚡ Тимчасовий бонус: +{value} до {stat_name}")
        
        results['message'] = f"🍃 Використано {item.name}!\n" + "\n".join(results['effects'])
        return results
    
    def load_items_from_file(self):
        """Load items from JSON file with backward compatibility"""
        items_file = Path('data/items.json')
        if items_file.exists():
            with open(items_file, 'r', encoding='utf-8') as f:
                items_data = json.load(f)
            
            for item_id, item_info in items_data.items():
                # Handle old format compatibility
                item_type_str = item_info.get('item_type') or item_info.get('type', 'weapon')
                
                # Convert old format stats to new format
                stats = item_info.get('stats', {})
                if not stats:
                    # Convert old format bonuses
                    if 'attack_bonus' in item_info:
                        stats['attack'] = item_info['attack_bonus']
                    if 'defense_bonus' in item_info:
                        stats['defense'] = item_info['defense_bonus']
                    if 'health_bonus' in item_info and item_type_str == 'consumable':
                        # For old consumables, move health_bonus to consumable_effects
                        pass  # Handle below
                
                # Handle old consumable format
                consumable_effects = item_info.get('consumable_effects', {})
                if not consumable_effects and 'health_bonus' in item_info and item_type_str == 'consumable':
                    consumable_effects['health'] = item_info['health_bonus']
                
                try:
                    item = Item(
                        item_id=item_id,
                        name=item_info['name'],
                        description=item_info.get('description', ''),
                        item_type=ItemType(item_type_str),
                        rarity=ItemRarity(item_info.get('rarity', 'common')),
                        price=item_info.get('price', 0),
                        level_required=item_info.get('level_required', 1),
                        stats=stats,
                        effects=item_info.get('effects', {}),
                        stackable=item_info.get('stackable', item_type_str == 'consumable'),
                        max_stack=item_info.get('max_stack', 10 if item_type_str == 'consumable' else 1),
                        consumable_effects=consumable_effects
                    )
                    self.add_item(item)
                except Exception as e:
                    logger.warning(f"Failed to load item {item_id}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self.items)} items from file")
    
    def save_items_to_file(self):
        """Save items to JSON file"""
        items_file = Path('data/items.json')
        items_file.parent.mkdir(exist_ok=True)
        
        items_data = {}
        for item_id, item in self.items.items():
            items_data[item_id] = item.to_dict()
        
        with open(items_file, 'w', encoding='utf-8') as f:
            json.dump(items_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(items_data)} items to file")
    
    def get_random_loot(self, min_level: int, max_level: int, loot_type: Optional[ItemType] = None) -> Optional[Item]:
        """Get random item for loot drops"""
        import random
        
        # Filter items by level and type
        possible_items = []
        for item in self.items.values():
            if min_level <= item.level_required <= max_level:
                if loot_type is None or item.item_type == loot_type:
                    if item.item_type != ItemType.QUEST:  # No quest items in random loot
                        possible_items.append(item)
        
        if not possible_items:
            return None
        
        # Weight by rarity (common items more likely)
        rarity_weights = {
            ItemRarity.COMMON: 50,
            ItemRarity.UNCOMMON: 25,
            ItemRarity.RARE: 15,
            ItemRarity.EPIC: 8,
            ItemRarity.LEGENDARY: 2
        }
        
        weighted_items = []
        for item in possible_items:
            weight = rarity_weights.get(item.rarity, 10)
            weighted_items.extend([item] * weight)
        
        return random.choice(weighted_items) if weighted_items else None
    
    def calculate_sell_price(self, item: Item) -> int:
        """Calculate sell price for item (usually 25-40% of buy price)"""
        base_price = item.price
        sell_multiplier = 0.3
        
        # Rare items have better sell value
        if item.rarity == ItemRarity.UNCOMMON:
            sell_multiplier = 0.35
        elif item.rarity == ItemRarity.RARE:
            sell_multiplier = 0.4
        elif item.rarity == ItemRarity.EPIC:
            sell_multiplier = 0.45
        elif item.rarity == ItemRarity.LEGENDARY:
            sell_multiplier = 0.5
        
        return max(1, int(base_price * sell_multiplier))
    
    def get_item_description_full(self, item: Item) -> str:
        """Get full item description with all details"""
        lines = [
            f"{item.get_rarity_emoji()} **{item.name}**",
            f"_{item.description}_",
            ""
        ]
        
        # Stats
        stats_text = item.get_display_stats()
        if stats_text:
            lines.append(f"📊 **Характеристики:** {stats_text}")
        
        # Consumable effects
        if item.consumable_effects:
            effects = []
            for effect, value in item.consumable_effects.items():
                if effect == 'health':
                    effects.append(f"💚 +{value} HP")
                elif effect == 'mana':
                    effects.append(f"💙 +{value} Mana")
                elif effect == 'mana_full':
                    effects.append("💙 Повне відновлення мани")
                elif effect == 'resurrect':
                    effects.append(f"🔥 Воскресіння ({int(value*100)}% HP)")
                elif effect.startswith('temp_'):
                    stat = effect.replace('temp_', '')
                    effects.append(f"⚡ Тимчасово +{value} {stat}")
            
            if effects:
                lines.append(f"✨ **Ефекти:** {' | '.join(effects)}")
        
        # Requirements and info
        lines.extend([
            "",
            f"🎯 **Рівень:** {item.level_required}",
            f"💰 **Ціна:** {item.price} золота",
            f"🏷 **Рідкість:** {item.rarity.value.title()}"
        ])
        
        if item.stackable:
            lines.append(f"📦 **Максимальна кількість:** {item.max_stack}")
        
        return "\n".join(lines)


# Global item manager instance - initialize when needed
# item_manager = ItemManager()  # Moved to lazy initialization
