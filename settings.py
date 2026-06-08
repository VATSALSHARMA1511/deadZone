"""
settings.py — Central configuration file.

WHY THIS EXISTS:
  Every magic number, color, and tunable value lives here. This means:
  - Zero hunting through multiple files to tweak balance
  - Easy difficulty tuning without touching game logic
  - Clear separation between "what the game does" and "how it's tuned"

ARCHITECTURE ROLE:
  Imported by almost every module. Read-only during runtime — nothing mutates
  these values. Game state (score, health) lives in entity/system classes, not here.
"""

# ─── Window ───────────────────────────────────────────────────────────────────
TITLE           = "DEADZONE"
SCREEN_W        = 1280
SCREEN_H        = 720
FPS_TARGET      = 60

# ─── World ────────────────────────────────────────────────────────────────────
WORLD_W         = 3200          # Pixels wide (2.5× screen)
WORLD_H         = 2400          # Pixels tall
TILE_SIZE       = 64            # Grid reference size

# ─── Colors (dark neon palette) ───────────────────────────────────────────────
C_BG            = (10,  12,  18)    # Near-black background
C_GRID          = (18,  22,  32)    # Subtle grid lines
C_PLAYER        = (0,   220, 180)   # Teal/cyan
C_PLAYER_ACCENT = (0,   255, 200)
C_BULLET        = (255, 220, 50)    # Yellow
C_BULLET_GLOW   = (255, 180, 0)
C_ZOMBIE        = (60,  180, 60)    # Sickly green
C_ZOMBIE_FAST   = (160, 255, 80)    # Bright lime — fast variant
C_ZOMBIE_TANK   = (120, 60,  200)   # Purple — tank variant
C_ZOMBIE_HIT    = (255, 80,  80)    # Flash on damage
C_HEALTH_BAR    = (220, 40,  40)
C_HEALTH_BAR_BG = (50,  20,  20)
C_HEALTH_GOOD   = (40,  200, 100)
C_XP_BAR        = (50,  130, 255)
C_WHITE         = (255, 255, 255)
C_BLACK         = (0,   0,   0)
C_DARK_GRAY     = (30,  35,  45)
C_MID_GRAY      = (80,  90,  110)
C_ACCENT_RED    = (255, 50,  70)
C_ACCENT_GOLD   = (255, 200, 50)
C_OVERLAY       = (0,   0,   0,    180)  # RGBA for semi-transparent surfaces
C_MUZZLE        = (255, 240, 140)

# ─── Player ───────────────────────────────────────────────────────────────────
PLAYER_SPEED        = 220           # px/s normal
PLAYER_SPRINT_SPEED = 360           # px/s sprinting
PLAYER_SPRINT_COST  = 30.0          # stamina/s drain while sprinting
PLAYER_STAMINA_MAX  = 100.0
PLAYER_STAMINA_REGEN= 20.0          # stamina/s when not sprinting
PLAYER_RADIUS       = 16            # Collision circle
PLAYER_HEALTH_MAX   = 100
PLAYER_IFRAMES      = 0.8           # Invincibility seconds after damage
PLAYER_DASH_SPEED   = 700           # px/s during dash
PLAYER_DASH_DUR     = 0.18          # seconds
PLAYER_DASH_COOLDOWN= 1.2           # seconds

# ─── Weapons ──────────────────────────────────────────────────────────────────
WEAPONS = {
    "pistol": {
        "damage":       25,
        "fire_rate":    0.35,       # seconds between shots
        "bullet_speed": 650,
        "ammo_max":     12,
        "reload_time":  1.4,
        "spread":       2.0,        # degrees of random spread
        "bullets_per_shot": 1,
    },
    "shotgun": {
        "damage":       18,         # per pellet
        "fire_rate":    0.75,
        "bullet_speed": 520,
        "ammo_max":     6,
        "reload_time":  2.2,
        "spread":       12.0,
        "bullets_per_shot": 5,
    },
    "smg": {
        "damage":       15,
        "fire_rate":    0.09,
        "bullet_speed": 720,
        "ammo_max":     30,
        "reload_time":  1.8,
        "spread":       4.0,
        "bullets_per_shot": 1,
    },
}
DEFAULT_WEAPON      = "pistol"

# ─── Bullets ──────────────────────────────────────────────────────────────────
BULLET_LIFETIME     = 1.8           # seconds before auto-despawn
BULLET_RADIUS       = 4

# ─── Zombies ──────────────────────────────────────────────────────────────────
ZOMBIE_TYPES = {
    "normal": {
        "speed":        85,
        "health":       60,
        "damage":       15,
        "radius":       18,
        "score_value":  10,
        "color":        None,       # uses C_ZOMBIE default
        "attack_rate":  1.0,        # seconds between attacks
    },
    "fast": {
        "speed":        160,
        "health":       35,
        "damage":       10,
        "radius":       14,
        "score_value":  20,
        "color":        None,       # uses C_ZOMBIE_FAST
        "attack_rate":  0.6,
    },
    "tank": {
        "speed":        50,
        "health":       200,
        "damage":       30,
        "radius":       28,
        "score_value":  50,
        "color":        None,       # uses C_ZOMBIE_TANK
        "attack_rate":  1.5,
    },
    "boss": {
        "speed":        70,
        "health":       600,
        "damage":       40,
        "radius":       38,
        "score_value":  300,
        "color":        None,
        "attack_rate":  1.2,
    },
}

# ─── Waves ────────────────────────────────────────────────────────────────────
WAVE_COOLDOWN           = 5.0       # seconds between waves
WAVE_BASE_COUNT         = 6         # zombies in wave 1
WAVE_COUNT_SCALE        = 1.4       # multiplier per wave
WAVE_BOSS_EVERY         = 5         # boss spawns every N waves
WAVE_FAST_UNLOCK        = 2         # wave when fast zombies appear
WAVE_TANK_UNLOCK        = 4         # wave when tanks appear

SPAWN_EDGE_MARGIN       = 60        # px from world border to spawn inside
SPAWN_MIN_PLAYER_DIST   = 400       # don't spawn too close

# ─── Particles ────────────────────────────────────────────────────────────────
PARTICLE_BLOOD_COUNT    = 10
PARTICLE_MUZZLE_COUNT   = 6
PARTICLE_LIFETIME_MIN   = 0.15
PARTICLE_LIFETIME_MAX   = 0.55
PARTICLE_SPEED_MIN      = 60
PARTICLE_SPEED_MAX      = 220

# ─── Camera ───────────────────────────────────────────────────────────────────
CAMERA_LERP             = 6.0       # smoothing factor; higher = snappier
SCREEN_SHAKE_DECAY      = 8.0       # shake magnitude falloff rate

# ─── Audio ────────────────────────────────────────────────────────────────────
MUSIC_VOLUME            = 0.35
SFX_VOLUME              = 0.55

# ─── HUD ──────────────────────────────────────────────────────────────────────
HUD_MARGIN              = 16
HUD_BAR_W               = 220
HUD_BAR_H               = 14
HUD_FONT_LARGE          = 36
HUD_FONT_MED            = 22
HUD_FONT_SMALL          = 16

# ─── Physics / misc ───────────────────────────────────────────────────────────
ZOMBIE_SEPARATION_RADIUS = 36       # zombies push each other apart within this
ZOMBIE_SEPARATION_FORCE  = 90       # strength of separation push (px/s²)
