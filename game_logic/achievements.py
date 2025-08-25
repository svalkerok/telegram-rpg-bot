"""
Achievement system for Telegram RPG Bot "Легенди Валгаллії"
Manages achievements, rewards, and progress tracking
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class AchievementType(Enum):
    """Types of achievements"""
    COMBAT = "combat"
    EXPLORATION = "exploration"
    ECONOMIC = "economic"
    ARENA = "arena"
    SOCIAL = "social"
    SPECIAL = "special"


class RewardType(Enum):
    """Types of rewards"""
    EXPERIENCE = "experience"
    GOLD = "gold"
    ITEM = "item"
    TITLE = "title"


@dataclass
class AchievementReward:
    """Achievement reward data"""
    type: RewardType
    value: int
    item_id: Optional[str] = None
    title: Optional[str] = None


@dataclass
class Achievement:
    """Achievement definition"""
    id: str
    name: str
    description: str
    type: AchievementType
    condition: str  # Description of what needs to be done
    requirement_key: str  # Statistics key to check
    requirement_value: int  # Value needed to unlock
    rewards: List[AchievementReward]
    icon: str
    hidden: bool = False  # Hidden until unlocked
    
    def check_condition(self, stats: dict) -> bool:
        """Check if achievement condition is met"""
        current_value = stats.get(self.requirement_key, 0)
        # Ensure we're comparing numbers
        try:
            current_value = int(current_value) if current_value is not None else 0
        except (ValueError, TypeError):
            current_value = 0
        return current_value >= self.requirement_value


class AchievementManager:
    """Manages achievements and rewards"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.achievements = self._initialize_achievements()
    
    def _initialize_achievements(self) -> Dict[str, Achievement]:
        """Initialize all achievements"""
        achievements = {}
        
        # COMBAT ACHIEVEMENTS
        achievements["first_blood"] = Achievement(
            id="first_blood",
            name="Перша кров",
            description="Переможіть свого першого ворога",
            type=AchievementType.COMBAT,
            condition="Вбийте 1 ворога",
            requirement_key="enemies_killed",
            requirement_value=1,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 50),
                AchievementReward(RewardType.GOLD, 25)
            ],
            icon="⚔️"
        )
        
        achievements["mass_killer"] = Achievement(
            id="mass_killer",
            name="Масовий вбивця",
            description="Переможіть 100 ворогів",
            type=AchievementType.COMBAT,
            condition="Вбийте 100 ворогів",
            requirement_key="enemies_killed",
            requirement_value=100,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 500),
                AchievementReward(RewardType.GOLD, 200),
                AchievementReward(RewardType.TITLE, 0, title="Убивця")
            ],
            icon="💀"
        )
        
        achievements["slaughter_master"] = Achievement(
            id="slaughter_master",
            name="Майстер бойні",
            description="Переможіть 500 ворогів",
            type=AchievementType.COMBAT,
            condition="Вбийте 500 ворогів",
            requirement_key="enemies_killed",
            requirement_value=500,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 1000),
                AchievementReward(RewardType.GOLD, 500),
                AchievementReward(RewardType.ITEM, 0, item_id="legendary_sword")
            ],
            icon="🗡️"
        )
        
        achievements["critical_master"] = Achievement(
            id="critical_master",
            name="Критичний майстер",
            description="Завдайте 50 критичних ударів",
            type=AchievementType.COMBAT,
            condition="Завдайте 50 критичних ударів",
            requirement_key="critical_hits",
            requirement_value=50,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 300),
                AchievementReward(RewardType.GOLD, 150)
            ],
            icon="💥"
        )
        
        # EXPLORATION ACHIEVEMENTS
        achievements["dungeon_conqueror"] = Achievement(
            id="dungeon_conqueror",
            name="Переможець мертвих",
            description="Завершіть 10 підземель",
            type=AchievementType.EXPLORATION,
            condition="Завершіть 10 підземель",
            requirement_key="dungeons_completed",
            requirement_value=10,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 750),
                AchievementReward(RewardType.GOLD, 300),
                AchievementReward(RewardType.TITLE, 0, title="Дослідник підземель")
            ],
            icon="🏰"
        )
        
        achievements["dragon_slayer"] = Achievement(
            id="dragon_slayer",
            name="Драконобоєць",
            description="Переможіть дракона в Логові Дракона",
            type=AchievementType.EXPLORATION,
            condition="Переможіть фінального боса Логова Дракона",
            requirement_key="dragon_boss_kills",
            requirement_value=1,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 2000),
                AchievementReward(RewardType.GOLD, 1000),
                AchievementReward(RewardType.ITEM, 0, item_id="dragon_scale_armor"),
                AchievementReward(RewardType.TITLE, 0, title="Драконобоєць")
            ],
            icon="🐉"
        )
        
        achievements["forest_wanderer"] = Achievement(
            id="forest_wanderer",
            name="Мандрівник лісу",
            description="Виграйте 25 боїв у Темному лісі",
            type=AchievementType.EXPLORATION,
            condition="Переможіть у 25 боях в лісі",
            requirement_key="forest_wins",
            requirement_value=25,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 400),
                AchievementReward(RewardType.GOLD, 200)
            ],
            icon="🌲"
        )
        
        # ECONOMIC ACHIEVEMENTS
        achievements["rich"] = Achievement(
            id="rich",
            name="Багатий",
            description="Накопичіть 1000 золота",
            type=AchievementType.ECONOMIC,
            condition="Мати 1000 золота одночасно",
            requirement_key="max_gold_owned",
            requirement_value=1000,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 200),
                AchievementReward(RewardType.GOLD, 100)
            ],
            icon="💰"
        )
        
        achievements["millionaire"] = Achievement(
            id="millionaire",
            name="Мільйонер",
            description="Накопичіть 10000 золота",
            type=AchievementType.ECONOMIC,
            condition="Мати 10000 золота одночасно",
            requirement_key="max_gold_owned",
            requirement_value=10000,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 1000),
                AchievementReward(RewardType.GOLD, 500),
                AchievementReward(RewardType.TITLE, 0, title="Мільйонер")
            ],
            icon="💎"
        )
        
        achievements["trader"] = Achievement(
            id="trader",
            name="Торговець",
            description="Витратьте 5000 золота в магазині",
            type=AchievementType.ECONOMIC,
            condition="Витратити 5000 золота на покупки",
            requirement_key="gold_spent",
            requirement_value=5000,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 500),
                AchievementReward(RewardType.GOLD, 250),
                AchievementReward(RewardType.TITLE, 0, title="Майстер торгівлі")
            ],
            icon="🛒"
        )
        
        # ARENA ACHIEVEMENTS
        achievements["arena_champion"] = Achievement(
            id="arena_champion",
            name="Чемпіон арени",
            description="Виграйте 10 боїв на арені",
            type=AchievementType.ARENA,
            condition="Переможіть у 10 боях на арені",
            requirement_key="arena_wins",
            requirement_value=10,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 600),
                AchievementReward(RewardType.GOLD, 300),
                AchievementReward(RewardType.TITLE, 0, title="Чемпіон арени")
            ],
            icon="🏆"
        )
        
        achievements["undefeated"] = Achievement(
            id="undefeated",
            name="Непереможний",
            description="Виграйте 5 боїв на арені поспіль",
            type=AchievementType.ARENA,
            condition="Серія з 5 перемог на арені",
            requirement_key="arena_win_streak",
            requirement_value=5,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 800),
                AchievementReward(RewardType.GOLD, 400),
                AchievementReward(RewardType.ITEM, 0, item_id="champion_crown")
            ],
            icon="👑"
        )
        
        # SOCIAL ACHIEVEMENTS
        achievements["potion_master"] = Achievement(
            id="potion_master",
            name="Майстер зілля",
            description="Використайте 50 зілль",
            type=AchievementType.SOCIAL,
            condition="Використати 50 зілль",
            requirement_key="potions_used",
            requirement_value=50,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 300),
                AchievementReward(RewardType.GOLD, 150),
                AchievementReward(RewardType.ITEM, 0, item_id="alchemist_kit")
            ],
            icon="🧪"
        )
        
        achievements["survivor"] = Achievement(
            id="survivor",
            name="Виживший",
            description="Втечіть з бою 10 разів",
            type=AchievementType.SOCIAL,
            condition="Втекти з 10 боїв",
            requirement_key="battles_fled",
            requirement_value=10,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 100),
                AchievementReward(RewardType.GOLD, 50)
            ],
            icon="🏃"
        )
        
        # SPECIAL ACHIEVEMENTS
        achievements["level_master"] = Achievement(
            id="level_master",
            name="Майстер рівнів",
            description="Досягніть 10-го рівня",
            type=AchievementType.SPECIAL,
            condition="Досягти 10-го рівня",
            requirement_key="max_level_reached",
            requirement_value=10,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 1500),
                AchievementReward(RewardType.GOLD, 750),
                AchievementReward(RewardType.TITLE, 0, title="Майстер")
            ],
            icon="⭐"
        )
        
        achievements["legendary_hero"] = Achievement(
            id="legendary_hero",
            name="Легендарний герой",
            description="Досягніть 20-го рівня",
            type=AchievementType.SPECIAL,
            condition="Досягти 20-го рівня",
            requirement_key="max_level_reached",
            requirement_value=20,
            rewards=[
                AchievementReward(RewardType.EXPERIENCE, 3000),
                AchievementReward(RewardType.GOLD, 1500),
                AchievementReward(RewardType.ITEM, 0, item_id="legendary_artifact"),
                AchievementReward(RewardType.TITLE, 0, title="Легенда")
            ],
            icon="🌟",
            hidden=True
        )
        
        return achievements
    
    async def check_achievements(self, user_id: int) -> List[Achievement]:
        """Check for new achievements for user"""
        try:
            # Get user statistics
            stats = await self.db.get_statistics(user_id)
            if not stats:
                return []
            
            # Get character for level checking
            character = await self.db.get_character(user_id)
            if not character:
                return []
            
            # Convert stats to dict for easier checking (ensure all values are integers)
            def safe_int(value, default=0):
                try:
                    return int(value) if value is not None else default
                except (ValueError, TypeError):
                    return default
            
            stats_dict = {
                'enemies_killed': safe_int(stats.enemies_killed),
                'critical_hits': safe_int(stats.critical_hits),
                'dungeons_completed': safe_int(stats.dungeons_completed),
                'dragon_boss_kills': safe_int(getattr(stats, 'dragon_boss_kills', 0)),
                'forest_wins': safe_int(getattr(stats, 'forest_wins', 0)),
                'max_gold_owned': safe_int(getattr(stats, 'max_gold_owned', character.gold)),
                'gold_spent': safe_int(getattr(stats, 'gold_spent', 0)),
                'arena_wins': safe_int(stats.arena_wins),
                'arena_win_streak': safe_int(getattr(stats, 'arena_win_streak', 0)),
                'potions_used': safe_int(getattr(stats, 'potions_used', 0)),
                'battles_fled': safe_int(getattr(stats, 'battles_fled', 0)),
                'max_level_reached': safe_int(character.level)
            }
            
            # Get already earned achievements
            earned_achievements = await self.db.get_user_achievements(user_id)
            earned_ids = [ach['achievement_id'] for ach in earned_achievements] if earned_achievements else []
            
            # Check for new achievements
            new_achievements = []
            for achievement in self.achievements.values():
                if achievement.id not in earned_ids and achievement.check_condition(stats_dict):
                    new_achievements.append(achievement)
            
            return new_achievements
            
        except Exception as e:
            logger.error(f"Error checking achievements for user {user_id}: {e}")
            return []
    
    async def give_achievement_reward(self, user_id: int, achievement: Achievement) -> str:
        """Give rewards for achievement and return description"""
        try:
            reward_text = ""
            
            for reward in achievement.rewards:
                if reward.type == RewardType.EXPERIENCE:
                    # Add experience to character
                    character = await self.db.get_character(user_id)
                    if character:
                        from game_logic.character import CharacterManager
                        char_manager = CharacterManager(self.db)
                        exp_result = char_manager.add_experience(character, reward.value)
                        await self.db.update_character(character)
                        
                        reward_text += f"⚡ +{reward.value} досвіду\n"
                        if exp_result and exp_result.get('level_up'):
                            reward_text += f"🎉 Рівень підвищено до {exp_result['new_level']}!\n"
                
                elif reward.type == RewardType.GOLD:
                    # Add gold to character
                    character = await self.db.get_character(user_id)
                    if character:
                        character.gold += reward.value
                        await self.db.update_character(character)
                    reward_text += f"💰 +{reward.value} золота\n"
                
                elif reward.type == RewardType.TITLE:
                    # Add title to character (could be stored in a titles table)
                    reward_text += f"🏅 Новий титул: **{reward.title}**\n"
                
                elif reward.type == RewardType.ITEM:
                    # Add item to inventory
                    from database.database_models import InventoryItem
                    item_name = self._get_item_name(reward.item_id)
                    
                    inventory_item = InventoryItem(
                        item_id=reward.item_id,
                        user_id=user_id,
                        item_type='special',
                        name=item_name,
                        description=f"Нагорода за досягнення: {achievement.name}",
                        quantity=1,
                        properties={'achievement_reward': True, 'achievement_id': achievement.id}
                    )
                    
                    await self.db.add_item_to_inventory(user_id, inventory_item)
                    reward_text += f"🎁 Отримано предмет: **{item_name}**\n"
            
            # Record achievement
            await self.db.add_user_achievement(user_id, achievement.id)
            
            return reward_text.strip()
            
        except Exception as e:
            logger.error(f"Error giving achievement reward: {e}")
            return "❌ Помилка при видачі нагороди"
    
    def _get_item_name(self, item_id: str) -> str:
        """Get item name by ID"""
        item_names = {
            'legendary_sword': 'Легендарний меч',
            'dragon_scale_armor': 'Обладунки з драконячої луски',
            'champion_crown': 'Корона чемпіона',
            'alchemist_kit': 'Набір алхіміка',
            'legendary_artifact': 'Легендарний артефакт'
        }
        return item_names.get(item_id, item_id.replace('_', ' ').title())
    
    def get_achievement_by_id(self, achievement_id: str) -> Optional[Achievement]:
        """Get achievement by ID"""
        return self.achievements.get(achievement_id)
    
    def get_achievements_by_type(self, achievement_type: AchievementType) -> List[Achievement]:
        """Get all achievements of specific type"""
        return [ach for ach in self.achievements.values() if ach.type == achievement_type]
    
    def get_all_achievements(self) -> List[Achievement]:
        """Get all achievements"""
        return list(self.achievements.values())
