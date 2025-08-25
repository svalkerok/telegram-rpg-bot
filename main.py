#!/usr/bin/env python3
"""
Telegram RPG Bot "Легенди Валгаллії"
Main entry point
"""

import asyncio
import logging
import sys
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from database.db_manager import DatabaseManager
from handlers import (
    start_handler,
    character_handler,
    tavern_handler,
    dungeon_handler,
    forest_handler,
    arena_handler,
    shop_handler,
    admin_handler,
    stats_handler,
    daily_quests_handler,
    equipment_handler
)
from utils.utils_logging import setup_logging
from utils.utils_monitoring import GameMetrics


# Initialize logging
logger = setup_logging()

# Initialize database
db_manager = DatabaseManager(config.DATABASE_URL)

# Initialize metrics
game_metrics = GameMetrics()


async def post_init(application: Application) -> None:
    """Initialize bot after startup"""
    logger.info("Bot started successfully!")
    
    # Initialize database tables
    await db_manager.init_database()
    logger.info("Database initialized")
    
    # Load game data
    await load_game_data()
    logger.info("Game data loaded")
    
    # Initialize monitoring system
    from utils.monitoring import init_monitoring
    await init_monitoring(db_manager)
    logger.info("Monitoring system initialized")
    
    # Start automatic backups
    from utils.backup_util import BackupManager
    backup_manager = BackupManager(db_manager)
    backup_manager.schedule_backups()
    logger.info("Automatic backup system started")


async def post_shutdown(application: Application) -> None:
    """Cleanup on shutdown"""
    logger.info("Bot shutting down...")
    
    # Close database connection
    await db_manager.close()
    
    logger.info("Bot stopped")


async def load_game_data():
    """Load game data from JSON files"""
    from pathlib import Path
    import json
    
    data_path = Path('data')
    
    # Create data files if they don't exist
    if not (data_path / 'enemies.json').exists():
        await create_default_data_files()
    
    logger.info("Game data files checked/created")


async def create_default_data_files():
    """Create default data files if they don't exist"""
    import json
    from pathlib import Path
    
    data_path = Path('data')
    data_path.mkdir(exist_ok=True)
    
    # Default enemies data
    enemies_data = {
        "skeleton_warrior": {
            "name": "Скелет-воїн",
            "health": 40,
            "attack": 8,
            "defense": 2,
            "speed": 6,
            "experience_reward": 20,
            "gold_min": 15,
            "gold_max": 25,
            "description": "Кістки гримлять при кожному кроці"
        },
        "zombie": {
            "name": "Гнилий зомбі",
            "health": 60,
            "attack": 6,
            "defense": 1,
            "speed": 4,
            "experience_reward": 15,
            "gold_min": 10,
            "gold_max": 20,
            "description": "Повільний, але небезпечний"
        }
    }
    
    # Default items data
    items_data = {
        "iron_sword": {
            "name": "Залізний меч",
            "type": "weapon",
            "price": 100,
            "attack_bonus": 15,
            "description": "Надійний залізний меч для початківців"
        },
        "leather_armor": {
            "name": "Шкіряна броня",
            "type": "armor",
            "price": 60,
            "defense_bonus": 6,
            "description": "Легка та зручна шкіряна броня"
        },
        "health_potion": {
            "name": "Зілля здоров'я",
            "type": "consumable",
            "price": 50,
            "health_bonus": 80,
            "description": "Відновлює 80 пунктів здоров'я"
        }
    }
    
    # Default dungeons data
    dungeons_data = {
        "crypt": {
            "name": "Склеп Новачка",
            "min_level": 1,
            "max_level": 3,
            "entry_cost": 20,
            "rooms": 4,
            "boss": "bone_lord_mortis"
        }
    }
    
    # Default achievements data
    achievements_data = {
        "first_blood": {
            "name": "Перша кров",
            "description": "Вбийте першого ворога",
            "reward_xp": 10
        },
        "dungeon_crawler": {
            "name": "Дослідник підземель",
            "description": "Пройдіть перше підземелля",
            "reward_xp": 50
        }
    }
    
    # Save data files
    with open(data_path / 'enemies.json', 'w', encoding='utf-8') as f:
        json.dump(enemies_data, f, ensure_ascii=False, indent=2)
    
    with open(data_path / 'items.json', 'w', encoding='utf-8') as f:
        json.dump(items_data, f, ensure_ascii=False, indent=2)
    
    with open(data_path / 'dungeons.json', 'w', encoding='utf-8') as f:
        json.dump(dungeons_data, f, ensure_ascii=False, indent=2)
    
    with open(data_path / 'achievements.json', 'w', encoding='utf-8') as f:
        json.dump(achievements_data, f, ensure_ascii=False, indent=2)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Виникла помилка! Спробуйте ще раз або зверніться до адміністратора."
        )


def main() -> None:
    """Main function to run the bot"""
    
    # Check if token is set
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        sys.exit(1)
    
    # Initialize persistence for user data
    from telegram.ext import PicklePersistence
    persistence = PicklePersistence(filepath="bot_data.pickle")
    
    # Create application with persistence
    application = Application.builder().token(config.BOT_TOKEN).persistence(persistence).build()
    
    # Add initialization
    application.post_init = post_init
    application.post_shutdown = post_shutdown
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_handler.start_handler))
    application.add_handler(CommandHandler("help", start_handler.help_command))
    application.add_handler(CommandHandler("stats", character_handler.stats_command))
    

    application.add_handler(CommandHandler("admin", admin_handler.admin_panel))
    application.add_handler(CommandHandler("inventory", character_handler.inventory_command))
    application.add_handler(CommandHandler("quests", character_handler.quests_command))
    
    # Callback query handlers for inline keyboards  
    application.add_handler(CallbackQueryHandler(
        start_handler.character_creation_handler,
        pattern="^create_"
    ))
    application.add_handler(CallbackQueryHandler(
        start_handler.start_new_character_callback,
        pattern="^start_new_character$"
    ))
    application.add_handler(CallbackQueryHandler(
        tavern_handler.tavern_callback,
        pattern="^tavern_"
    ))
    application.add_handler(CallbackQueryHandler(
        tavern_handler.delete_character_confirmed,
        pattern="^confirm_delete_yes$"
    ))
    application.add_handler(CallbackQueryHandler(
        dungeon_handler.dungeon_callback,
        pattern="^dungeon_"
    ))
    application.add_handler(CallbackQueryHandler(
        forest_handler.forest_callback,
        pattern="^forest_"
    ))
    application.add_handler(CallbackQueryHandler(
        arena_handler.arena_callback,
        pattern="^arena_"
    ))
    application.add_handler(CallbackQueryHandler(
        shop_handler.shop_callback,
        pattern="^shop_"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_handler.admin_callback,
        pattern="^admin_"
    ))
    application.add_handler(CallbackQueryHandler(
        stats_handler.stats_callback,
        pattern="^stats_"
    ))
    application.add_handler(CallbackQueryHandler(
        daily_quests_handler.daily_quests_callback,
        pattern="^quest"
    ))
    
    # Equipment system handlers
    application.add_handler(CallbackQueryHandler(
        equipment_handler.equipment_callback,
        pattern="^(merchant_|inventory_|blacksmith_|buy_|upgrade_|equip_|unequip_|sell_|use_potion_)"
    ))
    
    # Character name input handler (for character creation) - MUST BE FIRST
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        start_handler.text_input_handler
    ), group=0)
    
    # Admin message handler for broadcast messages and custom gold input
    application.add_handler(MessageHandler(
        filters.TEXT & filters.User(user_id=config.ADMIN_USER_ID),
        admin_handler.process_admin_message
    ), group=1)
    
    # Potion usage handlers
    application.add_handler(CallbackQueryHandler(
        forest_handler.forest_callback,
        pattern="^combat_potion_menu$"
    ))
    application.add_handler(CallbackQueryHandler(
        forest_handler.forest_callback,
        pattern="^combat_use_potion_"
    ))
    
    # Combat potion handlers (work for both forest and arena when combat_* is used)
    application.add_handler(CallbackQueryHandler(
        arena_handler.arena_callback,
        pattern="^arena_combat_potion_menu$"
    ))
    application.add_handler(CallbackQueryHandler(
        arena_handler.arena_callback, 
        pattern="^arena_combat_use_potion_"
    ))
    
    # Message handlers
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        start_handler.text_input_handler
    ))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info(f"Starting bot in {'DEBUG' if config.DEBUG_MODE else 'PRODUCTION'} mode...")
    
    if config.WEBHOOK_URL and not config.DEBUG_MODE:
        # Production mode with webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            url_path=config.BOT_TOKEN,
            webhook_url=f"{config.WEBHOOK_URL}/{config.BOT_TOKEN}"
        )
    else:
        # Development mode with polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        sys.exit(1)