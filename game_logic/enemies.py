"""
Enemy system for Telegram RPG Bot "Легенди Валгаллії"
Enemy classes and enemy management
"""

import logging
import json
import random
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from game_logic.items import ItemType

logger = logging.getLogger(__name__)


class EnemyType(Enum):
    """Enemy types for different locations"""
    FOREST = "forest"
    DUNGEON = "dungeon"
    ARENA = "arena"
    BOSS = "boss"
    ELITE = "elite"
    MINION = "minion"


class EnemyBehavior(Enum):
    """Enemy AI behaviors"""
    AGGRESSIVE = "aggressive"  # Always attacks
    DEFENSIVE = "defensive"   # Often blocks/defends
    BALANCED = "balanced"     # Mix of attack and defense
    BERSERKER = "berserker"   # High damage, low defense
    COWARD = "coward"         # Tries to flee when low HP


@dataclass
class Enemy:
    """Enemy data class with full combat stats"""
    enemy_id: str
    name: str
    description: str
    level: int
    enemy_type: EnemyType
    behavior: EnemyBehavior = EnemyBehavior.BALANCED
    
    # Combat stats
    max_health: int = 100
    health: int = 100
    attack: int = 10
    defense: int = 5
    magic_power: int = 0
    speed: int = 10
    critical_chance: int = 5
    block_chance: int = 10
    
    # Special abilities
    special_abilities: List[str] = field(default_factory=list)
    magic_resistance: int = 0  # % magic damage reduction
    physical_resistance: int = 0  # % physical damage reduction
    
    # Rewards
    experience_reward: int = 50
    gold_min: int = 10
    gold_max: int = 20
    drop_table: List[Dict[str, Any]] = field(default_factory=list)
    
    # Appearance
    emoji: str = "👹"
    
    def __post_init__(self):
        """Initialize health to max_health if not set"""
        if self.health == 100 and self.max_health != 100:
            self.health = self.max_health
    
    def is_alive(self) -> bool:
        """Check if enemy is still alive"""
        return self.health > 0
    
    def take_damage(self, damage: int, damage_type: str = "physical") -> int:
        """Take damage with resistance calculation"""
        original_damage = damage
        
        # Apply resistances
        if damage_type == "physical" and self.physical_resistance > 0:
            damage = max(1, damage - (damage * self.physical_resistance // 100))
        elif damage_type == "magic" and self.magic_resistance > 0:
            damage = max(1, damage - (damage * self.magic_resistance // 100))
        
        self.health = max(0, self.health - damage)
        return damage  # Return actual damage taken
    
    def heal(self, amount: int) -> int:
        """Heal enemy (used by some abilities)"""
        old_health = self.health
        self.health = min(self.max_health, self.health + amount)
        return self.health - old_health
    
    def get_health_percentage(self) -> float:
        """Get current health as percentage"""
        return (self.health / self.max_health) * 100
    
    def should_use_ability(self) -> bool:
        """Determine if enemy should use special ability"""
        # More likely to use abilities when low on health
        health_pct = self.get_health_percentage()
        
        base_chance = 15  # 15% base chance
        if health_pct < 30:
            base_chance = 40  # 40% when critically low
        elif health_pct < 50:
            base_chance = 25  # 25% when moderately low
        
        return random.randint(1, 100) <= base_chance
    
    def get_display_info(self, show_health: bool = True) -> str:
        """Get formatted enemy display info"""
        lines = [f"{self.emoji} **{self.name}**"]
        
        if show_health:
            health_bar = self._get_health_bar()
            lines.append(f"❤️ {self.health}/{self.max_health} {health_bar}")
        
        lines.append(f"⭐ Рівень: {self.level}")
        
        if self.description:
            lines.append(f"_{self.description}_")
        
        return "\n".join(lines)
    
    def _get_health_bar(self, length: int = 10) -> str:
        """Generate visual health bar"""
        health_pct = self.get_health_percentage()
        filled = int((health_pct / 100) * length)
        empty = length - filled
        
        if health_pct > 60:
            bar_char = "🟩"
        elif health_pct > 30:
            bar_char = "🟨"
        else:
            bar_char = "🟥"
        
        return bar_char * filled + "⬜" * empty
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'enemy_id': self.enemy_id,
            'name': self.name,
            'description': self.description,
            'level': self.level,
            'enemy_type': self.enemy_type.value,
            'behavior': self.behavior.value,
            'max_health': self.max_health,
            'attack': self.attack,
            'defense': self.defense,
            'magic_power': self.magic_power,
            'speed': self.speed,
            'critical_chance': self.critical_chance,
            'block_chance': self.block_chance,
            'special_abilities': self.special_abilities,
            'magic_resistance': self.magic_resistance,
            'physical_resistance': self.physical_resistance,
            'experience_reward': self.experience_reward,
            'gold_min': self.gold_min,
            'gold_max': self.gold_max,
            'drop_table': self.drop_table,
            'emoji': self.emoji
        }


class EnemyManager:
    """Manage all enemies in the game"""
    
    def __init__(self):
        self.enemies: Dict[str, Enemy] = {}
        self.forest_enemies: List[str] = []
        self.dungeon_enemies: List[str] = []
        self.arena_enemies: List[str] = []
        self.boss_enemies: List[str] = []
        self._item_manager = None
        
        self._initialize_enemies()
    
    @property
    def item_manager(self):
        """Lazy initialization of ItemManager"""
        if self._item_manager is None:
            from game_logic.items import ItemManager
            self._item_manager = ItemManager()
        return self._item_manager
    
    def _initialize_enemies(self):
        """Initialize enemy catalog"""
        try:
            self.load_enemies_from_file()
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("Creating default enemy catalog...")
            self._create_default_enemies()
            self.save_enemies_to_file()
    
    def _create_default_enemies(self):
        """Create default enemy catalog with diverse creatures"""
        
        # === FOREST ENEMIES ===
        forest_enemies = [
            # Level 1-3 enemies
            Enemy("forest_wolf", "Лісний вовк", "Голодний вовк шукає здобич", 1, EnemyType.FOREST, EnemyBehavior.AGGRESSIVE,
                  50, 50, 12, 3, 0, 15, 8, 5, ["howl"], 0, 0, 25, 8, 15, 
                  [{"item_id": "wolf_pelt", "chance": 0.3}, {"item_id": "small_health_potion", "chance": 0.2}], "🐺"),
            
            Enemy("giant_spider", "Гігантський павук", "Отруйний павук з великими кліщами", 2, EnemyType.FOREST, EnemyBehavior.DEFENSIVE,
                  35, 35, 10, 2, 0, 12, 5, 15, ["poison_bite", "web_trap"], 0, 0, 30, 12, 20,
                  [{"item_id": "spider_silk", "chance": 0.4}, {"item_id": "poison_gland", "chance": 0.2}], "🕷️"),
            
            Enemy("wild_boar", "Дикий кабан", "Розлючений кабан з гострими іклами", 2, EnemyType.FOREST, EnemyBehavior.BERSERKER,
                  60, 60, 18, 8, 0, 8, 12, 8, ["charge", "rage"], 0, 15, 35, 15, 25,
                  [{"item_id": "boar_hide", "chance": 0.35}, {"item_id": "tusks", "chance": 0.15}], "🐗"),
            
            Enemy("forest_bandit", "Лісний розбійник", "Хитрий розбійник який грабує мандрівників", 3, EnemyType.FOREST, EnemyBehavior.BALANCED,
                  70, 70, 20, 12, 0, 18, 15, 12, ["sneak_attack", "steal"], 0, 0, 45, 20, 35,
                  [{"item_id": "bronze_dagger", "chance": 0.2}, {"item_id": "leather_armor", "chance": 0.15}], "🏹"),
            
            # Level 4-6 enemies
            Enemy("dire_wolf", "Лютий вовк", "Величезний альфа-вовк з червоними очима", 5, EnemyType.FOREST, EnemyBehavior.AGGRESSIVE,
                  90, 90, 28, 15, 0, 20, 18, 10, ["pack_howl", "fury"], 0, 0, 75, 35, 50,
                  [{"item_id": "dire_wolf_fang", "chance": 0.3}, {"item_id": "health_potion", "chance": 0.25}], "🐺"),
            
            Enemy("forest_troll", "Лісний троль", "Величезний троль з моховою шкірою", 6, EnemyType.FOREST, EnemyBehavior.DEFENSIVE,
                  120, 120, 35, 25, 0, 8, 8, 20, ["regeneration", "tree_smash"], 0, 30, 100, 45, 70,
                  [{"item_id": "troll_moss", "chance": 0.4}, {"item_id": "war_hammer", "chance": 0.1}], "🧌"),
        ]
        
        # === DUNGEON ENEMIES ===
        dungeon_enemies = [
            # Level 1-4 undead
            Enemy("skeleton_warrior", "Скелет-воїн", "Кістки гримлять при кожному кроці", 2, EnemyType.DUNGEON, EnemyBehavior.BALANCED,
                  40, 40, 15, 8, 0, 12, 5, 18, ["bone_throw"], 0, 20, 40, 18, 30,
                  [{"item_id": "bone_fragment", "chance": 0.5}, {"item_id": "rusty_sword", "chance": 0.15}], "💀"),
            
            Enemy("zombie", "Гнилий зомбі", "Повільний але стійкий до пошкоджень", 1, EnemyType.DUNGEON, EnemyBehavior.AGGRESSIVE,
                  60, 60, 12, 4, 0, 6, 3, 5, ["disease"], 0, 25, 25, 10, 20,
                  [{"item_id": "rotten_flesh", "chance": 0.3}, {"item_id": "small_health_potion", "chance": 0.2}], "🧟"),
            
            Enemy("ghost", "Примарний дух", "Невловимий дух який пройшов крізь століття", 3, EnemyType.DUNGEON, EnemyBehavior.COWARD,
                  30, 30, 8, 2, 25, 25, 20, 30, ["phase", "chill_touch"], 50, 0, 50, 25, 40,
                  [{"item_id": "ectoplasm", "chance": 0.4}, {"item_id": "mana_potion", "chance": 0.2}], "👻"),
            
            Enemy("orc_warrior", "Орк-воїн", "Брутальний воїн з великою сокирою", 4, EnemyType.DUNGEON, EnemyBehavior.BERSERKER,
                  80, 80, 30, 15, 0, 10, 20, 8, ["berserker_rage", "intimidate"], 0, 10, 70, 30, 50,
                  [{"item_id": "orc_axe", "chance": 0.25}, {"item_id": "chainmail", "chance": 0.15}], "👹"),
            
            # Level 5-8 stronger enemies
            Enemy("death_knight", "Лицар Смерті", "Колишній лицар занурений у темну магію", 7, EnemyType.DUNGEON, EnemyBehavior.DEFENSIVE,
                  140, 140, 40, 30, 20, 15, 25, 25, ["death_strike", "dark_aura"], 30, 20, 120, 60, 90,
                  [{"item_id": "cursed_blade", "chance": 0.2}, {"item_id": "death_essence", "chance": 0.3}], "☠️"),
            
            Enemy("lich", "Ліч", "Могутній некромант який керує нежиттю", 8, EnemyType.DUNGEON, EnemyBehavior.BALANCED,
                  100, 100, 25, 15, 50, 20, 30, 15, ["summon_skeleton", "life_drain", "ice_lance"], 40, 10, 150, 70, 100,
                  [{"item_id": "necromantic_tome", "chance": 0.15}, {"item_id": "arcane_staff", "chance": 0.1}], "🧙‍♂️"),
        ]
        
        # === ARENA ENEMIES ===
        arena_enemies = [
            # Gladiators and champions
            Enemy("arena_gladiator", "Арена гладіатор", "Досвідчений боєць арени", 5, EnemyType.ARENA, EnemyBehavior.BALANCED,
                  100, 100, 35, 20, 0, 22, 20, 15, ["combat_expertise", "second_wind"], 0, 0, 90, 50, 80,
                  [{"item_id": "gladiator_helmet", "chance": 0.2}, {"item_id": "arena_coin", "chance": 0.8}], "⚔️"),
            
            Enemy("champion_knight", "Чемпіон-лицар", "Непереможний лицар арени", 8, EnemyType.ARENA, EnemyBehavior.DEFENSIVE,
                  160, 160, 45, 35, 0, 18, 25, 30, ["shield_bash", "divine_protection"], 0, 25, 180, 90, 120,
                  [{"item_id": "champion_sword", "chance": 0.15}, {"item_id": "plate_armor", "chance": 0.1}], "🛡️"),
            
            Enemy("arena_mage", "Арена маг", "Могутній маг майстер бойової магії", 7, EnemyType.ARENA, EnemyBehavior.AGGRESSIVE,
                  80, 80, 20, 10, 60, 25, 35, 20, ["fireball", "lightning_bolt", "magic_shield"], 20, 0, 140, 70, 110,
                  [{"item_id": "battle_staff", "chance": 0.2}, {"item_id": "mage_robes", "chance": 0.15}], "🔮"),
        ]
        
        # === BOSS ENEMIES ===
        boss_enemies = [
            Enemy("forest_king", "Король Лісу", "Древній хранитель лісу з величезною силою", 10, EnemyType.BOSS, EnemyBehavior.BALANCED,
                  300, 300, 60, 40, 30, 25, 30, 25, ["nature_wrath", "forest_blessing", "root_bind"], 25, 25, 400, 150, 250,
                  [{"item_id": "crown_of_forest", "chance": 0.8}, {"item_id": "nature_essence", "chance": 1.0}], "🌳"),
            
            Enemy("dungeon_overlord", "Володар Підземелля", "Темний повелитель всіх підземних жахів", 12, EnemyType.BOSS, EnemyBehavior.AGGRESSIVE,
                  400, 400, 80, 50, 40, 20, 35, 20, ["summon_minions", "dark_magic", "terror"], 40, 30, 600, 200, 350,
                  [{"item_id": "overlord_crown", "chance": 0.9}, {"item_id": "shadow_blade", "chance": 0.5}], "👑"),
            
            Enemy("arena_champion", "Чемпіон Арени", "Непереможний чемпіон що тримає титул роками", 15, EnemyType.BOSS, EnemyBehavior.BALANCED,
                  500, 500, 100, 60, 20, 30, 40, 35, ["champion_strike", "arena_mastery", "crowd_roar"], 20, 40, 800, 300, 500,
                  [{"item_id": "champion_belt", "chance": 1.0}, {"item_id": "legendary_weapon", "chance": 0.3}], "🏆"),
        ]
        
        # Add all enemies to catalog
        all_enemies = forest_enemies + dungeon_enemies + arena_enemies + boss_enemies
        
        for enemy in all_enemies:
            self.add_enemy(enemy)
    
    def add_enemy(self, enemy: Enemy):
        """Add enemy to catalog and categorize"""
        self.enemies[enemy.enemy_id] = enemy
        
        # Categorize by type
        if enemy.enemy_type == EnemyType.FOREST:
            self.forest_enemies.append(enemy.enemy_id)
        elif enemy.enemy_type == EnemyType.DUNGEON:
            self.dungeon_enemies.append(enemy.enemy_id)
        elif enemy.enemy_type == EnemyType.ARENA:
            self.arena_enemies.append(enemy.enemy_id)
        elif enemy.enemy_type == EnemyType.BOSS:
            self.boss_enemies.append(enemy.enemy_id)
    
    def get_enemy(self, enemy_id: str) -> Optional[Enemy]:
        """Get enemy by ID (returns a fresh copy)"""
        enemy_template = self.enemies.get(enemy_id)
        if not enemy_template:
            return None
        
        # Return a fresh copy with full health
        enemy_copy = Enemy(
            enemy_id=enemy_template.enemy_id,
            name=enemy_template.name,
            description=enemy_template.description,
            level=enemy_template.level,
            enemy_type=enemy_template.enemy_type,
            behavior=enemy_template.behavior,
            max_health=enemy_template.max_health,
            health=enemy_template.max_health,  # Fresh copy has full health
            attack=enemy_template.attack,
            defense=enemy_template.defense,
            magic_power=enemy_template.magic_power,
            speed=enemy_template.speed,
            critical_chance=enemy_template.critical_chance,
            block_chance=enemy_template.block_chance,
            special_abilities=enemy_template.special_abilities.copy(),
            magic_resistance=enemy_template.magic_resistance,
            physical_resistance=enemy_template.physical_resistance,
            experience_reward=enemy_template.experience_reward,
            gold_min=enemy_template.gold_min,
            gold_max=enemy_template.gold_max,
            drop_table=enemy_template.drop_table.copy(),
            emoji=enemy_template.emoji
        )
        
        return enemy_copy
    
    def get_random_enemy_for_location(self, location: EnemyType, character_level: int, 
                                     difficulty_modifier: float = 1.0) -> Optional[Enemy]:
        """Get random enemy suitable for location and character level"""
        
        # Get enemy list for location
        if location == EnemyType.FOREST:
            enemy_list = self.forest_enemies
        elif location == EnemyType.DUNGEON:
            enemy_list = self.dungeon_enemies
        elif location == EnemyType.ARENA:
            enemy_list = self.arena_enemies
        else:
            enemy_list = list(self.enemies.keys())
        
        # Filter by appropriate level range
        level_range = 2  # ±2 levels from character
        suitable_enemies = []
        
        for enemy_id in enemy_list:
            enemy_template = self.enemies[enemy_id]
            if (character_level - level_range <= enemy_template.level <= character_level + level_range and
                enemy_template.enemy_type != EnemyType.BOSS):  # No random bosses
                suitable_enemies.append(enemy_id)
        
        if not suitable_enemies:
            # Fallback to any appropriate level enemy
            for enemy_id, enemy_template in self.enemies.items():
                if (character_level - level_range <= enemy_template.level <= character_level + level_range and
                    enemy_template.enemy_type != EnemyType.BOSS):
                    suitable_enemies.append(enemy_id)
        
        if not suitable_enemies:
            return None
        
        # Select random enemy
        enemy_id = random.choice(suitable_enemies)
        enemy = self.get_enemy(enemy_id)
        
        if enemy and difficulty_modifier != 1.0:
            enemy = self.scale_enemy_difficulty(enemy, difficulty_modifier)
        
        return enemy
    
    def scale_enemy_difficulty(self, enemy: Enemy, difficulty_modifier: float) -> Enemy:
        """Scale enemy stats by difficulty modifier"""
        enemy.max_health = int(enemy.max_health * difficulty_modifier)
        enemy.health = enemy.max_health
        enemy.attack = int(enemy.attack * difficulty_modifier)
        enemy.defense = int(enemy.defense * difficulty_modifier)
        enemy.magic_power = int(enemy.magic_power * difficulty_modifier)
        enemy.experience_reward = int(enemy.experience_reward * difficulty_modifier)
        enemy.gold_min = int(enemy.gold_min * difficulty_modifier)
        enemy.gold_max = int(enemy.gold_max * difficulty_modifier)
        
        return enemy
    
    def get_boss_enemy(self, boss_id: str) -> Optional[Enemy]:
        """Get specific boss enemy"""
        if boss_id in self.boss_enemies:
            return self.get_enemy(boss_id)
        return None
    
    def get_enemies_by_type(self, enemy_type: EnemyType) -> List[Enemy]:
        """Get all enemies of specific type"""
        return [self.get_enemy(enemy_id) for enemy_id in self.enemies.keys() 
                if self.enemies[enemy_id].enemy_type == enemy_type]
    
    def get_enemies_by_level_range(self, min_level: int, max_level: int) -> List[Enemy]:
        """Get enemies within level range"""
        suitable_enemies = []
        for enemy in self.enemies.values():
            if min_level <= enemy.level <= max_level:
                suitable_enemies.append(self.get_enemy(enemy.enemy_id))
        return suitable_enemies
    
    def calculate_loot_drops(self, enemy: Enemy) -> List[str]:
        """Calculate which items drop from defeated enemy"""
        dropped_items = []
        
        for drop in enemy.drop_table:
            if random.random() < drop.get("chance", 0.1):
                dropped_items.append(drop["item_id"])
        
        return dropped_items
    
    def get_enemy_info_display(self, enemy: Enemy, detailed: bool = False) -> str:
        """Get formatted enemy information display"""
        lines = [
            f"{enemy.emoji} **{enemy.name}**",
            f"_{enemy.description}_",
            "",
            f"⭐ **Рівень:** {enemy.level}",
            f"❤️ **Здоров'я:** {enemy.max_health}",
            f"⚔️ **Атака:** {enemy.attack}",
            f"🛡️ **Захист:** {enemy.defense}",
            f"⚡ **Швидкість:** {enemy.speed}"
        ]
        
        if enemy.magic_power > 0:
            lines.append(f"🔮 **Магічна сила:** {enemy.magic_power}")
        
        if detailed:
            lines.extend([
                f"💥 **Шанс криту:** {enemy.critical_chance}%",
                f"🛡️ **Шанс блоку:** {enemy.block_chance}%"
            ])
            
            if enemy.physical_resistance > 0:
                lines.append(f"⚔️ **Фізичний опір:** {enemy.physical_resistance}%")
            
            if enemy.magic_resistance > 0:
                lines.append(f"🔮 **Магічний опір:** {enemy.magic_resistance}%")
            
            if enemy.special_abilities:
                abilities = ", ".join(enemy.special_abilities)
                lines.append(f"✨ **Спеціальні здібності:** {abilities}")
            
            lines.extend([
                "",
                f"💰 **Нагорода:** {enemy.gold_min}-{enemy.gold_max} золота",
                f"⭐ **Досвід:** {enemy.experience_reward} XP"
            ])
            
            if enemy.drop_table:
                lines.append("🎁 **Можливий лут:**")
                for drop in enemy.drop_table[:3]:  # Show first 3 items
                    chance_pct = int(drop.get("chance", 0) * 100)
                    lines.append(f"  • {drop['item_id']} ({chance_pct}%)")
        
        return "\n".join(lines)
    
    def load_enemies_from_file(self):
        """Load enemies from JSON file"""
        enemies_file = Path('data/enemies.json')
        if enemies_file.exists():
            with open(enemies_file, 'r', encoding='utf-8') as f:
                enemies_data = json.load(f)
            
            for enemy_id, enemy_info in enemies_data.items():
                # Handle both old and new format
                if 'enemy_type' not in enemy_info:
                    # Old format - convert to new
                    enemy = Enemy(
                        enemy_id=enemy_id,
                        name=enemy_info['name'],
                        description=enemy_info.get('description', ''),
                        level=enemy_info.get('level', 1),
                        enemy_type=EnemyType.FOREST,  # Default
                        max_health=enemy_info.get('health', 50),
                        attack=enemy_info.get('attack', 10),
                        defense=enemy_info.get('defense', 5),
                        speed=enemy_info.get('speed', 10),
                        experience_reward=enemy_info.get('experience_reward', 25),
                        gold_min=enemy_info.get('gold_min', 10),
                        gold_max=enemy_info.get('gold_max', 20)
                    )
                else:
                    # New format
                    enemy = Enemy(
                        enemy_id=enemy_id,
                        name=enemy_info['name'],
                        description=enemy_info['description'],
                        level=enemy_info['level'],
                        enemy_type=EnemyType(enemy_info['enemy_type']),
                        behavior=EnemyBehavior(enemy_info.get('behavior', 'balanced')),
                        max_health=enemy_info['max_health'],
                        attack=enemy_info['attack'],
                        defense=enemy_info['defense'],
                        magic_power=enemy_info.get('magic_power', 0),
                        speed=enemy_info['speed'],
                        critical_chance=enemy_info.get('critical_chance', 5),
                        block_chance=enemy_info.get('block_chance', 10),
                        special_abilities=enemy_info.get('special_abilities', []),
                        magic_resistance=enemy_info.get('magic_resistance', 0),
                        physical_resistance=enemy_info.get('physical_resistance', 0),
                        experience_reward=enemy_info['experience_reward'],
                        gold_min=enemy_info['gold_min'],
                        gold_max=enemy_info['gold_max'],
                        drop_table=enemy_info.get('drop_table', []),
                        emoji=enemy_info.get('emoji', '👹')
                    )
                
                self.add_enemy(enemy)
            
            logger.info(f"Loaded {len(self.enemies)} enemies from file")
    
    def save_enemies_to_file(self):
        """Save enemies to JSON file"""
        enemies_file = Path('data/enemies.json')
        enemies_file.parent.mkdir(exist_ok=True)
        
        enemies_data = {}
        for enemy_id, enemy in self.enemies.items():
            enemies_data[enemy_id] = enemy.to_dict()
        
        with open(enemies_file, 'w', encoding='utf-8') as f:
            json.dump(enemies_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(enemies_data)} enemies to file")


# Special ability implementations
class EnemyAbilities:
    """Special abilities that enemies can use"""
    
    @staticmethod
    def howl(enemy: Enemy, character) -> Dict[str, Any]:
        """Wolf howl - reduces character accuracy"""
        return {
            'success': True,
            'message': f"{enemy.name} виє, викликаючи страх!",
            'effect': 'intimidate',
            'duration': 2
        }
    
    @staticmethod
    def poison_bite(enemy: Enemy, character) -> Dict[str, Any]:
        """Poison bite - deals damage over time"""
        poison_damage = enemy.attack // 3
        return {
            'success': True,
            'message': f"{enemy.name} кусає отруйними зубами!",
            'damage': poison_damage,
            'effect': 'poison',
            'duration': 3
        }
    
    @staticmethod
    def regeneration(enemy: Enemy, character) -> Dict[str, Any]:
        """Troll regeneration - heals enemy"""
        heal_amount = enemy.max_health // 10
        actual_heal = enemy.heal(heal_amount)
        return {
            'success': True,
            'message': f"{enemy.name} регенерує {actual_heal} здоров'я!",
            'heal': actual_heal
        }
    
    @staticmethod
    def berserker_rage(enemy: Enemy, character) -> Dict[str, Any]:
        """Berserker rage - increases attack but reduces defense"""
        return {
            'success': True,
            'message': f"{enemy.name} впадає в берсерківський гнів!",
            'effect': 'rage',
            'attack_bonus': 10,
            'defense_penalty': 5,
            'duration': 3
        }


# Global enemy manager instance - initialize when needed
# enemy_manager = EnemyManager()  # Moved to lazy initialization
