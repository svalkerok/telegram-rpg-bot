"""
Equipment system for Telegram RPG Bot
Handles weapons, armor, upgrades and related mechanics
"""

import json
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EquipmentType(Enum):
    """Equipment types"""
    WEAPON = "weapon"
    ARMOR = "armor"


class CharacterClass(Enum):
    """Character classes for equipment restrictions"""
    WARRIOR = "warrior"
    MAGE = "mage"
    RANGER = "ranger"


class Quality(Enum):
    """Equipment quality levels"""
    COMMON = "common"
    UNCOMMON = "uncommon"  
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class SpecialEffect:
    """Special equipment effect"""
    type: str  # crit_bonus, damage_bonus, etc.
    value: int  # effect value
    description: str = ""


@dataclass
class EquipmentStats:
    """Equipment base statistics"""
    attack: int = 0
    defense: int = 0
    speed: int = 0
    mana: int = 0
    magic_power: int = 0
    crit_chance: int = 0
    block_chance: int = 0
    dodge_chance: int = 0


@dataclass
class EquipmentItem:
    """Equipment item definition"""
    id: str
    name: str
    type: EquipmentType
    class_restriction: CharacterClass
    level_requirement: int
    base_stats: EquipmentStats
    special_effects: List[SpecialEffect] = field(default_factory=list)
    base_price: int = 100
    upgrade_level: int = 0
    quality: Quality = Quality.COMMON
    can_upgrade: bool = True
    max_upgrade: int = 40
    description: str = ""

    def get_current_stats(self) -> EquipmentStats:
        """Calculate current stats with upgrades"""
        if self.upgrade_level == 0:
            return self.base_stats
        
        # Formula: base_stat + (base_stat * 0.15 * upgrade_level)
        multiplier = 1 + (0.15 * self.upgrade_level)
        
        return EquipmentStats(
            attack=int(self.base_stats.attack * multiplier),
            defense=int(self.base_stats.defense * multiplier),
            speed=int(self.base_stats.speed * multiplier),
            mana=int(self.base_stats.mana * multiplier),
            magic_power=int(self.base_stats.magic_power * multiplier),
            crit_chance=int(self.base_stats.crit_chance * multiplier),
            block_chance=int(self.base_stats.block_chance * multiplier),
            dodge_chance=int(self.base_stats.dodge_chance * multiplier)
        )

    def get_upgrade_cost(self) -> Dict[str, int]:
        """Get cost to upgrade to next level"""
        if self.upgrade_level >= self.max_upgrade:
            return {}
        
        base_cost = 50
        gods_stone_cost = 1 + (self.upgrade_level // 2)
        gold_cost = base_cost * (2 ** self.upgrade_level)
        
        # Success rate decreases with upgrade level
        success_rate = max(50, 90 - (self.upgrade_level * 5))
        
        return {
            "gods_stone": gods_stone_cost,
            "gold": gold_cost,
            "success_rate": success_rate
        }

    def get_sell_price(self) -> int:
        """Calculate sell price"""
        upgrade_value = sum(self.get_upgrade_cost().get("gold", 0) for _ in range(self.upgrade_level))
        return int((self.base_price + upgrade_value) * 0.5)


@dataclass
class PlayerEquipment:
    """Player's equipment instance"""
    user_id: int
    item_id: str
    upgrade_level: int = 0
    is_equipped: bool = False
    acquired_at: str = ""


@dataclass
class Materials:
    """Crafting materials"""
    gods_stone: int = 0
    mithril_dust: int = 0
    dragon_scale: int = 0


class EquipmentManager:
    """Manages all equipment-related operations"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.equipment_data = {}
        self.load_equipment_data()
    
    def load_equipment_data(self):
        """Load equipment data from definitions"""
        
        # Warrior weapons
        warrior_weapons = {
            "novice_sword": EquipmentItem(
                id="novice_sword",
                name="Меч новобранця",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.WARRIOR,
                level_requirement=1,
                base_stats=EquipmentStats(attack=25),
                base_price=100,
                quality=Quality.COMMON,
                description="Простий меч для початківців"
            ),
            "knight_sword": EquipmentItem(
                id="knight_sword",
                name="Меч лицаря",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.WARRIOR,
                level_requirement=5,
                base_stats=EquipmentStats(attack=55, crit_chance=5),
                special_effects=[SpecialEffect("crit_bonus", 10, "+10% критичний удар")],
                base_price=600,
                quality=Quality.UNCOMMON,
                description="Надійний меч досвідченого лицаря"
            ),
            "paladin_mace": EquipmentItem(
                id="paladin_mace",
                name="Булава паладина",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.WARRIOR,
                level_requirement=10,
                base_stats=EquipmentStats(attack=80, block_chance=10),
                special_effects=[SpecialEffect("defense_bonus", 15, "+15 захист")],
                base_price=1200,
                quality=Quality.RARE,
                description="Священна зброя захисника віри"
            ),
            "champion_blade": EquipmentItem(
                id="champion_blade",
                name="Клинок чемпіона",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.WARRIOR,
                level_requirement=15,
                base_stats=EquipmentStats(attack=120, crit_chance=15, speed=5),
                special_effects=[SpecialEffect("damage_bonus", 25, "+25% урон")],
                base_price=2500,
                quality=Quality.EPIC,
                description="Легендарна зброя арени"
            ),
            "dragon_slayer": EquipmentItem(
                id="dragon_slayer",
                name="Драконобійець",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.WARRIOR,
                level_requirement=20,
                base_stats=EquipmentStats(attack=180, crit_chance=20, speed=10),
                special_effects=[
                    SpecialEffect("dragon_slayer", 50, "+50% урон драконам"),
                    SpecialEffect("fire_resist", 30, "+30% опір вогню")
                ],
                base_price=5000,
                quality=Quality.LEGENDARY,
                description="Міфічна зброя для полювання на драконів"
            )
        }
        
        # Warrior armor
        warrior_armor = {
            "leather_armor": EquipmentItem(
                id="leather_armor",
                name="Шкіряна броня",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.WARRIOR,
                level_requirement=1,
                base_stats=EquipmentStats(defense=20, speed=-2),
                base_price=150,
                quality=Quality.COMMON,
                description="Легка захисна броня"
            ),
            "chainmail": EquipmentItem(
                id="chainmail",
                name="Кольчуга",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.WARRIOR,
                level_requirement=5,
                base_stats=EquipmentStats(defense=45, block_chance=5, speed=-3),
                base_price=800,
                quality=Quality.UNCOMMON,
                description="Металічна кольчуга зі сталі"
            ),
            "plate_armor": EquipmentItem(
                id="plate_armor",
                name="Латна броня",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.WARRIOR,
                level_requirement=10,
                base_stats=EquipmentStats(defense=75, block_chance=15, speed=-5),
                special_effects=[SpecialEffect("damage_reduce", 10, "-10% отриманий урон")],
                base_price=1500,
                quality=Quality.RARE,
                description="Важка металева броня"
            ),
            "dragon_scale_armor": EquipmentItem(
                id="dragon_scale_armor",
                name="Броня з драконячої луски",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.WARRIOR,
                level_requirement=15,
                base_stats=EquipmentStats(defense=110, block_chance=20, magic_power=25),
                special_effects=[
                    SpecialEffect("fire_resist", 50, "+50% опір вогню"),
                    SpecialEffect("magic_resist", 25, "+25% опір магії")
                ],
                base_price=3000,
                quality=Quality.EPIC,
                description="Броня з луски давнього дракона"
            ),
            "divine_armor": EquipmentItem(
                id="divine_armor",
                name="Божественна броня",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.WARRIOR,
                level_requirement=20,
                base_stats=EquipmentStats(defense=160, block_chance=30, magic_power=40, speed=-2),
                special_effects=[
                    SpecialEffect("divine_protection", 25, "+25% опір всьому урону"),
                    SpecialEffect("health_regen", 5, "+5 HP/хід")
                ],
                base_price=6000,
                quality=Quality.LEGENDARY,
                description="Священна броня благословенна богами"
            )
        }
        
        # Mage weapons
        mage_weapons = {
            "apprentice_staff": EquipmentItem(
                id="apprentice_staff",
                name="Посох учня",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.MAGE,
                level_requirement=1,
                base_stats=EquipmentStats(magic_power=30, mana=20),
                base_price=120,
                quality=Quality.COMMON,
                description="Простий посох для новачків магії"
            ),
            "wizard_staff": EquipmentItem(
                id="wizard_staff",
                name="Посох мага",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.MAGE,
                level_requirement=5,
                base_stats=EquipmentStats(magic_power=65, mana=50, crit_chance=8),
                base_price=700,
                quality=Quality.UNCOMMON,
                description="Зачарований посох досвідченого мага"
            ),
            "arcane_orb": EquipmentItem(
                id="arcane_orb",
                name="Таємна сфера",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.MAGE,
                level_requirement=10,
                base_stats=EquipmentStats(magic_power=95, mana=80, crit_chance=15),
                special_effects=[SpecialEffect("mana_regen", 3, "+3 мана/хід")],
                base_price=1400,
                quality=Quality.RARE,
                description="Містична сфера, що пульсує енергією"
            ),
            "elemental_staff": EquipmentItem(
                id="elemental_staff",
                name="Посох стихій",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.MAGE,
                level_requirement=15,
                base_stats=EquipmentStats(magic_power=140, mana=120, crit_chance=20),
                special_effects=[
                    SpecialEffect("elemental_mastery", 30, "+30% урон стихійної магії"),
                    SpecialEffect("spell_power", 25, "+25% сила заклинань")
                ],
                base_price=2800,
                quality=Quality.EPIC,
                description="Посох, що керує силами природи"
            ),
            "cosmic_scepter": EquipmentItem(
                id="cosmic_scepter",
                name="Космічний скіпетр",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.MAGE,
                level_requirement=20,
                base_stats=EquipmentStats(magic_power=200, mana=180, crit_chance=25, speed=8),
                special_effects=[
                    SpecialEffect("cosmic_power", 50, "+50% урон від усієї магії"),
                    SpecialEffect("mana_efficiency", 30, "-30% вартість заклинань")
                ],
                base_price=5500,
                quality=Quality.LEGENDARY,
                description="Скіпетр, створений з фрагментів зірок"
            )
        }
        
        # Mage armor
        mage_armor = {
            "cloth_robes": EquipmentItem(
                id="cloth_robes",
                name="Тканинні мантії",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.MAGE,
                level_requirement=1,
                base_stats=EquipmentStats(defense=15, mana=30, speed=2),
                base_price=100,
                quality=Quality.COMMON,
                description="Прості мантії для початківців магії"
            ),
            "mage_robes": EquipmentItem(
                id="mage_robes",
                name="Мантія мага",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.MAGE,
                level_requirement=5,
                base_stats=EquipmentStats(defense=35, mana=70, magic_power=25, speed=3),
                base_price=650,
                quality=Quality.UNCOMMON,
                description="Зачаровані мантії з магічними рунами"
            ),
            "arcane_vestments": EquipmentItem(
                id="arcane_vestments",
                name="Таємні вбрання",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.MAGE,
                level_requirement=10,
                base_stats=EquipmentStats(defense=55, mana=120, magic_power=50, crit_chance=10),
                special_effects=[SpecialEffect("magic_resist", 20, "+20% опір магії")],
                base_price=1300,
                quality=Quality.RARE,
                description="Вбрання, створене з чистої магічної енергії"
            ),
            "celestial_robes": EquipmentItem(
                id="celestial_robes",
                name="Небесні мантії",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.MAGE,
                level_requirement=15,
                base_stats=EquipmentStats(defense=80, mana=180, magic_power=80, crit_chance=18, speed=5),
                special_effects=[
                    SpecialEffect("celestial_power", 35, "+35% сила заклинань"),
                    SpecialEffect("mana_shield", 15, "15% шанс блокувати урон маною")
                ],
                base_price=2700,
                quality=Quality.EPIC,
                description="Мантії, благословенні небесними силами"
            ),
            "void_regalia": EquipmentItem(
                id="void_regalia",
                name="Регалії Порожнечі",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.MAGE,
                level_requirement=20,
                base_stats=EquipmentStats(defense=120, mana=250, magic_power=120, crit_chance=25, speed=8),
                special_effects=[
                    SpecialEffect("void_mastery", 60, "+60% урон від темної магії"),
                    SpecialEffect("spell_absorption", 25, "25% шанс поглинути заклинання ворога")
                ],
                base_price=5200,
                quality=Quality.LEGENDARY,
                description="Регалії, що черпають силу з самої Порожнечі"
            )
        }
        
        # Ranger weapons
        ranger_weapons = {
            "hunting_bow": EquipmentItem(
                id="hunting_bow",
                name="Мисливський лук",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.RANGER,
                level_requirement=1,
                base_stats=EquipmentStats(attack=22, speed=8),
                base_price=110,
                quality=Quality.COMMON,
                description="Надійний лук для полювання"
            ),
            "elven_bow": EquipmentItem(
                id="elven_bow",
                name="Ельфійський лук",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.RANGER,
                level_requirement=5,
                base_stats=EquipmentStats(attack=50, speed=15, crit_chance=12),
                special_effects=[SpecialEffect("precision", 10, "+10% точність")],
                base_price=650,
                quality=Quality.UNCOMMON,
                description="Вишуканий лук роботи ельфійських майстрів"
            ),
            "crossbow_master": EquipmentItem(
                id="crossbow_master",
                name="Арбалет майстра",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.RANGER,
                level_requirement=10,
                base_stats=EquipmentStats(attack=85, speed=10, crit_chance=20),
                special_effects=[SpecialEffect("piercing_shot", 25, "+25% прониклива стріла")],
                base_price=1350,
                quality=Quality.RARE,
                description="Потужний арбалет з механізмом швидкої перезарядки"
            ),
            "windforce_bow": EquipmentItem(
                id="windforce_bow",
                name="Лук сили вітру",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.RANGER,
                level_requirement=15,
                base_stats=EquipmentStats(attack=125, speed=25, crit_chance=25, dodge_chance=10),
                special_effects=[
                    SpecialEffect("wind_arrows", 40, "+40% урон від стріл вітру"),
                    SpecialEffect("swift_shot", 20, "+20% швидкість атаки")
                ],
                base_price=2600,
                quality=Quality.EPIC,
                description="Магічний лук, що стріляє стрілами зі стиснутого вітру"
            ),
            "dragon_bone_bow": EquipmentItem(
                id="dragon_bone_bow",
                name="Лук з кістки дракона",
                type=EquipmentType.WEAPON,
                class_restriction=CharacterClass.RANGER,
                level_requirement=20,
                base_stats=EquipmentStats(attack=180, speed=35, crit_chance=30, dodge_chance=15),
                special_effects=[
                    SpecialEffect("dragon_pierce", 55, "+55% пронизливі стріли"),
                    SpecialEffect("ancient_power", 35, "+35% урон від стародавньої сили")
                ],
                base_price=5300,
                quality=Quality.LEGENDARY,
                description="Лук, створений з кістки древнього дракона"
            )
        }
        
        # Ranger armor
        ranger_armor = {
            "scout_leather": EquipmentItem(
                id="scout_leather",
                name="Шкіра розвідника",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.RANGER,
                level_requirement=1,
                base_stats=EquipmentStats(defense=18, speed=5, dodge_chance=5),
                base_price=130,
                quality=Quality.COMMON,
                description="Легка шкіряна броня для швидкого пересування"
            ),
            "ranger_vest": EquipmentItem(
                id="ranger_vest",
                name="Жилет рейнджера",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.RANGER,
                level_requirement=5,
                base_stats=EquipmentStats(defense=40, speed=12, dodge_chance=10, crit_chance=5),
                base_price=680,
                quality=Quality.UNCOMMON,
                description="Зміцнений жилет з потайними кишенями"
            ),
            "shadow_cloak": EquipmentItem(
                id="shadow_cloak",
                name="Плащ тіней",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.RANGER,
                level_requirement=10,
                base_stats=EquipmentStats(defense=65, speed=20, dodge_chance=20, crit_chance=12),
                special_effects=[SpecialEffect("stealth", 15, "+15% шанс уникнути виявлення")],
                base_price=1250,
                quality=Quality.RARE,
                description="Магічний плащ, що зливається з тінями"
            ),
            "druid_hide": EquipmentItem(
                id="druid_hide",
                name="Шкура друїда",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.RANGER,
                level_requirement=15,
                base_stats=EquipmentStats(defense=95, speed=30, dodge_chance=25, magic_power=30),
                special_effects=[
                    SpecialEffect("nature_bond", 30, "+30% зв'язок з природою"),
                    SpecialEffect("forest_camouflage", 20, "+20% маскування в лісі")
                ],
                base_price=2650,
                quality=Quality.EPIC,
                description="Зачарована шкура, благословенна духами лісу"
            ),
            "phoenix_leather": EquipmentItem(
                id="phoenix_leather",
                name="Шкіра феніксу",
                type=EquipmentType.ARMOR,
                class_restriction=CharacterClass.RANGER,
                level_requirement=20,
                base_stats=EquipmentStats(defense=140, speed=40, dodge_chance=35, crit_chance=20, magic_power=50),
                special_effects=[
                    SpecialEffect("phoenix_rebirth", 10, "10% шанс воскреснути після смерті"),
                    SpecialEffect("fire_immunity", 100, "Повний імунітет до вогню")
                ],
                base_price=5400,
                quality=Quality.LEGENDARY,
                description="Легендарна шкіра міфічного феніксу"
            )
        }
        
        # Combine all equipment
        self.equipment_data = {
            **warrior_weapons,
            **warrior_armor,
            **mage_weapons,
            **mage_armor,
            **ranger_weapons,
            **ranger_armor
        }
        
        logger.info(f"Loaded {len(self.equipment_data)} equipment items")

    def get_equipment_by_id(self, item_id: str) -> Optional[EquipmentItem]:
        """Get equipment item by ID"""
        return self.equipment_data.get(item_id)

    def get_class_equipment(self, character_class: str, equipment_type: str = None) -> List[EquipmentItem]:
        """Get equipment available for character class"""
        try:
            class_enum = CharacterClass(character_class.lower())
            type_enum = EquipmentType(equipment_type.lower()) if equipment_type else None
            
            items = []
            for item in self.equipment_data.values():
                if item.class_restriction == class_enum:
                    if type_enum is None or item.type == type_enum:
                        items.append(item)
            
            # Sort by level requirement then by price
            items.sort(key=lambda x: (x.level_requirement, x.base_price))
            return items
            
        except (ValueError, AttributeError):
            return []

    def check_equipment_compatibility(self, character_class: str, item_id: str) -> bool:
        """Check if character can use equipment"""
        item = self.get_equipment_by_id(item_id)
        if not item:
            return False
        
        try:
            class_enum = CharacterClass(character_class.lower())
            return item.class_restriction == class_enum
        except ValueError:
            return False

    def calculate_upgrade_stats(self, base_stat: int, upgrade_level: int) -> int:
        """Calculate stat after upgrades"""
        if upgrade_level == 0:
            return base_stat
        
        # Formula: base_stat + (base_stat * 0.15 * upgrade_level)
        return int(base_stat * (1 + 0.15 * upgrade_level))

    def get_upgrade_cost(self, upgrade_level: int) -> Dict[str, int]:
        """Get cost for upgrading to next level"""
        if upgrade_level >= 40:  # Max upgrade level
            return {}
        
        # More balanced cost scaling for higher levels with integer gold costs
        gods_stone_cost = 1 + (upgrade_level // 3)
        # Use integer-based progression to avoid decimal gold costs
        gold_cost = int(50 * (1.5 ** upgrade_level))  # Convert to integer
        success_rate = max(30, 90 - (upgrade_level * 2))  # Slower decrease
        
        return {
            "gods_stone": gods_stone_cost,
            "gold": gold_cost,
            "success_rate": success_rate
        }

    def attempt_upgrade(self, item_id: str, upgrade_level: int) -> Dict[str, Any]:
        """Attempt to upgrade an item"""
        if upgrade_level >= 40:
            return {"success": False, "reason": "max_level"}
        
        cost = self.get_upgrade_cost(upgrade_level)
        success_rate = cost.get("success_rate", 50)
        
        # Roll for success
        success = random.randint(1, 100) <= success_rate
        
        result = {
            "success": success,
            "new_level": upgrade_level + 1 if success else upgrade_level,
            "materials_consumed": {
                "gods_stone": cost.get("gods_stone", 0),
                "gold": cost.get("gold", 0)
            }
        }
        
        return result

    def calculate_sell_price(self, item_id: str, upgrade_level: int = 0) -> int:
        """Calculate item sell price"""
        item = self.get_equipment_by_id(item_id)
        if not item:
            return 0
        
        # Base price + upgrade costs
        upgrade_value = 0
        for level in range(upgrade_level):
            cost = self.get_upgrade_cost(level)
            upgrade_value += cost.get("gold", 0)
        
        # Sell for 50% of total value
        return int((item.base_price + upgrade_value) * 0.5)

    def roll_material_drop(self, enemy_type: str, enemy_level: int = 1) -> Dict[str, int]:
        """Roll for material drops"""
        drops = {"gods_stone": 0, "mithril_dust": 0, "dragon_scale": 0}
        
        # Gods stone drop chance: 15% for all monsters in forest and dungeon
        if random.randint(1, 100) <= 15:
            drops["gods_stone"] = 1
        
        # Additional drops for special enemies
        if enemy_type.lower() in ["boss", "mini_boss"]:
            # Bosses have higher chance for additional materials
            if random.randint(1, 100) <= 25:
                drops["mithril_dust"] = 1
        elif enemy_type.lower() in ["dragon", "ancient"]:
            # Dragons have highest chance for rare materials
            if random.randint(1, 100) <= 5:
                drops["dragon_scale"] = 1
            if random.randint(1, 100) <= 35:
                drops["mithril_dust"] = 1
        
        # Level modifier for additional drops
        if enemy_level >= 10 and random.randint(1, 100) <= 8:
            drops["mithril_dust"] = 1
        
        return drops


