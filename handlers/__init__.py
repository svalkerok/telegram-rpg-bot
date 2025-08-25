"""
Handlers module initialization
Import all handlers for easy access
"""

# Import all handler modules
from . import (
    start_handler,
    character_handler,
    tavern_handler,
    dungeon_handler,
    forest_handler,
    arena_handler,
    shop_handler,
    admin_handler
)

# Export handler functions for main.py
__all__ = [
    'start_handler',
    'character_handler',
    'tavern_handler',
    'dungeon_handler',
    'forest_handler',
    'arena_handler',
    'shop_handler',
    'admin_handler'
]