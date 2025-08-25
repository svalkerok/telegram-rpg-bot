"""
Potion Manager - manages potion system
"""

import random
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Potion:
    """Potion item data"""
    id: str
    name: str
    description: str
    price: int
    level_required: int
    rarity: str
    effects: Dict
    usable_in_combat: bool = True
    stackable: bool = True
    max_stack: int = 10


class PotionManager:
    """Manage potion system"""
    
    def __init__(self):
        self.potions = self._create_potion_catalog()
    
    def _create_potion_catalog(self) -> Dict[str, Potion]:
        """Create potion catalog"""
        return {
            # Health potions
            'small_health_potion': Potion(
                id='small_health_potion',
                name='Мале зілля здоров\'я',
                description='Відновлює 50 HP',
                price=30,
                level_required=1,
                rarity='common',
                effects={'health': 50}
            ),
            'health_potion': Potion(
                id='health_potion',
                name='Зілля здоров\'я',
                description='Відновлює 100 HP',
                price=60,
                level_required=1,
                rarity='common',
                effects={'health': 100}
            ),
            'greater_health_potion': Potion(
                id='greater_health_potion',
                name='Велике зілля здоров\'я',
                description='Відновлює 200 HP',
                price=120,
                level_required=3,
                rarity='uncommon',
                effects={'health': 200}
            ),
            'supreme_health_potion': Potion(
                id='supreme_health_potion',
                name='Найкраще зілля здоров\'я',
                description='Відновлює 400 HP',
                price=250,
                level_required=8,
                rarity='rare',
                effects={'health': 400}
            ),
            
            # Mana potions
            'small_mana_potion': Potion(
                id='small_mana_potion',
                name='Мале зілля мани',
                description='Відновлює 30 мани',
                price=25,
                level_required=1,
                rarity='common',
                effects={'mana': 30}
            ),
            'mana_potion': Potion(
                id='mana_potion',
                name='Зілля мани',
                description='Відновлює 60 мани',
                price=45,
                level_required=1,
                rarity='common',
                effects={'mana': 60}
            ),
            'greater_mana_potion': Potion(
                id='greater_mana_potion',
                name='Велике зілля мани',
                description='Відновлює 120 мани',
                price=90,
                level_required=3,
                rarity='uncommon',
                effects={'mana': 120}
            ),
            
            # Combat buff potions
            'strength_potion': Potion(
                id='strength_potion',
                name='Зілля сили',
                description='Тимчасово +15 до атаки на 3 ходи',
                price=80,
                level_required=2,
                rarity='uncommon',
                effects={'temp_attack': 15, 'duration': 3}
            ),
            'defense_potion': Potion(
                id='defense_potion',
                name='Зілля захисту',
                description='Тимчасово +12 до захисту на 3 ходи',
                price=70,
                level_required=2,
                rarity='uncommon',
                effects={'temp_defense': 12, 'duration': 3}
            ),
            'speed_potion': Potion(
                id='speed_potion',
                name='Зілля швидкості',
                description='Тимчасово +10 до швидкості на 2 ходи',
                price=60,
                level_required=2,
                rarity='uncommon',
                effects={'temp_speed': 10, 'duration': 2}
            ),
            'regen_potion': Potion(
                id='regen_potion',
                name='Зілля регенерації',
                description='Регенерує 25 HP/хід на 4 ходи',
                price=100,
                level_required=4,
                rarity='uncommon',
                effects={'health_regen': 25, 'duration': 4}
            )
        }
    
    def get_potion(self, potion_id: str) -> Optional[Potion]:
        """Get potion by ID"""
        return self.potions.get(potion_id)
    
    def get_all_potions(self) -> Dict[str, Potion]:
        """Get all potions"""
        return self.potions
    
    def get_potions_by_type(self, potion_type: str) -> Dict[str, Potion]:
        """Get potions by type (health, mana, combat)"""
        if potion_type == 'health':
            return {k: v for k, v in self.potions.items() if 'health' in k and 'regen' not in k}
        elif potion_type == 'mana':
            return {k: v for k, v in self.potions.items() if 'mana' in k}
        elif potion_type == 'combat':
            return {k: v for k, v in self.potions.items() if any(x in k for x in ['strength', 'defense', 'speed', 'regen'])}
        return {}
    
    def roll_dungeon_potion_drop(self) -> Optional[str]:
        """Roll for potion drop after dungeon completion (10% chance)"""
        if random.random() < 0.1:  # 10% chance
            # Weighted random selection
            potion_weights = {
                'small_health_potion': 40,  # 40% chance
                'health_potion': 25,        # 25% chance
                'small_mana_potion': 20,    # 20% chance
                'mana_potion': 10,          # 10% chance
                'strength_potion': 3,       # 3% chance
                'defense_potion': 2         # 2% chance
            }
            
            total_weight = sum(potion_weights.values())
            roll = random.uniform(0, total_weight)
            
            current_weight = 0
            for potion_id, weight in potion_weights.items():
                current_weight += weight
                if roll <= current_weight:
                    return potion_id
        
        return None
    
    def apply_potion_effects(self, character: Dict, potion: Potion) -> Dict:
        """Apply potion effects to character"""
        updates = {}
        effects_text = []
        
        # Instant effects
        if 'health' in potion.effects:
            heal_amount = potion.effects['health']
            new_health = min(character['max_health'], character['health'] + heal_amount)
            health_gained = new_health - character['health']
            updates['health'] = new_health
            effects_text.append(f"💚 Відновлено {health_gained} здоров'я")
        
        if 'mana' in potion.effects:
            mana_amount = potion.effects['mana']
            new_mana = min(character.get('max_mana', 100), character.get('mana', 0) + mana_amount)
            mana_gained = new_mana - character.get('mana', 0)
            updates['mana'] = new_mana
            effects_text.append(f"⚡ Відновлено {mana_gained} мани")
        
        return {
            'updates': updates,
            'effects_text': effects_text,
            'temp_effects': {k: v for k, v in potion.effects.items() if k.startswith('temp_') or k == 'health_regen'}
        }
    
    def get_potion_display_name(self, potion: Potion, quantity: int = 1) -> str:
        """Get formatted potion display name"""
        effects = []
        
        if 'health' in potion.effects:
            effects.append(f"💚+{potion.effects['health']} HP")
        if 'mana' in potion.effects:
            effects.append(f"⚡+{potion.effects['mana']} MP")
        if 'temp_attack' in potion.effects:
            effects.append(f"⚔️+{potion.effects['temp_attack']} атака")
        if 'temp_defense' in potion.effects:
            effects.append(f"🛡️+{potion.effects['temp_defense']} захист")
        if 'temp_speed' in potion.effects:
            effects.append(f"⚡+{potion.effects['temp_speed']} швидкість")
        if 'health_regen' in potion.effects:
            effects.append(f"💚{potion.effects['health_regen']} HP/хід")
        
        effects_text = " ".join(effects)
        return f"{potion.name} x{quantity} ({effects_text})"


# Global potion manager instance
potion_manager = PotionManager()

