"""
Daily quests system for Telegram RPG Bot "Легенди Валгаллії"
Manages daily quests, progress tracking, and rewards
"""

import logging
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Київський часовий пояс
KYIV_TZ = timezone(timedelta(hours=3))


class QuestType(Enum):
    """Types of daily quests"""
    FOREST_CLEARING = "forest_clearing"
    DUNGEON_EXPLORER = "dungeon_explorer"
    ARENA_CHAMPION = "arena_champion"
    TREASURE_COLLECTOR = "treasure_collector"
    BATTLE_MASTER = "battle_master"
    SURVIVOR = "survivor"
    TRADER = "trader"


class QuestStatus(Enum):
    """Quest completion status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CLAIMED = "claimed"


@dataclass
class QuestReward:
    """Daily quest reward data"""
    experience: int = 0
    gold: int = 0
    item_id: Optional[str] = None
    item_name: Optional[str] = None


@dataclass
class DailyQuest:
    """Daily quest definition"""
    id: str
    quest_type: QuestType
    name: str
    description: str
    requirement: int
    current_progress: int
    reward: QuestReward
    status: QuestStatus
    icon: str
    
    @property
    def is_completed(self) -> bool:
        """Check if quest is completed"""
        return self.current_progress >= self.requirement
    
    @property
    def progress_percentage(self) -> int:
        """Get progress as percentage"""
        return min(100, int((self.current_progress / self.requirement) * 100))
    
    def get_progress_bar(self) -> str:
        """Get visual progress bar"""
        filled = min(10, int(self.progress_percentage / 10))
        empty = 10 - filled
        return "█" * filled + "░" * empty


class DailyQuestManager:
    """Manages daily quests system"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.quest_templates = self._initialize_quest_templates()
    
    def _initialize_quest_templates(self) -> Dict[QuestType, dict]:
        """Initialize quest templates"""
        return {
            QuestType.FOREST_CLEARING: {
                "name": "Очищення лісу",
                "description": "Вбийте {} лісових створінь",
                "icon": "🌲",
                "requirements": [5, 8, 12],
                "rewards": {
                    "experience": [60, 80, 100],
                    "gold": [40, 60, 80],
                    "items": ["health_potion", "strength_potion", "mana_potion"]
                }
            },
            QuestType.DUNGEON_EXPLORER: {
                "name": "Дослідник підземель",
                "description": "Завершіть {} підземелля",
                "icon": "🏰",
                "requirements": [1, 2, 3],
                "rewards": {
                    "experience": [80, 100, 120],
                    "gold": [60, 80, 100],
                    "items": ["defense_potion", "health_potion_large", "regeneration_potion"]
                }
            },
            QuestType.ARENA_CHAMPION: {
                "name": "Чемпіон арени",
                "description": "Виграйте {} боїв на арені",
                "icon": "⚔️",
                "requirements": [3, 5, 7],
                "rewards": {
                    "experience": [70, 90, 110],
                    "gold": [50, 70, 90],
                    "items": ["strength_potion", "speed_potion", "health_potion"]
                }
            },
            QuestType.TREASURE_COLLECTOR: {
                "name": "Збирач скарбів",
                "description": "Накопичіть {} золота за день",
                "icon": "💰",
                "requirements": [150, 200, 300],
                "rewards": {
                    "experience": [50, 70, 90],
                    "gold": [30, 50, 70],
                    "items": ["mana_potion", "health_potion", "strength_potion"]
                }
            },
            QuestType.BATTLE_MASTER: {
                "name": "Майстер бою",
                "description": "Завдайте {} урону за день",
                "icon": "💥",
                "requirements": [300, 500, 800],
                "rewards": {
                    "experience": [60, 80, 100],
                    "gold": [40, 60, 80],
                    "items": ["strength_potion", "speed_potion", "health_potion_large"]
                }
            },
            QuestType.SURVIVOR: {
                "name": "Виживший",
                "description": "Не втрачайте HP протягом {} боїв",
                "icon": "🛡",
                "requirements": [3, 5, 8],
                "rewards": {
                    "experience": [70, 90, 110],
                    "gold": [50, 70, 90],
                    "items": ["defense_potion", "regeneration_potion", "health_potion_large"]
                }
            },
            QuestType.TRADER: {
                "name": "Торговець",
                "description": "Купіть {} предметів у магазині",
                "icon": "🛒",
                "requirements": [2, 3, 5],
                "rewards": {
                    "experience": [40, 60, 80],
                    "gold": [30, 50, 70],
                    "items": ["mana_potion", "health_potion", "strength_potion"]
                }
            }
        }
    
    def _get_kyiv_date(self) -> str:
        """Get current date in Kyiv timezone"""
        now = datetime.now(KYIV_TZ)
        return now.strftime("%Y-%m-%d")
    
    def _is_new_day(self, last_reset: str) -> bool:
        """Check if it's a new day since last reset"""
        if not last_reset:
            return True
        
        current_date = self._get_kyiv_date()
        return last_reset != current_date
    
    async def check_daily_reset(self, user_id: int) -> bool:
        """Check if daily quests need to be reset"""
        try:
            # Get user's last quest reset date
            last_reset = await self.db.get_user_data(user_id, 'last_quest_reset')
            
            if self._is_new_day(last_reset):
                await self._reset_daily_quests(user_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking daily reset for user {user_id}: {e}")
            return False
    
    async def _reset_daily_quests(self, user_id: int) -> None:
        """Reset daily quests for new day"""
        try:
            # Clear old quests
            await self.db.clear_daily_quests(user_id)
            
            # Generate new quests
            new_quests = self._generate_daily_quests()
            
            # Save new quests
            for quest in new_quests:
                await self.db.save_daily_quest(user_id, quest)
            
            # Update last reset date
            current_date = self._get_kyiv_date()
            await self.db.set_user_data(user_id, 'last_quest_reset', current_date)
            
            logger.info(f"Reset daily quests for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error resetting daily quests for user {user_id}: {e}")
    
    def _generate_daily_quests(self) -> List[DailyQuest]:
        """Generate 3 random daily quests"""
        quest_types = list(QuestType)
        selected_types = random.sample(quest_types, 3)
        
        quests = []
        for i, quest_type in enumerate(selected_types):
            template = self.quest_templates[quest_type]
            
            # Random difficulty
            difficulty = random.randint(0, 2)
            requirement = template["requirements"][difficulty]
            
            # Generate quest
            quest = DailyQuest(
                id=f"daily_{quest_type.value}_{i}",
                quest_type=quest_type,
                name=template["name"],
                description=template["description"].format(requirement),
                requirement=requirement,
                current_progress=0,
                reward=QuestReward(
                    experience=template["rewards"]["experience"][difficulty],
                    gold=template["rewards"]["gold"][difficulty],
                    item_id=template["rewards"]["items"][difficulty],
                    item_name=self._get_item_name(template["rewards"]["items"][difficulty])
                ),
                status=QuestStatus.ACTIVE,
                icon=template["icon"]
            )
            
            quests.append(quest)
        
        return quests
    
    def _get_item_name(self, item_id: str) -> str:
        """Get item display name"""
        item_names = {
            'health_potion_small': 'Мале зілля здоров\'я',
            'health_potion': 'Зілля здоров\'я',
            'health_potion_large': 'Велике зілля здоров\'я',
            'mana_potion': 'Зілля мани',
            'strength_potion': 'Зілля сили',
            'defense_potion': 'Зілля захисту',
            'speed_potion': 'Зілля швидкості',
            'regeneration_potion': 'Зілля регенерації'
        }
        return item_names.get(item_id, item_id.replace('_', ' ').title())
    
    async def get_daily_quests(self, user_id: int) -> List[DailyQuest]:
        """Get user's daily quests"""
        try:
            # Check for daily reset first
            await self.check_daily_reset(user_id)
            
            # Get quests from database
            quest_data = await self.db.get_daily_quests(user_id)
            
            if not quest_data:
                # Generate first-time quests
                await self._reset_daily_quests(user_id)
                quest_data = await self.db.get_daily_quests(user_id)
            
            # Convert to DailyQuest objects
            quests = []
            for data in quest_data:
                quest = self._data_to_quest(data)
                quests.append(quest)
            
            return quests
            
        except Exception as e:
            logger.error(f"Error getting daily quests for user {user_id}: {e}")
            return []
    
    def _data_to_quest(self, data: dict) -> DailyQuest:
        """Convert database data to DailyQuest object"""
        return DailyQuest(
            id=data['quest_id'],
            quest_type=QuestType(data['quest_type']),
            name=data['name'],
            description=data['description'],
            requirement=data['requirement'],
            current_progress=data['current_progress'],
            reward=QuestReward(
                experience=data['reward_experience'],
                gold=data['reward_gold'],
                item_id=data['reward_item_id'],
                item_name=data['reward_item_name']
            ),
            status=QuestStatus(data['status']),
            icon=data['icon']
        )
    
    async def update_quest_progress(self, user_id: int, quest_type: QuestType, amount: int = 1) -> List[DailyQuest]:
        """Update progress for specific quest type"""
        try:
            quests = await self.get_daily_quests(user_id)
            completed_quests = []
            
            for quest in quests:
                if quest.quest_type == quest_type and quest.status == QuestStatus.ACTIVE:
                    quest.current_progress += amount
                    
                    # Check if completed
                    if quest.is_completed and quest.status == QuestStatus.ACTIVE:
                        quest.status = QuestStatus.COMPLETED
                        completed_quests.append(quest)
                    
                    # Update in database
                    await self.db.update_quest_progress(user_id, quest.id, quest.current_progress, quest.status.value)
            
            return completed_quests
            
        except Exception as e:
            logger.error(f"Error updating quest progress for user {user_id}: {e}")
            return []
    
    async def give_quest_reward(self, user_id: int, quest_id: str) -> str:
        """Give reward for completed quest"""
        try:
            # Get quest
            quest_data = await self.db.get_daily_quest(user_id, quest_id)
            if not quest_data:
                return "❌ Завдання не знайдено"
            
            quest = self._data_to_quest(quest_data)
            
            if quest.status != QuestStatus.COMPLETED:
                return "❌ Завдання ще не завершено"
            
            reward_text = ""
            
            # Give experience
            if quest.reward.experience > 0:
                character = await self.db.get_character(user_id)
                if character:
                    from game_logic.character import CharacterManager
                    char_manager = CharacterManager(self.db)
                    exp_result = char_manager.add_experience(character, quest.reward.experience)
                    await self.db.update_character(character)
                    
                    reward_text += f"⚡ +{quest.reward.experience} досвіду\n"
                    if exp_result and exp_result.get('level_up'):
                        reward_text += f"🎉 Рівень підвищено до {exp_result['new_level']}!\n"
            
            # Give gold
            if quest.reward.gold > 0:
                character = await self.db.get_character(user_id)
                if character:
                    character.gold += quest.reward.gold
                    await self.db.update_character(character)
                reward_text += f"💰 +{quest.reward.gold} золота\n"
            
            # Give item
            if quest.reward.item_id:
                from database.database_models import InventoryItem
                inventory_item = InventoryItem(
                    item_id=quest.reward.item_id,
                    user_id=user_id,
                    item_type='potion',
                    name=quest.reward.item_name,
                    description=f"Нагорода за щоденне завдання: {quest.name}",
                    quantity=1,
                    properties={'quest_reward': True, 'quest_id': quest_id}
                )
                
                await self.db.add_item_to_inventory(user_id, inventory_item)
                reward_text += f"🎁 Отримано: {quest.reward.item_name}\n"
            
            # Mark as claimed
            await self.db.update_quest_status(user_id, quest_id, QuestStatus.CLAIMED.value)
            
            return reward_text.strip()
            
        except Exception as e:
            logger.error(f"Error giving quest reward: {e}")
            return "❌ Помилка при видачі нагороди"
    
    async def get_quest_summary(self, user_id: int) -> dict:
        """Get summary of daily quest progress"""
        try:
            quests = await self.get_daily_quests(user_id)
            
            total_quests = len(quests)
            completed_quests = len([q for q in quests if q.status in [QuestStatus.COMPLETED, QuestStatus.CLAIMED]])
            claimed_quests = len([q for q in quests if q.status == QuestStatus.CLAIMED])
            
            return {
                'total': total_quests,
                'completed': completed_quests,
                'claimed': claimed_quests,
                'progress': f"{completed_quests}/{total_quests}",
                'completion_rate': int((completed_quests / total_quests * 100)) if total_quests > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting quest summary: {e}")
            return {'total': 0, 'completed': 0, 'claimed': 0, 'progress': '0/0', 'completion_rate': 0}



