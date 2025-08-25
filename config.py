"""
Configuration file for Telegram RPG Bot "Легенди Валгаллії"
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///game.db')
DATABASE_BACKUP_PATH = 'backups/'

# Server Configuration
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
PORT = int(os.getenv('PORT', '8443'))
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/bot.log')
ENABLE_LOGGING = os.getenv('ENABLE_LOGGING', 'true').lower() == 'true'

# Game Configuration
MAX_LEVEL = int(os.getenv('MAX_LEVEL', '50'))
BASE_EXP_REQUIRED = int(os.getenv('BASE_EXP_REQUIRED', '100'))
EXP_MULTIPLIER = float(os.getenv('EXP_MULTIPLIER', '1.5'))
DAILY_QUEST_RESET_HOUR = int(os.getenv('DAILY_QUEST_RESET_HOUR', '0'))

# Performance Settings
MAX_PLAYERS_PER_SERVER = int(os.getenv('MAX_PLAYERS_PER_SERVER', '10000'))
BACKUP_INTERVAL_HOURS = int(os.getenv('BACKUP_INTERVAL_HOURS', '6'))
BACKUP_KEEP_DAYS = int(os.getenv('BACKUP_KEEP_DAYS', '7'))

# Character Classes Configuration
CHARACTER_CLASSES = {
    'warrior': {
        'name': 'Воїн',
        'emoji': '🗡',
        'base_stats': {
            'health': 100,
            'max_health': 100,
            'mana': 0,
            'max_mana': 0,
            'attack': 12,
            'defense': 8,
            'magic_power': 0,
            'speed': 8,
            'critical_chance': 10,
            'block_chance': 15
        },
        'level_bonus': {
            'health': 15,
            'mana': 0,
            'attack': 3,
            'defense': 2,
            'magic_power': 0,
            'speed': 1,
            'critical_chance': 0,
            'block_chance': 0
        },
        'start_equipment': {
            'weapon': 'iron_sword',
            'armor': 'leather_armor'
        }
    },
    'mage': {
        'name': 'Маг',
        'emoji': '🧙‍♂️',
        'base_stats': {
            'health': 70,
            'max_health': 70,
            'mana': 100,
            'max_mana': 100,
            'attack': 6,
            'defense': 3,
            'magic_power': 15,
            'speed': 12,
            'critical_chance': 10,
            'block_chance': 5
        },
        'level_bonus': {
            'health': 10,
            'mana': 15,
            'attack': 1,
            'defense': 1,
            'magic_power': 3,
            'speed': 1,
            'critical_chance': 0,
            'block_chance': 0
        },
        'start_equipment': {
            'weapon': 'wooden_staff',
            'armor': 'apprentice_robe'
        }
    },
    'ranger': {
        'name': 'Розвідник',
        'emoji': '🏹',
        'base_stats': {
            'health': 85,
            'max_health': 85,
            'mana': 0,
            'max_mana': 0,
            'attack': 10,
            'defense': 5,
            'magic_power': 0,
            'speed': 15,
            'critical_chance': 20,
            'block_chance': 5
        },
        'level_bonus': {
            'health': 12,
            'mana': 0,
            'attack': 2,
            'defense': 1,
            'magic_power': 0,
            'speed': 2,
            'critical_chance': 1,
            'block_chance': 0
        },
        'start_equipment': {
            'weapon': 'hunting_bow',
            'armor': 'leather_armor'
        }
    }
}

# Dungeon Configuration
DUNGEON_ENTRY_COSTS = {
    'crypt': 20,
    'orcs': 50,
    'tower': 100,
    'dragon': 200
}

DUNGEON_MIN_LEVELS = {
    'crypt': 1,
    'orcs': 3,
    'tower': 6,
    'dragon': 9
}

# Dungeon room limits
DUNGEON_MAX_ROOMS = {
    'crypt': 5,
    'orcs': 8,
    'tower': 10,
    'dragon': 15
}

# Dungeon enemy templates
DUNGEON_ENEMIES = {
    'crypt': {
        'name': 'Скелет-воїн',
        'health': 40,
        'attack': 8,
        'defense': 2,
        'exp_reward': 20,
        'gold_reward': 15
    },
    'orcs': {
        'name': 'Орк-берсерк',
        'health': 60,
        'attack': 12,
        'defense': 4,
        'exp_reward': 30,
        'gold_reward': 25
    },
    'tower': {
        'name': 'Темний маг',
        'health': 80,
        'attack': 15,
        'defense': 6,
        'exp_reward': 40,
        'gold_reward': 35
    },
    'dragon': {
        'name': 'Дракончик',
        'health': 120,
        'attack': 20,
        'defense': 8,
        'exp_reward': 60,
        'gold_reward': 50
    }
}

# Forest Zones Configuration
FOREST_ZONES = {
    'edge': {'min_level': 1, 'max_level': 2, 'name': 'Краї лісу'},
    'deep': {'min_level': 3, 'max_level': 4, 'name': 'Глибини лісу'},
    'cursed': {'min_level': 5, 'max_level': 6, 'name': 'Закляте серце лісу'},
    'cursed_lands': {'min_level': 7, 'max_level': 10, 'name': 'Прокляті землі'}
}

# Shop Configuration
SHOP_DISCOUNT_DAY = 2  # Wednesday
SHOP_DISCOUNT_PERCENT = 20

# Arena Configuration
ARENA_WIN_GOLD_MIN = 50
ARENA_WIN_GOLD_MAX = 100
ARENA_WIN_EXP_MIN = 30
ARENA_WIN_EXP_MAX = 60

# Special Events Configuration
EVENTS_CHECK_INTERVAL_HOURS = 1
RANDOM_EVENT_CHANCE = 5  # percent

# Message Templates
WELCOME_MESSAGE = """
🎮 **Ласкаво просимо до "Легенди Валгаллії"!**

📜 Ви прибули до містечка Камінний Притулок після довгої подорожі.
Попереду вас чекають пригоди, багатства та слава!

Щоб почати гру, створіть свого персонажа.
"""

TAVERN_MESSAGE = """
🏛 **Таверна "Камінний Притулок"**
━━━━━━━━━━━━━━━━━━━━━━━━━
👤 {name} | Рівень: {level}
💚 Здоров'я: {health}/{max_health}
⚡ Досвід: {experience}/{experience_needed}
💰 Золото: {gold} монет

Куди бажаєте вирушити, відважний авантюристе?
"""

# Validation Settings
MIN_CHARACTER_NAME_LENGTH = 2
MAX_CHARACTER_NAME_LENGTH = 20

# Rate Limiting
MAX_COMMANDS_PER_MINUTE = 30
COOLDOWN_DURATION = 60  # seconds

# File Paths
DATA_PATH = Path('data/')
LOGS_PATH = Path('logs/')
BACKUPS_PATH = Path('backups/')

# Create necessary directories
for path in [DATA_PATH, LOGS_PATH, BACKUPS_PATH]:
    path.mkdir(parents=True, exist_ok=True)