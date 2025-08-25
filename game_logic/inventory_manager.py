"""
Inventory and Equipment Management System
"""

import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import logging

from .equipment import EquipmentManager, EquipmentItem, EquipmentType, CharacterClass, Materials

logger = logging.getLogger(__name__)


@dataclass
class CharacterEquipment:
    """Character's equipped items and inventory"""
    user_id: int
    equipped_weapon: Optional[str] = None
    equipped_armor: Optional[str] = None
    weapon_upgrade_level: int = 0
    armor_upgrade_level: int = 0
    
    # Inventory (item_id -> upgrade_level)
    weapons: Dict[str, int] = None
    armor: Dict[str, int] = None
    materials: Dict[str, int] = None
    
    def __post_init__(self):
        if self.weapons is None:
            self.weapons = {}
        if self.armor is None:
            self.armor = {}
        if self.materials is None:
            self.materials = {"gods_stone": 0, "mithril_dust": 0, "dragon_scale": 0}


@dataclass
class CharacterStats:
    """Complete character statistics with equipment bonuses"""
    # Base stats
    base_attack: int
    base_defense: int
    base_speed: int
    base_mana: int
    base_magic_power: int
    base_crit_chance: int
    base_block_chance: int
    base_dodge_chance: int
    
    # Equipment bonuses
    weapon_attack: int = 0
    weapon_magic_power: int = 0
    weapon_crit_chance: int = 0
    weapon_speed: int = 0
    weapon_mana: int = 0
    
    armor_defense: int = 0
    armor_speed: int = 0
    armor_mana: int = 0
    armor_magic_power: int = 0
    armor_block_chance: int = 0
    armor_dodge_chance: int = 0
    armor_crit_chance: int = 0
    
    # Special effects
    special_effects: List[str] = None
    
    def __post_init__(self):
        if self.special_effects is None:
            self.special_effects = []
    
    @property
    def total_attack(self) -> int:
        return self.base_attack + self.weapon_attack
    
    @property
    def total_defense(self) -> int:
        return self.base_defense + self.armor_defense
    
    @property
    def total_speed(self) -> int:
        return self.base_speed + self.weapon_speed + self.armor_speed
    
    @property
    def total_mana(self) -> int:
        return self.base_mana + self.weapon_mana + self.armor_mana
    
    @property
    def total_magic_power(self) -> int:
        return self.base_magic_power + self.weapon_magic_power + self.armor_magic_power
    
    @property
    def total_crit_chance(self) -> int:
        return self.base_crit_chance + self.weapon_crit_chance + self.armor_crit_chance
    
    @property
    def total_block_chance(self) -> int:
        return self.base_block_chance + self.armor_block_chance
    
    @property
    def total_dodge_chance(self) -> int:
        return self.base_dodge_chance + self.armor_dodge_chance


class InventoryManager:
    """Manages character inventory and equipment"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.equipment_manager = EquipmentManager(db_manager)
    
    async def get_character_equipment(self, user_id: int) -> CharacterEquipment:
        """Get character's equipment and inventory"""
        try:
            conn = await self.db.get_connection()
            
            # Get equipped items
            async with conn.execute('''
                SELECT equipped_weapon, equipped_armor, weapon_upgrade_level, armor_upgrade_level
                FROM characters WHERE user_id = ?
            ''', (user_id,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return CharacterEquipment(user_id=user_id)
            
            equipped_weapon, equipped_armor, weapon_upgrade, armor_upgrade = row
            
            # Get inventory
            async with conn.execute('''
                SELECT item_id, upgrade_level, item_type FROM player_equipment 
                WHERE user_id = ? AND is_equipped = 0
            ''', (user_id,)) as cursor:
                inventory_rows = await cursor.fetchall()
            
            weapons = {}
            armor = {}
            
            for item_id, upgrade_level, item_type in inventory_rows:
                if item_type == 'weapon':
                    weapons[item_id] = upgrade_level
                elif item_type == 'armor':
                    armor[item_id] = upgrade_level
            
            # Get materials
            async with conn.execute('''
                SELECT gods_stone, mithril_dust, dragon_scale FROM player_materials 
                WHERE user_id = ?
            ''', (user_id,)) as cursor:
                materials_row = await cursor.fetchone()
            
            materials = {"gods_stone": 0, "mithril_dust": 0, "dragon_scale": 0}
            if materials_row:
                materials["gods_stone"] = materials_row[0] or 0
                materials["mithril_dust"] = materials_row[1] or 0
                materials["dragon_scale"] = materials_row[2] or 0
            
            return CharacterEquipment(
                user_id=user_id,
                equipped_weapon=equipped_weapon,
                equipped_armor=equipped_armor,
                weapon_upgrade_level=weapon_upgrade or 0,
                armor_upgrade_level=armor_upgrade or 0,
                weapons=weapons,
                armor=armor,
                materials=materials
            )
            
        except Exception as e:
            logger.error(f"Error getting character equipment: {e}")
            return CharacterEquipment(user_id=user_id)
    
    async def add_item_to_inventory(self, user_id: int, item_id: str, upgrade_level: int = 0) -> bool:
        """Add item to player inventory"""
        try:
            # Check if item exists
            item = self.equipment_manager.get_equipment_by_id(item_id)
            if not item:
                return False
            
            conn = await self.db.get_connection()
            
            # Add to player_equipment table
            await conn.execute('''
                INSERT INTO player_equipment 
                (user_id, item_id, upgrade_level, item_type, is_equipped)
                VALUES (?, ?, ?, ?, 0)
            ''', (user_id, item_id, upgrade_level, item.type.value))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error adding item to inventory: {e}")
            return False

    async def add_potion_to_inventory(self, user_id: int, potion_id: str, quantity: int = 1) -> bool:
        """Add potion to player inventory"""
        try:
            from game_logic.potion_manager import potion_manager
            
            potion = potion_manager.get_potion(potion_id)
            if not potion:
                logger.error(f"Potion {potion_id} not found")
                return False
            
            conn = await self.db.get_connection()
            
            # Check if potion already exists in inventory
            async with conn.execute('''
                SELECT id, quantity FROM player_equipment 
                WHERE user_id = ? AND item_id = ? AND item_type = 'consumable'
            ''', (user_id, potion_id)) as cursor:
                existing = await cursor.fetchone()
            
            if existing:
                # Update quantity for existing potion
                new_quantity = existing['quantity'] + quantity
                await conn.execute('''
                    UPDATE player_equipment 
                    SET quantity = ? WHERE id = ?
                ''', (new_quantity, existing['id']))
            else:
                # Add new potion
                await conn.execute('''
                    INSERT INTO player_equipment 
                    (user_id, item_id, upgrade_level, item_type, is_equipped, quantity)
                    VALUES (?, ?, 0, 'consumable', 0, ?)
                ''', (user_id, potion_id, quantity))
            
            await conn.commit()
            logger.info(f"Added {quantity}x {potion.name} to user {user_id} inventory")
            return True
            
        except Exception as e:
            logger.error(f"Error adding potion to inventory: {e}")
            return False

    async def remove_potion_from_inventory(self, user_id: int, potion_id: str, quantity: int = 1) -> bool:
        """Remove potion from player inventory"""
        try:
            conn = await self.db.get_connection()
            
            # Check current quantity
            async with conn.execute('''
                SELECT id, quantity FROM player_equipment 
                WHERE user_id = ? AND item_id = ? AND item_type = 'consumable'
            ''', (user_id, potion_id)) as cursor:
                existing = await cursor.fetchone()
            
            if not existing:
                logger.warning(f"Potion {potion_id} not found in user {user_id} inventory")
                return False
            
            current_quantity = existing['quantity']
            
            if current_quantity <= quantity:
                # Remove entire stack
                await conn.execute('''
                    DELETE FROM player_equipment 
                    WHERE id = ?
                ''', (existing['id'],))
            else:
                # Reduce quantity
                new_quantity = current_quantity - quantity
                await conn.execute('''
                    UPDATE player_equipment 
                    SET quantity = ? WHERE id = ?
                ''', (new_quantity, existing['id']))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error removing potion from inventory: {e}")
            return False
    
    async def remove_item_from_inventory(self, user_id: int, item_id: str) -> bool:
        """Remove item from player inventory"""
        try:
            conn = await self.db.get_connection()
            
            await conn.execute('''
                DELETE FROM player_equipment 
                WHERE user_id = ? AND item_id = ? AND is_equipped = 0
                LIMIT 1
            ''', (user_id, item_id))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error removing item from inventory: {e}")
            return False
    
    async def equip_item(self, user_id: int, item_id: str) -> Dict[str, Any]:
        """Equip an item from inventory"""
        try:
            # Get item details
            item = self.equipment_manager.get_equipment_by_id(item_id)
            if not item:
                return {"success": False, "reason": "item_not_found"}
            
            # Get character and check compatibility
            character = await self.db.get_character(user_id)
            if not character:
                return {"success": False, "reason": "character_not_found"}
            
            if not self.equipment_manager.check_equipment_compatibility(character.character_class, item_id):
                return {"success": False, "reason": "class_incompatible"}
            
            if character.level < item.level_requirement:
                return {"success": False, "reason": "level_requirement"}
            
            conn = await self.db.get_connection()
            
            # Get item upgrade level from inventory
            async with conn.execute('''
                SELECT upgrade_level FROM player_equipment 
                WHERE user_id = ? AND item_id = ? AND is_equipped = 0
            ''', (user_id, item_id)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return {"success": False, "reason": "item_not_in_inventory"}
            
            upgrade_level = row[0]
            
            # Unequip current item and add to inventory
            if item.type == EquipmentType.WEAPON:
                current_equipped = character.weapon
                current_upgrade = getattr(character, 'weapon_upgrade_level', 0)
                
                if current_equipped and current_equipped != 'basic_sword':
                    await self._add_to_inventory_table(user_id, current_equipped, current_upgrade, 'weapon')
                
                # Update character (both old and new fields for compatibility)
                await conn.execute('''
                    UPDATE characters 
                    SET weapon = ?, weapon_upgrade_level = ?,
                        equipped_weapon = ?
                    WHERE user_id = ?
                ''', (item_id, upgrade_level, item_id, user_id))
                
            elif item.type == EquipmentType.ARMOR:
                current_equipped = character.armor
                current_upgrade = getattr(character, 'armor_upgrade_level', 0)
                
                if current_equipped and current_equipped != 'basic_clothes':
                    await self._add_to_inventory_table(user_id, current_equipped, current_upgrade, 'armor')
                
                # Update character (both old and new fields for compatibility)
                await conn.execute('''
                    UPDATE characters 
                    SET armor = ?, armor_upgrade_level = ?,
                        equipped_armor = ?
                    WHERE user_id = ?
                ''', (item_id, upgrade_level, item_id, user_id))
            
            # Remove item from inventory
            await conn.execute('''
                DELETE FROM player_equipment 
                WHERE user_id = ? AND item_id = ? AND is_equipped = 0
                LIMIT 1
            ''', (user_id, item_id))
            
            await conn.commit()
            
            return {"success": True, "equipped_item": item_id, "upgrade_level": upgrade_level}
            
        except Exception as e:
            logger.error(f"Error equipping item: {e}")
            return {"success": False, "reason": "database_error"}
    
    async def _add_to_inventory_table(self, user_id: int, item_id: str, upgrade_level: int, item_type: str):
        """Helper method to add item to inventory table"""
        conn = await self.db.get_connection()
        await conn.execute('''
            INSERT INTO player_equipment 
            (user_id, item_id, upgrade_level, item_type, is_equipped)
            VALUES (?, ?, ?, ?, 0)
        ''', (user_id, item_id, upgrade_level, item_type))
    
    async def calculate_character_stats(self, user_id: int) -> CharacterStats:
        """Calculate complete character stats with equipment"""
        try:
            # Get base character stats
            character = await self.db.get_character(user_id)
            if not character:
                return None
            
            # Get equipment
            equipment = await self.get_character_equipment(user_id)
            
            # Base stats from character
            stats = CharacterStats(
                base_attack=character.attack,
                base_defense=character.defense,
                base_speed=character.speed,
                base_mana=getattr(character, 'mana', 0),
                base_magic_power=getattr(character, 'magic_power', 0),
                base_crit_chance=getattr(character, 'critical_chance', 10),
                base_block_chance=getattr(character, 'block_chance', 5),
                base_dodge_chance=0
            )
            
            # Add weapon bonuses
            if equipment.equipped_weapon:
                weapon = self.equipment_manager.get_equipment_by_id(equipment.equipped_weapon)
                if weapon:
                    # Calculate weapon stats with correct upgrade level from database
                    weapon_attack = self.equipment_manager.calculate_upgrade_stats(weapon.base_stats.attack, equipment.weapon_upgrade_level)
                    weapon_magic_power = self.equipment_manager.calculate_upgrade_stats(weapon.base_stats.magic_power, equipment.weapon_upgrade_level)
                    weapon_crit_chance = self.equipment_manager.calculate_upgrade_stats(weapon.base_stats.crit_chance, equipment.weapon_upgrade_level)
                    weapon_speed = self.equipment_manager.calculate_upgrade_stats(weapon.base_stats.speed, equipment.weapon_upgrade_level)
                    weapon_mana = self.equipment_manager.calculate_upgrade_stats(weapon.base_stats.mana, equipment.weapon_upgrade_level)
                    
                    stats.weapon_attack = weapon_attack
                    stats.weapon_magic_power = weapon_magic_power
                    stats.weapon_crit_chance = weapon_crit_chance
                    stats.weapon_speed = weapon_speed
                    stats.weapon_mana = weapon_mana
                    
                    # Add special effects
                    for effect in weapon.special_effects:
                        stats.special_effects.append(f"🗡 {weapon.name}: {effect.description}")
            
            # Add armor bonuses
            if equipment.equipped_armor:
                armor = self.equipment_manager.get_equipment_by_id(equipment.equipped_armor)
                if armor:
                    # Calculate armor stats with correct upgrade level from database
                    armor_defense = self.equipment_manager.calculate_upgrade_stats(armor.base_stats.defense, equipment.armor_upgrade_level)
                    armor_speed = self.equipment_manager.calculate_upgrade_stats(armor.base_stats.speed, equipment.armor_upgrade_level)
                    armor_mana = self.equipment_manager.calculate_upgrade_stats(armor.base_stats.mana, equipment.armor_upgrade_level)
                    armor_magic_power = self.equipment_manager.calculate_upgrade_stats(armor.base_stats.magic_power, equipment.armor_upgrade_level)
                    armor_block_chance = self.equipment_manager.calculate_upgrade_stats(armor.base_stats.block_chance, equipment.armor_upgrade_level)
                    armor_dodge_chance = self.equipment_manager.calculate_upgrade_stats(armor.base_stats.dodge_chance, equipment.armor_upgrade_level)
                    armor_crit_chance = self.equipment_manager.calculate_upgrade_stats(armor.base_stats.crit_chance, equipment.armor_upgrade_level)
                    
                    stats.armor_defense = armor_defense
                    stats.armor_speed = armor_speed
                    stats.armor_mana = armor_mana
                    stats.armor_magic_power = armor_magic_power
                    stats.armor_block_chance = armor_block_chance
                    stats.armor_dodge_chance = armor_dodge_chance
                    stats.armor_crit_chance = armor_crit_chance
                    
                    # Add special effects
                    for effect in armor.special_effects:
                        stats.special_effects.append(f"🛡 {armor.name}: {effect.description}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating character stats: {e}")
            return None
    
    async def upgrade_item(self, user_id: int, item_id: str, item_type: str) -> Dict[str, Any]:
        """Upgrade an equipped item"""
        try:
            character = await self.db.get_character(user_id)
            equipment = await self.get_character_equipment(user_id)
            
            if not character or not equipment:
                return {"success": False, "reason": "character_not_found"}
            
            # Check if item is equipped
            current_upgrade = 0
            if item_type == 'weapon' and equipment.equipped_weapon == item_id:
                current_upgrade = equipment.weapon_upgrade_level
            elif item_type == 'armor' and equipment.equipped_armor == item_id:
                current_upgrade = equipment.armor_upgrade_level
            else:
                return {"success": False, "reason": "item_not_equipped"}
            
            # Check max upgrade
            if current_upgrade >= 40:
                return {"success": False, "reason": "max_upgrade"}
            
            # Get upgrade cost
            cost = self.equipment_manager.get_upgrade_cost(current_upgrade)
            
            # Check materials
            if equipment.materials["gods_stone"] < cost.get("gods_stone", 0):
                return {"success": False, "reason": "insufficient_gods_stone"}
            
            if character.gold < cost.get("gold", 0):
                return {"success": False, "reason": "insufficient_gold"}
            
            # Attempt upgrade
            upgrade_result = self.equipment_manager.attempt_upgrade(item_id, current_upgrade)
            
            if upgrade_result["success"]:
                # Update character
                conn = await self.db.get_connection()
                
                # Deduct materials and gold
                new_gold = int(character.gold - cost.get("gold", 0))
                new_gods_stone = equipment.materials["gods_stone"] - cost.get("gods_stone", 0)
                
                if item_type == 'weapon':
                    await conn.execute('''
                        UPDATE characters 
                        SET weapon_upgrade_level = ?, gold = ?
                        WHERE user_id = ?
                    ''', (upgrade_result["new_level"], new_gold, user_id))
                else:
                    await conn.execute('''
                        UPDATE characters 
                        SET armor_upgrade_level = ?, gold = ?
                        WHERE user_id = ?
                    ''', (upgrade_result["new_level"], new_gold, user_id))
                
                # Update materials
                await conn.execute('''
                    UPDATE player_materials 
                    SET gods_stone = ?
                    WHERE user_id = ?
                ''', (new_gods_stone, user_id))
                
                await conn.commit()
                
                return {
                    "success": True,
                    "new_level": upgrade_result["new_level"],
                    "materials_used": upgrade_result["materials_consumed"]
                }
            else:
                # Failed upgrade - still consume materials
                conn = await self.db.get_connection()
                
                new_gold = int(character.gold - cost.get("gold", 0))
                new_gods_stone = equipment.materials["gods_stone"] - cost.get("gods_stone", 0)
                
                await conn.execute('''
                    UPDATE characters SET gold = ? WHERE user_id = ?
                ''', (new_gold, user_id))
                
                await conn.execute('''
                    UPDATE player_materials SET gods_stone = ? WHERE user_id = ?
                ''', (new_gods_stone, user_id))
                
                await conn.commit()
                
                return {
                    "success": False,
                    "reason": "upgrade_failed",
                    "materials_used": upgrade_result["materials_consumed"]
                }
                
        except Exception as e:
            logger.error(f"Error upgrading item: {e}")
            return {"success": False, "reason": "database_error"}
    
    async def add_materials(self, user_id: int, materials: Dict[str, int]) -> bool:
        """Add crafting materials to player"""
        try:
            conn = await self.db.get_connection()
            
            # Initialize materials if not exists
            await conn.execute('''
                INSERT OR IGNORE INTO player_materials (user_id, gods_stone, mithril_dust, dragon_scale)
                VALUES (?, 0, 0, 0)
            ''', (user_id,))
            
            # Update materials
            gods_stone = materials.get("gods_stone", 0)
            mithril_dust = materials.get("mithril_dust", 0)
            dragon_scale = materials.get("dragon_scale", 0)
            
            await conn.execute('''
                UPDATE player_materials 
                SET gods_stone = gods_stone + ?,
                    mithril_dust = mithril_dust + ?,
                    dragon_scale = dragon_scale + ?
                WHERE user_id = ?
            ''', (gods_stone, mithril_dust, dragon_scale, user_id))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error adding materials: {e}")
            return False
    
    async def sell_item(self, user_id: int, item_id: str) -> Dict[str, Any]:
        """Sell item from inventory"""
        try:
            # Check if item exists in inventory
            conn = await self.db.get_connection()
            
            async with conn.execute('''
                SELECT upgrade_level FROM player_equipment 
                WHERE user_id = ? AND item_id = ? AND is_equipped = 0
                LIMIT 1
            ''', (user_id, item_id)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return {"success": False, "reason": "item_not_found"}
            
            upgrade_level = row[0]
            
            # Calculate sell price
            sell_price = self.equipment_manager.calculate_sell_price(item_id, upgrade_level)
            
            # Remove item and add gold
            await conn.execute('''
                DELETE FROM player_equipment 
                WHERE user_id = ? AND item_id = ? AND is_equipped = 0
                LIMIT 1
            ''', (user_id, item_id))
            
            await conn.execute('''
                UPDATE characters 
                SET gold = gold + ?
                WHERE user_id = ?
            ''', (sell_price, user_id))
            
            await conn.commit()
            
            return {"success": True, "gold_earned": sell_price}
            
        except Exception as e:
            logger.error(f"Error selling item: {e}")
            return {"success": False, "reason": "database_error"}
