"""
Rest Manager - manages rest system in tavern
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RestManager:
    """Manage rest system for health regeneration"""
    
    def __init__(self):
        self.active_rests: Dict[int, Dict] = {}  # user_id -> rest_data
        self.rest_task = None
    
    async def start_rest(self, user_id: int, character: Dict, db_manager) -> Dict:
        """Start rest session for character"""
        
        if user_id in self.active_rests:
            return {
                'success': False,
                'message': 'Ви вже відпочиваєте!'
            }
        
        if character['health'] >= character['max_health']:
            return {
                'success': False,
                'message': '💚 Ваше здоров\'я вже повне!'
            }
        
        # Calculate rest duration based on missing health
        missing_health = character['max_health'] - character['health']
        heal_per_tick = 15  # HP per 15 seconds
        total_ticks = (missing_health + heal_per_tick - 1) // heal_per_tick  # Ceiling division
        total_duration = total_ticks * 15  # 15 seconds per tick
        
        rest_data = {
            'user_id': user_id,
            'character': character,
            'start_time': datetime.now(),
            'end_time': datetime.now() + timedelta(seconds=total_duration),
            'heal_per_tick': heal_per_tick,
            'total_ticks': total_ticks,
            'current_tick': 0,
            'db_manager': db_manager,
            'is_active': True
        }
        
        self.active_rests[user_id] = rest_data
        
        # Start rest process
        asyncio.create_task(self._rest_process(user_id))
        
        return {
            'success': True,
            'message': f'🏠 Ви почали відпочивати!\n💚 Відновлення: +{heal_per_tick} HP кожні 15 секунд\n⏱️ Час відпочинку: {total_duration} секунд',
            'duration': total_duration,
            'heal_per_tick': heal_per_tick
        }
    
    async def stop_rest(self, user_id: int) -> Dict:
        """Stop rest session"""
        
        if user_id not in self.active_rests:
            return {
                'success': False,
                'message': 'Ви не відпочиваєте!'
            }
        
        rest_data = self.active_rests[user_id]
        rest_data['is_active'] = False
        
        # Calculate total healing done
        total_healed = rest_data['current_tick'] * rest_data['heal_per_tick']
        
        del self.active_rests[user_id]
        
        return {
            'success': True,
            'message': f'🏠 Відпочинок завершено!\n💚 Відновлено: +{total_healed} HP',
            'total_healed': total_healed
        }
    
    def get_rest_status(self, user_id: int) -> Optional[Dict]:
        """Get current rest status for user"""
        return self.active_rests.get(user_id)
    
    def is_resting(self, user_id: int) -> bool:
        """Check if user is currently resting"""
        return user_id in self.active_rests and self.active_rests[user_id]['is_active']
    
    async def _rest_process(self, user_id: int):
        """Background process for rest healing"""
        
        rest_data = self.active_rests.get(user_id)
        if not rest_data:
            return
        
        try:
            while rest_data['is_active'] and rest_data['current_tick'] < rest_data['total_ticks']:
                # Wait 15 seconds
                await asyncio.sleep(15)
                
                if not rest_data['is_active']:
                    break
                
                # Heal character
                current_health = rest_data['character']['health']
                max_health = rest_data['character']['max_health']
                heal_amount = min(rest_data['heal_per_tick'], max_health - current_health)
                
                if heal_amount > 0:
                    rest_data['character']['health'] = min(max_health, current_health + heal_amount)
                    rest_data['current_tick'] += 1
                    
                    # Update database
                    await rest_data['db_manager'].update_character_by_id(
                        user_id, 
                        {'health': rest_data['character']['health']}
                    )
                    
                    logger.info(f"User {user_id} healed +{heal_amount} HP during rest (tick {rest_data['current_tick']})")
                
                # Check if fully healed
                if rest_data['character']['health'] >= max_health:
                    rest_data['is_active'] = False
                    break
            
            # Clean up if rest is complete
            if user_id in self.active_rests:
                del self.active_rests[user_id]
                
        except Exception as e:
            logger.error(f"Error in rest process for user {user_id}: {e}")
            if user_id in self.active_rests:
                del self.active_rests[user_id]
    
    def get_rest_progress(self, user_id: int) -> Optional[Dict]:
        """Get rest progress information"""
        
        if user_id not in self.active_rests:
            return None
        
        rest_data = self.active_rests[user_id]
        
        if not rest_data['is_active']:
            return None
        
        elapsed = (datetime.now() - rest_data['start_time']).total_seconds()
        total_duration = (rest_data['end_time'] - rest_data['start_time']).total_seconds()
        progress_percent = min(100, (elapsed / total_duration) * 100) if total_duration > 0 else 0
        
        current_health = rest_data['character']['health']
        max_health = rest_data['character']['max_health']
        total_healed = rest_data['current_tick'] * rest_data['heal_per_tick']
        
        # Create progress bar
        progress_bar = self._create_progress_bar(progress_percent)
        
        # Calculate health percentage
        health_percent = (current_health / max_health) * 100 if max_health > 0 else 0
        health_bar = self._create_health_bar(health_percent)
        
        return {
            'progress_percent': progress_percent,
            'current_health': current_health,
            'max_health': max_health,
            'total_healed': total_healed,
            'heal_per_tick': rest_data['heal_per_tick'],
            'ticks_completed': rest_data['current_tick'],
            'total_ticks': rest_data['total_ticks'],
            'time_remaining': max(0, total_duration - elapsed),
            'progress_bar': progress_bar,
            'health_bar': health_bar,
            'health_percent': health_percent
        }
    
    def _create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create a visual progress bar"""
        filled = int((percentage / 100) * width)
        empty = width - filled
        
        # Use different characters for progress bar
        bar = "█" * filled + "░" * empty
        return f"[{bar}] {percentage:.1f}%"
    
    def _create_health_bar(self, percentage: float, width: int = 15) -> str:
        """Create a visual health bar"""
        filled = int((percentage / 100) * width)
        empty = width - filled
        
        # Use different characters for health bar
        if percentage >= 80:
            bar = "🟢" * filled + "⚪" * empty  # Green for high health
        elif percentage >= 50:
            bar = "🟡" * filled + "⚪" * empty  # Yellow for medium health
        elif percentage >= 25:
            bar = "🟠" * filled + "⚪" * empty  # Orange for low health
        else:
            bar = "🔴" * filled + "⚪" * empty  # Red for critical health
        
        return f"{bar} {percentage:.1f}%"


# Global rest manager instance
rest_manager = RestManager()
