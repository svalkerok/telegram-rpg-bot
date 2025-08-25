"""
Balance System - manages game balance and scaling
"""

import random
from typing import Dict, Any

class BalanceSystem:
    """Basic balance system for game scaling"""
    
    def __init__(self):
        self.difficulty_multipliers = {
            'easy': 0.8,
            'normal': 1.0,
            'hard': 1.3,
            'nightmare': 1.8
        }
    
    def calculate_player_power(self, character: Dict[str, Any]) -> int:
        """Calculate player power level"""
        attack = character.get('attack', 10)
        defense = character.get('defense', 5)
        max_health = character.get('max_health', 100)
        speed = character.get('speed', 10)
        crit_chance = character.get('critical_chance', 5)
        level = character.get('level', 1)
        
        power = (
            level * 20 +
            attack * 8 +
            defense * 6 +
            max_health * 0.4 +
            speed * 2 +
            crit_chance * 3
        )
        
        return int(power)
    
    def calculate_gold_reward(self, enemy_level: int, difficulty: str) -> int:
        """Calculate gold reward for victory"""
        base_gold = enemy_level * 15
        difficulty_bonus = self.difficulty_multipliers.get(difficulty, 1.0)
        
        return int(base_gold * difficulty_bonus * random.uniform(0.8, 1.2))
    
    def suggest_dungeon_difficulty(self, player_power: int, dungeon_base_power: int) -> str:
        """Suggest dungeon difficulty"""
        power_ratio = dungeon_base_power / player_power
        
        if power_ratio < 0.6:
            return "easy"
        elif power_ratio < 0.9:
            return "normal"  
        elif power_ratio < 1.3:
            return "hard"
        else:
            return "nightmare"
    
    def scale_enemy_stats(self, base_enemy: Dict[str, Any], player_level: int, player_power: int, difficulty: str) -> Dict[str, Any]:
        """Scale enemy stats based on player level and difficulty"""
        difficulty_multiplier = self.difficulty_multipliers.get(difficulty, 1.0)
        
        # Calculate level difference
        level_diff = max(0, player_level - base_enemy.get('level', 1))
        level_scaling = 1 + (level_diff * 0.1)  # 10% increase per level difference
        
        # Scale stats
        scaled_enemy = base_enemy.copy()
        scaled_enemy['level'] = max(1, int(base_enemy.get('level', 1) * level_scaling))
        scaled_enemy['health'] = int(base_enemy.get('health', 50) * difficulty_multiplier * level_scaling)
        scaled_enemy['max_health'] = scaled_enemy['health']
        scaled_enemy['attack'] = int(base_enemy.get('attack', 10) * difficulty_multiplier * level_scaling)
        scaled_enemy['defense'] = int(base_enemy.get('defense', 5) * difficulty_multiplier * level_scaling)
        scaled_enemy['speed'] = int(base_enemy.get('speed', 8) * difficulty_multiplier * level_scaling)
        
        # Scale rewards
        base_exp = base_enemy.get('exp_reward', 10)
        base_gold = base_enemy.get('gold_reward', 5)
        scaled_enemy['exp_reward'] = int(base_exp * difficulty_multiplier * level_scaling)
        scaled_enemy['gold_reward'] = int(base_gold * difficulty_multiplier * level_scaling)
        
        return scaled_enemy
