"""
utils/constants.py — Enumerations and symbolic constants.

WHY THIS EXISTS:
  String comparisons like `if state == "playing"` are fragile — typos are silent
  bugs. Using IntEnum means mistyped names raise AttributeError immediately at
  import time. This file has ZERO game logic; it is a vocabulary file.
"""

from enum import IntEnum, auto


class GameState(IntEnum):
    """Top-level state machine for the game loop."""
    MAIN_MENU   = auto()
    PLAYING     = auto()
    PAUSED      = auto()
    GAME_OVER   = auto()


class ZombieType(IntEnum):
    """Maps to keys in settings.ZOMBIE_TYPES for O(1) lookup."""
    NORMAL = auto()
    FAST   = auto()
    TANK   = auto()
    BOSS   = auto()


class WeaponSlot(IntEnum):
    SLOT_1 = 0
    SLOT_2 = 1
    SLOT_3 = 2


# Weapon name → WeaponSlot index
WEAPON_ORDER = ["pistol", "shotgun", "smg"]

# ZombieType → settings key string
ZOMBIE_TYPE_KEYS = {
    ZombieType.NORMAL: "normal",
    ZombieType.FAST:   "fast",
    ZombieType.TANK:   "tank",
    ZombieType.BOSS:   "boss",
}
