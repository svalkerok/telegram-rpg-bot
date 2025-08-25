"""
Complete Database manager for Telegram RPG Bot "Легенди Валгаллії"
Handles all database operations with full async support
"""

import asyncio
import aiosqlite
import sqlite3
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import json
import logging

from .database_models import Character, User, InventoryItem, Inventory, Achievement, Statistics

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Complete async database manager for RPG bot"""
    
    def __init__(self, db_path: str):
        """Initialize database manager
        
        Args:
            db_path: Path to SQLite database file (can include sqlite:/// prefix)
        """
        # Clean up the database path
        if db_path.startswith('sqlite:///'):
            self.db_path = db_path.replace('sqlite:///', '')
        else:
            self.db_path = db_path
            
        self._connection = None
    
    async def get_connection(self) -> aiosqlite.Connection:
        """Get database connection"""
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
        return self._connection
    
    async def close(self) -> None:
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def init_database(self) -> bool:
        """Initialize all database tables"""
        try:
            conn = await self.get_connection()
            
            # Users table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_active TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    settings TEXT DEFAULT '{}'
                )
            ''')
            
            # Characters table with all required characteristics
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    class TEXT NOT NULL,
                    level INTEGER DEFAULT 1,
                    experience INTEGER DEFAULT 0,
                    experience_needed INTEGER DEFAULT 100,
                    health INTEGER NOT NULL,
                    max_health INTEGER NOT NULL,
                    mana INTEGER DEFAULT 0,
                    max_mana INTEGER DEFAULT 0,
                    attack INTEGER NOT NULL,
                    defense INTEGER NOT NULL,
                    magic_power INTEGER DEFAULT 0,
                    speed INTEGER DEFAULT 10,
                    critical_chance INTEGER DEFAULT 10,
                    block_chance INTEGER DEFAULT 5,
                    gold INTEGER DEFAULT 50,
                    weapon TEXT DEFAULT 'basic_sword',
                    armor TEXT DEFAULT 'basic_clothes',
                    dungeon_progress INTEGER DEFAULT 0,
                    daily_quests_completed INTEGER DEFAULT 0,
                    last_daily_reset TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_played TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Inventory table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    quantity INTEGER DEFAULT 1,
                    properties TEXT DEFAULT '{}',
                    is_equipped BOOLEAN DEFAULT 0,
                    obtained_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Achievements table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    achievement_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    achievement_type TEXT NOT NULL,
                    requirements TEXT DEFAULT '{}',
                    rewards TEXT DEFAULT '{}',
                    is_unlocked BOOLEAN DEFAULT 0,
                    progress INTEGER DEFAULT 0,
                    max_progress INTEGER DEFAULT 1,
                    unlocked_at TEXT,
                    is_hidden BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, achievement_id)
                )
            ''')
            
            # Daily quests table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_quests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    quest_id TEXT NOT NULL,
                    quest_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    requirement INTEGER NOT NULL,
                    current_progress INTEGER DEFAULT 0,
                    reward_experience INTEGER DEFAULT 0,
                    reward_gold INTEGER DEFAULT 0,
                    reward_item_id TEXT,
                    reward_item_name TEXT,
                    status TEXT DEFAULT 'active',
                    icon TEXT DEFAULT '📋',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, quest_id)
                )
            ''')
            
            # User data table for misc data storage
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, key)
                )
            ''')
            
            # Statistics table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    user_id INTEGER PRIMARY KEY,
                    enemies_killed INTEGER DEFAULT 0,
                    total_damage_dealt INTEGER DEFAULT 0,
                    total_damage_received INTEGER DEFAULT 0,
                    critical_hits INTEGER DEFAULT 0,
                    blocks_performed INTEGER DEFAULT 0,
                    arena_wins INTEGER DEFAULT 0,
                    arena_losses INTEGER DEFAULT 0,
                    arena_draws INTEGER DEFAULT 0,
                    highest_arena_streak INTEGER DEFAULT 0,
                    current_arena_streak INTEGER DEFAULT 0,
                    dungeons_completed INTEGER DEFAULT 0,
                    bosses_defeated INTEGER DEFAULT 0,
                    deepest_dungeon_level INTEGER DEFAULT 0,
                    gold_earned INTEGER DEFAULT 0,
                    gold_spent INTEGER DEFAULT 0,
                    items_found INTEGER DEFAULT 0,
                    items_sold INTEGER DEFAULT 0,
                    total_playtime_hours REAL DEFAULT 0.0,
                    sessions_count INTEGER DEFAULT 0,
                    quests_completed INTEGER DEFAULT 0,
                    daily_streaks INTEGER DEFAULT 0,
                    max_daily_streak INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Create performance indexes
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_inventory_equipped ON inventory(user_id, is_equipped)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_achievements_user_id ON achievements(user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_achievements_unlocked ON achievements(user_id, is_unlocked)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_daily_quests_user_id ON daily_quests(user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_daily_quests_status ON daily_quests(user_id, status)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_user_data_key ON user_data(user_id, key)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_characters_level ON characters(level)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)')
            
            # Equipment system tables
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS player_equipment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    upgrade_level INTEGER DEFAULT 0,
                    item_type TEXT NOT NULL,
                    is_equipped BOOLEAN DEFAULT 0,
                    acquired_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS player_materials (
                    user_id INTEGER PRIMARY KEY,
                    gods_stone INTEGER DEFAULT 0,
                    mithril_dust INTEGER DEFAULT 0,
                    dragon_scale INTEGER DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Add equipment columns to characters table if not exist
            try:
                await conn.execute('ALTER TABLE characters ADD COLUMN equipped_weapon TEXT')
                await conn.execute('ALTER TABLE characters ADD COLUMN equipped_armor TEXT')
                await conn.execute('ALTER TABLE characters ADD COLUMN weapon_upgrade_level INTEGER DEFAULT 0')
                await conn.execute('ALTER TABLE characters ADD COLUMN armor_upgrade_level INTEGER DEFAULT 0')
            except:
                pass  # Columns might already exist
            
            # Add quantity column to player_equipment table for potions
            try:
                await conn.execute('ALTER TABLE player_equipment ADD COLUMN quantity INTEGER DEFAULT 1')
            except:
                pass  # Column might already exist
            
            # Create indexes for equipment tables
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_player_equipment_user ON player_equipment(user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_player_equipment_item ON player_equipment(user_id, item_id)')
            
            await conn.commit()
            logger.info("Database tables and indexes created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False
    
    # =====================================================
    # USER OPERATIONS
    # =====================================================
    
    async def create_user(self, user_id: int, username: str) -> bool:
        """Create a new user"""
        try:
            conn = await self.get_connection()
            await conn.execute(
                '''INSERT OR IGNORE INTO users (user_id, username, created_at, last_active) 
                   VALUES (?, ?, ?, ?)''',
                (user_id, username, datetime.now().isoformat(), datetime.now().isoformat())
            )
            
            # Also create statistics entry
            await conn.execute(
                "INSERT OR IGNORE INTO statistics (user_id, created_at, updated_at) VALUES (?, ?, ?)",
                (user_id, datetime.now().isoformat(), datetime.now().isoformat())
            )
            
            await conn.commit()
            logger.info(f"Created user: {user_id} ({username})")
            return True
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                return User.from_dict(dict(row))
            return None
            
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    async def update_user_activity(self, user_id: int) -> bool:
        """Update user's last activity time"""
        try:
            conn = await self.get_connection()
            await conn.execute(
                "UPDATE users SET last_active = ? WHERE user_id = ?",
                (datetime.now().isoformat(), user_id)
            )
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")
            return False
    
    # =====================================================
    # CHARACTER OPERATIONS
    # =====================================================
    
    async def create_character(self, character_data: Dict[str, Any]) -> bool:
        """Create a new character with all required characteristics"""
        try:
            conn = await self.get_connection()
            
            # First ensure user exists
            await self.create_user(
                character_data['user_id'],
                character_data.get('username', 'Unknown')
            )
            
            # Insert character with all required characteristics
            await conn.execute('''
                INSERT OR REPLACE INTO characters 
                (user_id, name, class, level, experience, experience_needed,
                 health, max_health, mana, max_mana, attack, defense, 
                 magic_power, speed, critical_chance, block_chance, gold,
                 weapon, armor, dungeon_progress, daily_quests_completed,
                 last_daily_reset, created_at, last_played)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                character_data['user_id'],
                character_data['name'],
                character_data['class'],
                character_data.get('level', 1),
                character_data.get('experience', 0),
                character_data.get('experience_needed', 100),
                character_data['health'],
                character_data['max_health'],
                character_data.get('mana', 0),
                character_data.get('max_mana', 0),
                character_data['attack'],
                character_data['defense'],
                character_data.get('magic_power', 0),
                character_data.get('speed', 10),
                character_data.get('critical_chance', 10),
                character_data.get('block_chance', 5),
                character_data.get('gold', 50),
                character_data.get('weapon', 'basic_sword'),
                character_data.get('armor', 'basic_clothes'),
                character_data.get('dungeon_progress', 0),
                character_data.get('daily_quests_completed', 0),
                character_data.get('last_daily_reset'),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            await conn.commit()
            logger.info(f"Created character: {character_data['name']} for user {character_data['user_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating character: {e}")
            return False
    
    async def get_character(self, user_id: int) -> Optional[Character]:
        """Get character by user ID"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT * FROM characters WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                # Update last activity
                await self.update_user_activity(user_id)
                return Character.from_dict(dict(row))
            return None
            
        except Exception as e:
            logger.error(f"Error getting character: {e}")
            return None
    
    async def update_character(self, character: Character) -> bool:
        """Update character data"""
        try:
            conn = await self.get_connection()
            character.last_played = datetime.now()
            character_data = character.to_dict()
            
            await conn.execute('''
                UPDATE characters SET
                name = ?, class = ?, level = ?, experience = ?, experience_needed = ?,
                health = ?, max_health = ?, mana = ?, max_mana = ?, attack = ?,
                defense = ?, magic_power = ?, speed = ?, critical_chance = ?, block_chance = ?,
                gold = ?, weapon = ?, armor = ?, dungeon_progress = ?,
                daily_quests_completed = ?, last_daily_reset = ?, last_played = ?
                WHERE user_id = ?
            ''', (
                character_data['name'], character_data['class'], character_data['level'],
                character_data['experience'], character_data['experience_needed'],
                character_data['health'], character_data['max_health'],
                character_data['mana'], character_data['max_mana'],
                character_data['attack'], character_data['defense'],
                character_data['magic_power'], character_data['speed'],
                character_data['critical_chance'], character_data['block_chance'],
                character_data['gold'], character_data['weapon'], character_data['armor'],
                character_data['dungeon_progress'], character_data['daily_quests_completed'],
                character_data['last_daily_reset'], character_data['last_played'],
                character_data['user_id']
            ))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating character: {e}")
            return False
    
    async def update_character_by_id(self, user_id: int, updates: dict) -> bool:
        """Update character data by user_id with specific updates"""
        try:
            # Get current character
            character = await self.get_character(user_id)
            if not character:
                return False
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(character, key):
                    setattr(character, key, value)
            
            # Update in database
            return await self.update_character(character)
        except Exception as e:
            logger.error(f"Error updating character by ID: {e}")
            return False
    
    async def delete_character(self, user_id: int) -> bool:
        """Delete character and all related data"""
        try:
            conn = await self.get_connection()
            
            # Delete in order to respect foreign key constraints
            await conn.execute("DELETE FROM achievements WHERE user_id = ?", (user_id,))
            await conn.execute("DELETE FROM inventory WHERE user_id = ?", (user_id,))
            await conn.execute("DELETE FROM characters WHERE user_id = ?", (user_id,))
            
            # Reset statistics (don't delete, just reset)
            await conn.execute('''
                UPDATE statistics SET
                enemies_killed = 0, total_damage_dealt = 0, total_damage_received = 0,
                critical_hits = 0, blocks_performed = 0, arena_wins = 0, arena_losses = 0,
                arena_draws = 0, highest_arena_streak = 0, current_arena_streak = 0,
                dungeons_completed = 0, bosses_defeated = 0, deepest_dungeon_level = 0,
                gold_earned = 0, gold_spent = 0, items_found = 0, items_sold = 0,
                total_playtime_hours = 0.0, sessions_count = 0, quests_completed = 0,
                daily_streaks = 0, max_daily_streak = 0, updated_at = ?
                WHERE user_id = ?
            ''', (datetime.now().isoformat(), user_id))
            
            await conn.commit()
            logger.info(f"Deleted character data for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting character: {e}")
            return False
    
    async def get_character_by_name(self, name: str) -> Optional[Character]:
        """Get character by name (useful for admin functions)"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT * FROM characters WHERE name = ? LIMIT 1",
                (name,)
            )
            row = await cursor.fetchone()
            
            if row:
                return Character.from_dict(dict(row))
            return None
            
        except Exception as e:
            logger.error(f"Error getting character by name: {e}")
            return None
    
    # =====================================================
    # INVENTORY OPERATIONS
    # =====================================================
    
    async def get_inventory(self, user_id: int) -> Inventory:
        """Get user's complete inventory"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT * FROM inventory WHERE user_id = ? ORDER BY obtained_at DESC",
                (user_id,)
            )
            rows = await cursor.fetchall()
            
            items = []
            for row in rows:
                items.append(InventoryItem.from_dict(dict(row)))
            
            return Inventory(user_id=user_id, items=items)
            
        except Exception as e:
            logger.error(f"Error getting inventory: {e}")
            return Inventory(user_id=user_id)
    
    async def add_item_to_inventory(self, user_id: int, item: InventoryItem) -> bool:
        """Add item to user's inventory"""
        try:
            conn = await self.get_connection()
            
            # Check if stackable item already exists
            if item.item_type == 'consumable':
                cursor = await conn.execute(
                    "SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item.item_id)
                )
                existing = await cursor.fetchone()
                
                if existing:
                    # Update quantity
                    new_quantity = existing['quantity'] + item.quantity
                    await conn.execute(
                        "UPDATE inventory SET quantity = ? WHERE id = ?",
                        (new_quantity, existing['id'])
                    )
                    await conn.commit()
                    return True
            
            # Check inventory space
            inventory = await self.get_inventory(user_id)
            if len(inventory.items) >= inventory.max_slots:
                logger.warning(f"Inventory full for user {user_id}")
                return False
            
            # Add new item
            item_data = item.to_dict()
            await conn.execute('''
                INSERT INTO inventory 
                (user_id, item_id, item_type, name, description, quantity, 
                 properties, is_equipped, obtained_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item_data['user_id'], item_data['item_id'], item_data['item_type'],
                item_data['name'], item_data['description'], item_data['quantity'],
                item_data['properties'], item_data['is_equipped'], 
                item_data['obtained_at'] or datetime.now().isoformat()
            ))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error adding item to inventory: {e}")
            return False
    
    async def remove_item_from_inventory(self, user_id: int, item_id: str, quantity: int = 1) -> bool:
        """Remove item from inventory"""
        try:
            conn = await self.get_connection()
            
            # Get current quantity
            cursor = await conn.execute(
                "SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ? LIMIT 1",
                (user_id, item_id)
            )
            row = await cursor.fetchone()
            
            if not row:
                return False
            
            current_quantity = row['quantity']
            
            if current_quantity > quantity:
                # Decrease quantity
                await conn.execute(
                    "UPDATE inventory SET quantity = ? WHERE id = ?",
                    (current_quantity - quantity, row['id'])
                )
            elif current_quantity == quantity:
                # Remove item completely
                await conn.execute(
                    "DELETE FROM inventory WHERE id = ?",
                    (row['id'],)
                )
            else:
                return False
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error removing item from inventory: {e}")
            return False
    
    async def equip_item(self, user_id: int, item_id: str) -> bool:
        """Equip item and unequip others of same type"""
        try:
            conn = await self.get_connection()
            
            # Get item details
            cursor = await conn.execute(
                "SELECT item_type FROM inventory WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            )
            row = await cursor.fetchone()
            
            if not row:
                return False
            
            item_type = row['item_type']
            
            # Only weapons and armor can be equipped
            if item_type not in ['weapon', 'armor']:
                return False
            
            # Unequip other items of same type
            await conn.execute(
                "UPDATE inventory SET is_equipped = 0 WHERE user_id = ? AND item_type = ?",
                (user_id, item_type)
            )
            
            # Equip the item
            await conn.execute(
                "UPDATE inventory SET is_equipped = 1 WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            )
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error equipping item: {e}")
            return False
    
    async def unequip_item(self, user_id: int, item_id: str) -> bool:
        """Unequip specific item"""
        try:
            conn = await self.get_connection()
            
            await conn.execute(
                "UPDATE inventory SET is_equipped = 0 WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            )
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error unequipping item: {e}")
            return False
    
    async def get_equipped_items(self, user_id: int) -> List[InventoryItem]:
        """Get all equipped items for user"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT * FROM inventory WHERE user_id = ? AND is_equipped = 1",
                (user_id,)
            )
            rows = await cursor.fetchall()
            
            return [InventoryItem.from_dict(dict(row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting equipped items: {e}")
            return []
    
    # =====================================================
    # STATISTICS OPERATIONS
    # =====================================================
    
    async def get_statistics(self, user_id: int) -> Optional[Statistics]:
        """Get user statistics"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT * FROM statistics WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                return Statistics.from_dict(dict(row))
            
            # Create default statistics if none exist
            default_stats = Statistics(user_id=user_id, created_at=datetime.now())
            await self.update_statistics(default_stats)
            return default_stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return None
    
    async def update_statistics(self, stats: Statistics) -> bool:
        """Update user statistics"""
        try:
            conn = await self.get_connection()
            stats.updated_at = datetime.now()
            stats_data = stats.to_dict()
            
            await conn.execute('''
                INSERT OR REPLACE INTO statistics
                (user_id, enemies_killed, total_damage_dealt, total_damage_received,
                 critical_hits, blocks_performed, arena_wins, arena_losses, arena_draws,
                 highest_arena_streak, current_arena_streak, dungeons_completed,
                 bosses_defeated, deepest_dungeon_level, gold_earned, gold_spent,
                 items_found, items_sold, total_playtime_hours, sessions_count,
                 quests_completed, daily_streaks, max_daily_streak, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                stats_data['user_id'], stats_data['enemies_killed'], 
                stats_data['total_damage_dealt'], stats_data['total_damage_received'],
                stats_data['critical_hits'], stats_data['blocks_performed'],
                stats_data['arena_wins'], stats_data['arena_losses'], stats_data['arena_draws'],
                stats_data['highest_arena_streak'], stats_data['current_arena_streak'],
                stats_data['dungeons_completed'], stats_data['bosses_defeated'],
                stats_data['deepest_dungeon_level'], stats_data['gold_earned'],
                stats_data['gold_spent'], stats_data['items_found'], stats_data['items_sold'],
                stats_data['total_playtime_hours'], stats_data['sessions_count'],
                stats_data['quests_completed'], stats_data['daily_streaks'],
                stats_data['max_daily_streak'], stats_data['created_at'], 
                stats_data['updated_at']
            ))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
            return False

    async def update_statistics_by_id(self, user_id: int, updates: dict) -> bool:
        """Update user statistics by user_id with specific updates"""
        try:
            # Get current statistics
            stats = await self.get_statistics(user_id)
            if not stats:
                # Create new statistics if doesn't exist
                stats = Statistics(user_id=user_id)
            
            # Apply updates (increment values)
            for key, value in updates.items():
                if hasattr(stats, key):
                    current_value = getattr(stats, key, 0)
                    setattr(stats, key, current_value + value)
            
            # Update in database
            return await self.update_statistics(stats)
        except Exception as e:
            logger.error(f"Error updating statistics by ID: {e}")
            return False
    
    async def update_combat_statistics(self, user_id: int, damage_dealt: int, damage_received: int,
                                     critical_hit: bool = False, blocked: bool = False,
                                     enemy_killed: bool = False) -> bool:
        """Update combat-specific statistics"""
        try:
            stats = await self.get_statistics(user_id)
            if not stats:
                return False
            
            stats.update_combat_stats(damage_dealt, damage_received, critical_hit, blocked, enemy_killed)
            return await self.update_statistics(stats)
            
        except Exception as e:
            logger.error(f"Error updating combat statistics: {e}")
            return False
    
    async def update_arena_statistics(self, user_id: int, won: bool, draw: bool = False) -> bool:
        """Update arena-specific statistics"""
        try:
            stats = await self.get_statistics(user_id)
            if not stats:
                return False
            
            stats.update_arena_stats(won, draw)
            return await self.update_statistics(stats)
            
        except Exception as e:
            logger.error(f"Error updating arena statistics: {e}")
            return False
    
    async def update_economy_statistics(self, user_id: int, gold_earned: int = 0, 
                                      gold_spent: int = 0, items_found: int = 0, 
                                      items_sold: int = 0) -> bool:
        """Update economy-specific statistics"""
        try:
            stats = await self.get_statistics(user_id)
            if not stats:
                return False
            
            stats.update_economy_stats(gold_earned, gold_spent, items_found, items_sold)
            return await self.update_statistics(stats)
            
        except Exception as e:
            logger.error(f"Error updating economy statistics: {e}")
            return False
    
    # =====================================================
    # ACHIEVEMENT OPERATIONS
    # =====================================================
    
    async def get_achievements(self, user_id: int, unlocked_only: bool = False) -> List[Achievement]:
        """Get user's achievements"""
        try:
            conn = await self.get_connection()
            
            query = "SELECT * FROM achievements WHERE user_id = ?"
            params = [user_id]
            
            if unlocked_only:
                query += " AND is_unlocked = 1"
            
            query += " ORDER BY unlocked_at DESC, achievement_id"
            
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            
            achievements = []
            for row in rows:
                achievements.append(Achievement.from_dict(dict(row)))
            
            return achievements
            
        except Exception as e:
            logger.error(f"Error getting achievements: {e}")
            return []
    
    async def add_achievement(self, achievement: Achievement) -> bool:
        """Add achievement to user"""
        try:
            conn = await self.get_connection()
            achievement_data = achievement.to_dict()
            
            await conn.execute('''
                INSERT OR REPLACE INTO achievements
                (user_id, achievement_id, name, description, achievement_type,
                 requirements, rewards, is_unlocked, progress, max_progress,
                 unlocked_at, is_hidden)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                achievement_data['user_id'], achievement_data['achievement_id'],
                achievement_data['name'], achievement_data['description'],
                achievement_data['achievement_type'], achievement_data['requirements'],
                achievement_data['rewards'], achievement_data['is_unlocked'],
                achievement_data['progress'], achievement_data['max_progress'],
                achievement_data['unlocked_at'], achievement_data['is_hidden']
            ))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error adding achievement: {e}")
            return False
    
    async def unlock_achievement(self, user_id: int, achievement_id: str) -> Optional[Achievement]:
        """Unlock specific achievement and return it"""
        try:
            conn = await self.get_connection()
            
            # Get the achievement first
            cursor = await conn.execute('''
                SELECT * FROM achievements 
                WHERE user_id = ? AND achievement_id = ? AND is_unlocked = 0
            ''', (user_id, achievement_id))
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            # Unlock the achievement
            unlock_time = datetime.now().isoformat()
            await conn.execute('''
                UPDATE achievements 
                SET is_unlocked = 1, unlocked_at = ?, progress = max_progress
                WHERE user_id = ? AND achievement_id = ?
            ''', (unlock_time, user_id, achievement_id))
            
            await conn.commit()
            
            # Return the unlocked achievement
            achievement_data = dict(row)
            achievement_data['is_unlocked'] = True
            achievement_data['unlocked_at'] = unlock_time
            achievement_data['progress'] = achievement_data['max_progress']
            
            logger.info(f"Unlocked achievement {achievement_id} for user {user_id}")
            return Achievement.from_dict(achievement_data)
            
        except Exception as e:
            logger.error(f"Error unlocking achievement: {e}")
            return None
    
    async def update_achievement_progress(self, user_id: int, achievement_id: str, progress: int) -> bool:
        """Update achievement progress"""
        try:
            conn = await self.get_connection()
            
            await conn.execute('''
                UPDATE achievements 
                SET progress = ?
                WHERE user_id = ? AND achievement_id = ? AND is_unlocked = 0
            ''', (progress, user_id, achievement_id))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating achievement progress: {e}")
            return False
    
    async def check_and_unlock_achievements(self, user_id: int) -> List[Achievement]:
        """Check all achievements and unlock any that are completed"""
        try:
            # Get current character and statistics
            character = await self.get_character(user_id)
            stats = await self.get_statistics(user_id)
            
            if not character or not stats:
                return []
            
            # Get all locked achievements
            achievements = await self.get_achievements(user_id, unlocked_only=False)
            locked_achievements = [a for a in achievements if not a.is_unlocked]
            
            # Combine stats for checking
            current_stats = {
                'level': character.level,
                'enemies_killed': stats.enemies_killed,
                'critical_hits': stats.critical_hits,
                'arena_wins': stats.arena_wins,
                'highest_arena_streak': stats.highest_arena_streak,
                'dungeons_completed': stats.dungeons_completed,
                'deepest_dungeon_level': stats.deepest_dungeon_level,
                'items_found': stats.items_found,
                'gold_earned': stats.gold_earned,
                'daily_streaks': stats.daily_streaks,
                'quests_completed': stats.quests_completed
            }
            
            unlocked = []
            for achievement in locked_achievements:
                if achievement.check_progress(current_stats):
                    unlocked_achievement = await self.unlock_achievement(user_id, achievement.achievement_id)
                    if unlocked_achievement:
                        unlocked.append(unlocked_achievement)
            
            return unlocked
            
        except Exception as e:
            logger.error(f"Error checking achievements: {e}")
            return []
    
    async def get_user_achievements(self, user_id: int) -> List:
        """Get simple list of user's earned achievements"""
        try:
            conn = await self.get_connection()
            async with conn.execute('''
                SELECT achievement_id, unlocked_at FROM achievements 
                WHERE user_id = ? AND is_unlocked = 1
                ORDER BY unlocked_at DESC
            ''', (user_id,)) as cursor:
                rows = await cursor.fetchall()
                
            # Return simple objects with just the data we need
            achievements = []
            for row in rows:
                achievements.append({
                    'achievement_id': row[0],
                    'unlocked_at': row[1]
                })
            
            return achievements
            
        except Exception as e:
            logger.error(f"Error getting user achievements: {e}")
            return []
    
    async def add_user_achievement(self, user_id: int, achievement_id: str) -> bool:
        """Add simple achievement record"""
        try:
            conn = await self.get_connection()
            unlock_time = datetime.now().isoformat()
            
            await conn.execute('''
                INSERT OR REPLACE INTO achievements 
                (user_id, achievement_id, name, description, achievement_type,
                 requirements, rewards, is_unlocked, progress, max_progress,
                 unlocked_at, is_hidden)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, 1, ?, 0)
            ''', (
                user_id, achievement_id, achievement_id, achievement_id, 
                'game', '{}', '{}', unlock_time
            ))
            
            await conn.commit()
            logger.info(f"Added achievement {achievement_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding user achievement: {e}")
            return False
    
    # DAILY QUESTS OPERATIONS
    
    async def get_daily_quests(self, user_id: int) -> List[Dict]:
        """Get user's daily quests"""
        try:
            conn = await self.get_connection()
            async with conn.execute('''
                SELECT * FROM daily_quests 
                WHERE user_id = ? 
                ORDER BY created_at ASC
            ''', (user_id,)) as cursor:
                rows = await cursor.fetchall()
                
            quests = []
            for row in rows:
                quests.append(dict(row))
            
            return quests
            
        except Exception as e:
            logger.error(f"Error getting daily quests: {e}")
            return []
    
    async def get_daily_quest(self, user_id: int, quest_id: str) -> Optional[Dict]:
        """Get specific daily quest"""
        try:
            conn = await self.get_connection()
            async with conn.execute('''
                SELECT * FROM daily_quests 
                WHERE user_id = ? AND quest_id = ?
            ''', (user_id, quest_id)) as cursor:
                row = await cursor.fetchone()
                
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Error getting daily quest: {e}")
            return None
    
    async def save_daily_quest(self, user_id: int, quest) -> bool:
        """Save daily quest to database"""
        try:
            conn = await self.get_connection()
            await conn.execute('''
                INSERT OR REPLACE INTO daily_quests 
                (user_id, quest_id, quest_type, name, description, requirement, 
                 current_progress, reward_experience, reward_gold, reward_item_id, 
                 reward_item_name, status, icon, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, quest.id, quest.quest_type.value, quest.name,
                quest.description, quest.requirement, quest.current_progress,
                quest.reward.experience, quest.reward.gold, quest.reward.item_id,
                quest.reward.item_name, quest.status.value, quest.icon,
                datetime.now().isoformat()
            ))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving daily quest: {e}")
            return False
    
    async def update_quest_progress(self, user_id: int, quest_id: str, progress: int, status: str) -> bool:
        """Update quest progress"""
        try:
            conn = await self.get_connection()
            await conn.execute('''
                UPDATE daily_quests 
                SET current_progress = ?, status = ?
                WHERE user_id = ? AND quest_id = ?
            ''', (progress, status, user_id, quest_id))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating quest progress: {e}")
            return False
    
    async def update_quest_status(self, user_id: int, quest_id: str, status: str) -> bool:
        """Update quest status"""
        try:
            conn = await self.get_connection()
            await conn.execute('''
                UPDATE daily_quests 
                SET status = ?
                WHERE user_id = ? AND quest_id = ?
            ''', (status, user_id, quest_id))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating quest status: {e}")
            return False
    
    async def clear_daily_quests(self, user_id: int) -> bool:
        """Clear all daily quests for user"""
        try:
            conn = await self.get_connection()
            await conn.execute('''
                DELETE FROM daily_quests WHERE user_id = ?
            ''', (user_id,))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error clearing daily quests: {e}")
            return False
    
    async def get_user_data(self, user_id: int, key: str) -> Optional[str]:
        """Get user data by key"""
        try:
            conn = await self.get_connection()
            async with conn.execute('''
                SELECT value FROM user_data 
                WHERE user_id = ? AND key = ?
            ''', (user_id, key)) as cursor:
                row = await cursor.fetchone()
                
            return row[0] if row else None
            
        except Exception as e:
            logger.error(f"Error getting user data: {e}")
            return None
    
    async def set_user_data(self, user_id: int, key: str, value: str) -> bool:
        """Set user data"""
        try:
            conn = await self.get_connection()
            await conn.execute('''
                INSERT OR REPLACE INTO user_data (user_id, key, value)
                VALUES (?, ?, ?)
            ''', (user_id, key, value))
            
            await conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error setting user data: {e}")
            return False
    
    # =====================================================
    # UTILITY AND ADMIN OPERATIONS
    # =====================================================
    
    async def get_leaderboard(self, stat_type: str = 'level', limit: int = 10) -> List[Dict[str, Any]]:
        """Get leaderboard based on specified statistic"""
        try:
            conn = await self.get_connection()
            
            valid_stats = ['level', 'gold', 'enemies_killed', 'arena_wins', 'dungeons_completed']
            if stat_type not in valid_stats:
                stat_type = 'level'
            
            if stat_type in ['level', 'gold']:
                # From characters table
                cursor = await conn.execute(f'''
                    SELECT u.username, c.name, c.{stat_type}, c.class, c.level
                    FROM characters c
                    JOIN users u ON c.user_id = u.user_id
                    WHERE u.is_active = 1
                    ORDER BY c.{stat_type} DESC
                    LIMIT ?
                ''', (limit,))
            else:
                # From statistics table
                cursor = await conn.execute(f'''
                    SELECT u.username, c.name, s.{stat_type}, c.class, c.level
                    FROM statistics s
                    JOIN users u ON s.user_id = u.user_id
                    JOIN characters c ON s.user_id = c.user_id
                    WHERE u.is_active = 1
                    ORDER BY s.{stat_type} DESC
                    LIMIT ?
                ''', (limit,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            conn = await self.get_connection()
            
            stats = {}
            
            # Get table counts
            tables = ['users', 'characters', 'inventory', 'achievements', 'statistics']
            for table in tables:
                cursor = await conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                row = await cursor.fetchone()
                stats[f'{table}_count'] = row['count'] if row else 0
            
            # Get active users count
            cursor = await conn.execute("SELECT COUNT(*) as count FROM users WHERE is_active = 1")
            row = await cursor.fetchone()
            stats['active_users'] = row['count'] if row else 0
            
            # Get level distribution
            cursor = await conn.execute('''
                SELECT level, COUNT(*) as count 
                FROM characters 
                GROUP BY level 
                ORDER BY level
            ''')
            level_rows = await cursor.fetchall()
            stats['level_distribution'] = {row['level']: row['count'] for row in level_rows}
            
            # Get class distribution
            cursor = await conn.execute('''
                SELECT class, COUNT(*) as count 
                FROM characters 
                GROUP BY class
            ''')
            class_rows = await cursor.fetchall()
            stats['class_distribution'] = {row['class']: row['count'] for row in class_rows}
            
            # Get database file size
            import os
            if os.path.exists(self.db_path):
                stats['database_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    async def get_active_users_count(self) -> int:
        """Get count of active users"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT COUNT(*) as count FROM users WHERE is_active = 1"
            )
            row = await cursor.fetchone()
            return row['count'] if row else 0
            
        except Exception as e:
            logger.error(f"Error getting active users count: {e}")
            return 0
    
    async def get_characters_count(self) -> int:
        """Get total characters count"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute("SELECT COUNT(*) as count FROM characters")
            row = await cursor.fetchone()
            return row['count'] if row else 0
            
        except Exception as e:
            logger.error(f"Error getting characters count: {e}")
            return 0
    
    # =====================================================
    # BATCH AND PERFORMANCE OPERATIONS  
    # =====================================================
    
    async def batch_update_characters(self, characters: List[Character]) -> bool:
        """Update multiple characters in a single transaction"""
        try:
            conn = await self.get_connection()
            
            for character in characters:
                character.last_played = datetime.now()
                character_data = character.to_dict()
                
                await conn.execute('''
                    UPDATE characters SET
                    name = ?, class = ?, level = ?, experience = ?, experience_needed = ?,
                    health = ?, max_health = ?, mana = ?, max_mana = ?, attack = ?,
                    defense = ?, magic_power = ?, speed = ?, critical_chance = ?,
                    block_chance = ?, gold = ?, weapon = ?, armor = ?, 
                    dungeon_progress = ?, daily_quests_completed = ?, 
                    last_daily_reset = ?, last_played = ?
                    WHERE user_id = ?
                ''', (
                    character_data['name'], character_data['class'], character_data['level'],
                    character_data['experience'], character_data['experience_needed'],
                    character_data['health'], character_data['max_health'],
                    character_data['mana'], character_data['max_mana'],
                    character_data['attack'], character_data['defense'],
                    character_data['magic_power'], character_data['speed'],
                    character_data['critical_chance'], character_data['block_chance'],
                    character_data['gold'], character_data['weapon'], character_data['armor'],
                    character_data['dungeon_progress'], character_data['daily_quests_completed'],
                    character_data['last_daily_reset'], character_data['last_played'],
                    character_data['user_id']
                ))
            
            await conn.commit()
            logger.info(f"Batch updated {len(characters)} characters")
            return True
            
        except Exception as e:
            logger.error(f"Error in batch update: {e}")
            return False
    
    async def vacuum_database(self) -> bool:
        """Optimize database performance"""
        try:
            conn = await self.get_connection()
            await conn.execute("VACUUM")
            logger.info("Database vacuumed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error vacuuming database: {e}")
            return False
    
    async def cleanup_old_data(self, days_old: int = 90) -> Dict[str, int]:
        """Clean up old data for performance"""
        try:
            conn = await self.get_connection()
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
            
            cleanup_stats = {}
            
            # Remove old unequipped consumables
            cursor = await conn.execute('''
                DELETE FROM inventory 
                WHERE item_type = 'consumable' AND is_equipped = 0 AND obtained_at < ?
            ''', (cutoff_date,))
            cleanup_stats['old_consumables_removed'] = cursor.rowcount
            
            # Archive old achievements (mark as archived instead of deleting)
            await conn.execute('''
                UPDATE achievements 
                SET is_hidden = 1 
                WHERE unlocked_at < ? AND is_unlocked = 1
            ''', (cutoff_date,))
            
            await conn.commit()
            logger.info(f"Cleaned up old data: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return {}
    
    # =====================================================
    # SPECIALIZED QUERY METHODS
    # =====================================================
    
    async def get_top_players_by_level(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top players by level"""
        return await self.get_leaderboard('level', limit)
    
    async def get_richest_players(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get richest players by gold"""
        return await self.get_leaderboard('gold', limit)
    
    async def get_arena_champions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top arena fighters"""
        return await self.get_leaderboard('arena_wins', limit)
    
    async def search_characters(self, search_term: str, limit: int = 10) -> List[Character]:
        """Search characters by name"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute('''
                SELECT * FROM characters 
                WHERE name LIKE ? 
                ORDER BY level DESC, name 
                LIMIT ?
            ''', (f'%{search_term}%', limit))
            
            rows = await cursor.fetchall()
            return [Character.from_dict(dict(row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Error searching characters: {e}")
            return []
    
    async def get_users_by_last_active(self, hours_ago: int = 24) -> List[User]:
        """Get users active within specified hours"""
        try:
            conn = await self.get_connection()
            cutoff_time = (datetime.now() - timedelta(hours=hours_ago)).isoformat()
            
            cursor = await conn.execute('''
                SELECT * FROM users 
                WHERE last_active >= ? AND is_active = 1
                ORDER BY last_active DESC
            ''', (cutoff_time,))
            
            rows = await cursor.fetchall()
            return [User.from_dict(dict(row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting recent users: {e}")
            return []
    
    # =====================================================
    # TRANSACTION METHODS
    # =====================================================
    
    async def transfer_gold(self, from_user_id: int, to_user_id: int, amount: int) -> bool:
        """Transfer gold between characters (admin function)"""
        try:
            conn = await self.get_connection()
            
            # Start transaction
            await conn.execute("BEGIN TRANSACTION")
            
            try:
                # Check sender has enough gold
                cursor = await conn.execute(
                    "SELECT gold FROM characters WHERE user_id = ?",
                    (from_user_id,)
                )
                sender_row = await cursor.fetchone()
                
                if not sender_row or sender_row['gold'] < amount:
                    await conn.execute("ROLLBACK")
                    return False
                
                # Check receiver exists
                cursor = await conn.execute(
                    "SELECT user_id FROM characters WHERE user_id = ?",
                    (to_user_id,)
                )
                receiver_row = await cursor.fetchone()
                
                if not receiver_row:
                    await conn.execute("ROLLBACK")
                    return False
                
                # Update gold amounts
                await conn.execute(
                    "UPDATE characters SET gold = gold - ? WHERE user_id = ?",
                    (amount, from_user_id)
                )
                
                await conn.execute(
                    "UPDATE characters SET gold = gold + ? WHERE user_id = ?",
                    (amount, to_user_id)
                )
                
                # Commit transaction
                await conn.execute("COMMIT")
                
                logger.info(f"Transferred {amount} gold from {from_user_id} to {to_user_id}")
                return True
                
            except Exception as e:
                await conn.execute("ROLLBACK")
                raise e
                
        except Exception as e:
            logger.error(f"Error transferring gold: {e}")
            return False
    
    async def apply_item_effects(self, user_id: int, item_id: str) -> bool:
        """Apply item effects to character (for consumables)"""
        try:
            conn = await self.get_connection()
            
            # Get item from inventory
            cursor = await conn.execute(
                "SELECT properties, quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            )
            item_row = await cursor.fetchone()
            
            if not item_row or item_row['quantity'] <= 0:
                return False
            
            # Parse item properties
            properties = json.loads(item_row['properties'])
            effects = properties.get('effect', {})
            
            # Get character
            character = await self.get_character(user_id)
            if not character:
                return False
            
            # Apply effects
            if 'heal' in effects:
                character.health = min(character.health + effects['heal'], character.max_health)
            
            if 'restore_mana' in effects:
                character.mana = min(character.mana + effects['restore_mana'], character.max_mana)
            
            # Update character
            await self.update_character(character)
            
            # Remove one item from inventory
            await self.remove_item_from_inventory(user_id, item_id, 1)
            
            logger.info(f"Applied item {item_id} effects for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying item effects: {e}")
            return False
    
    # =====================================================
    # DATA EXPORT/IMPORT METHODS
    # =====================================================
    
    async def export_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Export all user data for backup or transfer"""
        try:
            user_data = {}
            
            # Get user info
            user = await self.get_user(user_id)
            if user:
                user_data['user'] = user.to_dict()
            
            # Get character
            character = await self.get_character(user_id)
            if character:
                user_data['character'] = character.to_dict()
            
            # Get inventory
            inventory = await self.get_inventory(user_id)
            user_data['inventory'] = [item.to_dict() for item in inventory.items]
            
            # Get achievements
            achievements = await self.get_achievements(user_id)
            user_data['achievements'] = [achievement.to_dict() for achievement in achievements]
            
            # Get statistics
            stats = await self.get_statistics(user_id)
            if stats:
                user_data['statistics'] = stats.to_dict()
            
            user_data['export_timestamp'] = datetime.now().isoformat()
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error exporting user data: {e}")
            return None
    
    async def import_user_data(self, user_data: Dict[str, Any], overwrite: bool = False) -> bool:
        """Import user data from backup"""
        try:
            user_id = user_data['user']['user_id']
            
            # Check if user exists
            existing_user = await self.get_user(user_id)
            if existing_user and not overwrite:
                logger.warning(f"User {user_id} already exists and overwrite is False")
                return False
            
            # Import user
            if 'user' in user_data:
                user = User.from_dict(user_data['user'])
                await self.create_user(user.user_id, user.username)
            
            # Import character
            if 'character' in user_data:
                await self.create_character(user_data['character'])
            
            # Import inventory
            if 'inventory' in user_data:
                for item_data in user_data['inventory']:
                    item = InventoryItem.from_dict(item_data)
                    await self.add_item_to_inventory(user_id, item)
            
            # Import achievements
            if 'achievements' in user_data:
                for achievement_data in user_data['achievements']:
                    achievement = Achievement.from_dict(achievement_data)
                    await self.add_achievement(achievement)
            
            # Import statistics
            if 'statistics' in user_data:
                stats = Statistics.from_dict(user_data['statistics'])
                await self.update_statistics(stats)
            
            logger.info(f"Imported data for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing user data: {e}")
            return False
    
    # =====================================================
    # DAILY RESET AND MAINTENANCE
    # =====================================================
    
    async def reset_daily_quests(self, reset_hour: int = 0) -> int:
        """Reset daily quests for all users at specified hour"""
        try:
            conn = await self.get_connection()
            
            current_time = datetime.now()
            reset_time = current_time.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
            
            # Get characters that need daily reset
            cursor = await conn.execute('''
                SELECT user_id, last_daily_reset 
                FROM characters 
                WHERE last_daily_reset IS NULL OR last_daily_reset < ?
            ''', (reset_time.isoformat(),))
            
            users_to_reset = await cursor.fetchall()
            
            # Reset daily quests for each user
            for user in users_to_reset:
                await conn.execute('''
                    UPDATE characters 
                    SET daily_quests_completed = 0, last_daily_reset = ?
                    WHERE user_id = ?
                ''', (current_time.isoformat(), user['user_id']))
            
            await conn.commit()
            
            logger.info(f"Reset daily quests for {len(users_to_reset)} users")
            return len(users_to_reset)
            
        except Exception as e:
            logger.error(f"Error resetting daily quests: {e}")
            return 0
    
    async def cleanup_inactive_users(self, days_inactive: int = 30) -> int:
        """Mark inactive users as inactive (soft delete)"""
        try:
            conn = await self.get_connection()
            cutoff_date = (datetime.now() - timedelta(days=days_inactive)).isoformat()
            
            # Find inactive users
            cursor = await conn.execute('''
                SELECT user_id FROM users 
                WHERE last_active < ? AND is_active = 1
            ''', (cutoff_date,))
            
            inactive_users = await cursor.fetchall()
            
            # Mark as inactive
            for user in inactive_users:
                await conn.execute(
                    "UPDATE users SET is_active = 0 WHERE user_id = ?",
                    (user['user_id'],)
                )
            
            await conn.commit()
            
            logger.info(f"Marked {len(inactive_users)} users as inactive")
            return len(inactive_users)
            
        except Exception as e:
            logger.error(f"Error cleaning up inactive users: {e}")
            return 0
    
    # =====================================================
    # ADVANCED QUERY METHODS
    # =====================================================
    
    async def get_user_rank(self, user_id: int, stat_type: str = 'level') -> Optional[int]:
        """Get user's rank in specified statistic"""
        try:
            conn = await self.get_connection()
            
            if stat_type in ['level', 'gold']:
                cursor = await conn.execute(f'''
                    SELECT COUNT(*) + 1 as rank
                    FROM characters c1
                    JOIN users u1 ON c1.user_id = u1.user_id
                    WHERE u1.is_active = 1 AND c1.{stat_type} > (
                        SELECT c2.{stat_type}
                        FROM characters c2
                        WHERE c2.user_id = ?
                    )
                ''', (user_id,))
            else:
                cursor = await conn.execute(f'''
                    SELECT COUNT(*) + 1 as rank
                    FROM statistics s1
                    JOIN users u1 ON s1.user_id = u1.user_id
                    WHERE u1.is_active = 1 AND s1.{stat_type} > (
                        SELECT s2.{stat_type}
                        FROM statistics s2
                        WHERE s2.user_id = ?
                    )
                ''', (user_id,))
            
            row = await cursor.fetchone()
            return row['rank'] if row else None
            
        except Exception as e:
            logger.error(f"Error getting user rank: {e}")
            return None
    
    async def get_guild_stats(self, guild_name: str) -> Dict[str, Any]:
        """Get statistics for guild (future feature)"""
        # Placeholder for guild system
        return {
            'total_members': 0,
            'average_level': 0,
            'total_gold': 0,
            'guild_achievements': []
        }
    
    # =====================================================
    # BACKUP AND RESTORE METHODS
    # =====================================================
    
    async def create_full_backup(self) -> str:
        """Create complete database backup"""
        try:
            import shutil
            from pathlib import Path
            
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"game_backup_{timestamp}.db"
            backup_path = backup_dir / backup_filename
            
            # Close connection for backup
            await self.close()
            
            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            
            # Reconnect
            await self.get_connection()
            
            logger.info(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return ""
    
    async def restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            import shutil
            
            # Close current connection
            await self.close()
            
            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            
            # Reconnect and verify
            await self.get_connection()
            stats = await self.get_database_stats()
            
            logger.info(f"Restored from backup: {backup_path}, Stats: {stats}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            return False
    
    # =====================================================
    # USER LIST OPERATIONS
    # =====================================================
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users from database"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT user_id, username, created_at, last_active FROM users ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
            
            users = []
            for row in rows:
                users.append({
                    'user_id': row['user_id'],
                    'username': row['username'],
                    'created_at': row['created_at'],
                    'last_active': row['last_active']
                })
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    async def get_total_users(self) -> int:
        """Get total number of users"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute("SELECT COUNT(*) as count FROM users")
            row = await cursor.fetchone()
            return row['count'] if row else 0
            
        except Exception as e:
            logger.error(f"Error getting total users: {e}")
            return 0
    
    async def get_active_users_today(self) -> int:
        """Get number of users active today"""
        try:
            conn = await self.get_connection()
            today = datetime.now().strftime('%Y-%m-%d')
            cursor = await conn.execute(
                "SELECT COUNT(*) as count FROM users WHERE DATE(last_active) = ?",
                (today,)
            )
            row = await cursor.fetchone()
            return row['count'] if row else 0
            
        except Exception as e:
            logger.error(f"Error getting active users today: {e}")
            return 0
    
    async def get_active_users_week(self) -> int:
        """Get number of users active this week"""
        try:
            conn = await self.get_connection()
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            cursor = await conn.execute(
                "SELECT COUNT(*) as count FROM users WHERE DATE(last_active) >= ?",
                (week_ago,)
            )
            row = await cursor.fetchone()
            return row['count'] if row else 0
            
        except Exception as e:
            logger.error(f"Error getting active users week: {e}")
            return 0
    
    async def get_total_characters(self) -> int:
        """Get total number of characters"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute("SELECT COUNT(*) as count FROM characters")
            row = await cursor.fetchone()
            return row['count'] if row else 0
            
        except Exception as e:
            logger.error(f"Error getting total characters: {e}")
            return 0
    
    async def get_average_level(self) -> float:
        """Get average character level"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute("SELECT AVG(level) as avg_level FROM characters")
            row = await cursor.fetchone()
            return float(row['avg_level']) if row and row['avg_level'] else 0.0
            
        except Exception as e:
            logger.error(f"Error getting average level: {e}")
            return 0.0
    
    async def get_popular_class(self) -> str:
        """Get most popular character class"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT class, COUNT(*) as count FROM characters GROUP BY class ORDER BY count DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            return row['class'] if row else "Невідомо"
            
        except Exception as e:
            logger.error(f"Error getting popular class: {e}")
            return "Невідомо"
    
    async def get_total_gold_earned(self) -> int:
        """Get total gold earned by all players"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute("SELECT SUM(gold) as total_gold FROM characters")
            row = await cursor.fetchone()
            return int(row['total_gold']) if row and row['total_gold'] else 0
            
        except Exception as e:
            logger.error(f"Error getting total gold earned: {e}")
            return 0
    
    # =====================================================
    # CONTEXT MANAGERS AND UTILITIES
    # =====================================================
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.get_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, '_connection') and self._connection:
            # Note: Can't use async in __del__, so we schedule it
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except:
                pass


# =====================================================
# HELPER FUNCTIONS
# =====================================================

async def get_character_with_stats(db_manager: DatabaseManager, user_id: int) -> Optional[Dict[str, Any]]:
    """Get character with complete statistics"""
    character = await db_manager.get_character(user_id)
    if not character:
        return None
    
    stats = await db_manager.get_statistics(user_id)
    inventory = await db_manager.get_inventory(user_id)
    achievements = await db_manager.get_achievements(user_id, unlocked_only=True)
    
    return {
        'character': character,
        'statistics': stats,
        'inventory': inventory,
        'achievements': achievements,
        'equipped_items': inventory.get_equipped_items(),
        'combat_power': character.calculate_combat_power()
    }


async def create_character_with_defaults(db_manager: DatabaseManager, user_id: int, 
                                       username: str, name: str, char_class: str) -> bool:
    """Create character with default stats from config"""
    from config import CHARACTER_CLASSES
    
    # Get class configuration
    class_config = CHARACTER_CLASSES.get(char_class, CHARACTER_CLASSES['warrior'])
    base_stats = class_config['base_stats']
    start_equipment = class_config['start_equipment']
    
    # Prepare character data with all required characteristics
    character_data = {
        'user_id': user_id,
        'username': username,
        'name': name,
        'class': char_class,
        'level': 1,
        'experience': 0,
        'experience_needed': 100,
        'health': base_stats['health'],
        'max_health': base_stats['max_health'],
        'mana': base_stats.get('mana', 0),
        'max_mana': base_stats.get('max_mana', 0),
        'attack': base_stats['attack'],
        'defense': base_stats['defense'],
        'magic_power': base_stats.get('magic_power', 0),
        'speed': base_stats['speed'],
        'critical_chance': base_stats['critical_chance'],
        'block_chance': base_stats['block_chance'],
        'gold': class_config.get('starting_gold', 50),
        'weapon': start_equipment['weapon'],
        'armor': start_equipment['armor'],
        'dungeon_progress': 0,
        'daily_quests_completed': 0
    }
    
    return await db_manager.create_character(character_data)


# =====================================================
# DATABASE TESTING UTILITIES
# =====================================================

async def test_database_operations(db_manager: DatabaseManager) -> bool:
    """Test all major database operations"""
    try:
        test_user_id = 999999999
        
        logger.info("Testing database operations...")
        
        # Test user creation
        success = await db_manager.create_user(test_user_id, "test_user")
        assert success, "User creation failed"
        
        # Test character creation
        success = await create_character_with_defaults(
            db_manager, test_user_id, "test_user", "Test Hero", "warrior"
        )
        assert success, "Character creation failed"
        
        # Test character retrieval
        character = await db_manager.get_character(test_user_id)
        assert character is not None, "Character retrieval failed"
        assert character.name == "Test Hero", "Character data incorrect"
        
        # Test inventory operations
        from database.database_models import InventoryItem
        test_item = InventoryItem(
            item_id='test_item',
            user_id=test_user_id,
            item_type='consumable',
            name='Test Item',
            description='Test item description',
            quantity=5,
            obtained_at=datetime.now()
        )
        
        success = await db_manager.add_item_to_inventory(test_user_id, test_item)
        assert success, "Adding item failed"
        
        inventory = await db_manager.get_inventory(test_user_id)
        assert len(inventory.items) > 0, "Inventory retrieval failed"
        
        # Test statistics
        stats = await db_manager.get_statistics(test_user_id)
        assert stats is not None, "Statistics retrieval failed"
        
        # Test achievement
        from database.database_models import Achievement, AchievementType
        test_achievement = Achievement(
            achievement_id='test_achievement',
            user_id=test_user_id,
            name='Test Achievement',
            description='Test description',
            achievement_type=AchievementType.SPECIAL.value,
            requirements={'test': 1},
            max_progress=1
        )
        
        success = await db_manager.add_achievement(test_achievement)
        assert success, "Achievement creation failed"
        
        # Cleanup test data
        await db_manager.delete_character(test_user_id)
        
        logger.info("✅ All database operations tested successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False