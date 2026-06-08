# DEADZONE — Top-Down Zombie Survival Shooter

> A polished, fully modular 2D zombie survival shooter built with Python + Pygame.  
> Built as an intermediate-level portfolio project showcasing clean game architecture.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Pygame](https://img.shields.io/badge/Pygame-2.5+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Screenshot

```
 ╔══════════════════════════════════════════════════════╗
 ║  SCORE  12,450        WAVE  3           FPS 60       ║
 ╠══════════════════════════════════════════════════════╣
 ║                                                      ║
 ║   ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·   ║
 ║                                                      ║
 ║          ◆ ━━━>    ●  ●  ●                          ║
 ║                                                      ║
 ╠══════════════════════════════════════════════════════╣
 ║  HP ████████░░   STAM ██████████   [PISTOL 10/12]  ║
 ╚══════════════════════════════════════════════════════╝
```

---

## Features

### Core Gameplay
- **WASD movement** with mouse aiming
- **3 weapons**: Pistol, Shotgun, SMG — each with unique stats, fire rate, spread
- **Ammo system** with manual reload (R key)
- **Sprint** (Shift) with stamina drain/regen
- **Dash** (Space) with cooldown + brief invincibility
- **Invincibility frames** after taking damage

### Enemy System
- **4 zombie types**: Normal, Fast, Tank, Boss
- Smooth chase AI with velocity smoothing
- Zombie separation prevents pile-up clumping
- Per-type attack rates, health pools, score values

### Wave System
- Escalating waves with configurable composition
- Boss every 5th wave (crown-adorned with 600 HP)
- Cooldown between waves with animated countdown
- Score accumulates continuously (time + kills)

### Visual Polish
- Smooth delta-time movement everywhere
- Screen shake on player damage
- Muzzle flash + bullet trails
- Blood splatter particles with gravity
- Zombie death burst particles
- Invincibility flicker effect
- Smooth camera follow with lerp
- Player dash trail effect
- Animated main menu with grid + scanlines
- Weapon slot HUD with ammo pips
- Circular reload indicator on cursor

### Architecture
- Full separation of concerns across 12 files
- Zero circular imports
- Central settings.py for all tuning
- Dead entity tombstone cleanup pattern
- Pre-rendered world surface for performance

---

## Installation

### Requirements
- Python 3.11+
- Pygame 2.5+

### Setup

```bash
# Clone the repo
git clone https://github.com/yourname/deadzone.git
cd deadzone

# Install dependency
pip install pygame

# Run
python main.py
```

---

## Controls

| Key / Input        | Action              |
|--------------------|---------------------|
| WASD / Arrow Keys  | Move                |
| Mouse              | Aim                 |
| Left Mouse Button  | Shoot               |
| Shift              | Sprint              |
| Space              | Dash                |
| R                  | Reload              |
| 1 / 2 / 3          | Switch weapon slot  |
| Scroll Wheel       | Cycle weapon        |
| ESC                | Pause               |

---

## Project Structure

```
deadzone/
│
├── main.py              ← Entry point + game loop
├── game.py              ← Game orchestrator + state machine
├── settings.py          ← All constants, tuning values, colors
│
├── entities/
│   ├── player.py        ← Player: movement, shooting, weapons, health
│   ├── zombie.py        ← Zombie: AI, types, health, drawing
│   └── bullet.py        ← Projectile entity
│
├── systems/
│   ├── camera.py        ← Smooth-follow camera + screen shake
│   ├── collision.py     ← Centralised collision detection/resolution
│   ├── particles.py     ← Blood, muzzle flash, death effects
│   └── waves.py         ← Wave spawning and difficulty scaling
│
├── ui/
│   ├── hud.py           ← In-game HUD (health, ammo, score, wave)
│   └── menus.py         ← Main menu, pause, game over screens
│
├── utils/
│   ├── helpers.py       ← Math utilities (vectors, collision, drawing)
│   └── constants.py     ← Enums (GameState, ZombieType)
│
└── assets/
    ├── sounds/          ← .wav SFX files (optional, game runs without)
    ├── music/           ← ambient.ogg (optional)
    └── sprites/         ← Reserved for future sprite sheets
```

---

## Architecture Deep-Dive

### Update Loop Order (per frame)
```
main.py:clock.tick()
  → game.update(dt, events)
      1. Parse events → intent booleans
      2. player.update() → returns new bullets
      3. zombie.update() for each zombie
      4. bullet.update() for each bullet
      5. collision.process() → mutates entities
      6. Dead entity cleanup + score accounting
      7. waves.update() → may spawn new zombies
      8. camera.update()
      9. particles.update()
     10. hud.update()
  → game.draw(fps)
      1. Blit pre-rendered world surface (fast)
      2. Draw bullets
      3. Draw zombies (frustum-culled)
      4. Draw player
      5. Draw particles
      6. Draw HUD / menus (screen-space)
```

### System Communication
```
game.py ←→ player       (reads position, passes input booleans)
game.py ←→ bullets      (appends player-created bullets, owns list)
game.py ←→ zombies      (owns list, passes to wave/collision)
game.py ←→ collision    (passes all entity refs, collision mutates)
game.py ←→ camera       (passes player position, reads for world→screen)
game.py ←→ particles    (calls spawn methods, passes cam to draw)
game.py ←→ waves        (passes zombie list ref for appending + counting)
game.py ←→ hud          (reads player/wave state, never mutates)
menus   →  game.py      (returns string action signals, never mutate state)
```

---

## Adding Audio

Drop WAV/OGG files into `assets/sounds/` and `assets/music/`. See `assets/README.md` for filenames. The game runs silently without them.

**Free resources:**
- SFX: [jsfxr](https://sfxr.me/) (browser, free)
- Music: [OpenGameArt.org](https://opengameart.org/)

---

## Packaging as Executable

### PyInstaller (recommended)

```bash
pip install pyinstaller

# Single-file EXE (Windows)
pyinstaller --onefile --windowed --name=deadzone main.py

# Include assets
pyinstaller --onefile --windowed --name=deadzone \
  --add-data "assets;assets" main.py

# Output: dist/deadzone.exe
```

### Nuitka (faster binary)

```bash
pip install nuitka
nuitka --standalone --onefile --windows-disable-console main.py
```

---

## Tuning & Balance

All balance values are in `settings.py`. Key knobs:

| Setting                   | Effect                          |
|---------------------------|---------------------------------|
| `WAVE_COUNT_SCALE`        | Zombie count growth per wave    |
| `WAVE_BOSS_EVERY`         | Boss wave frequency             |
| `ZOMBIE_TYPES[*].speed`   | Per-type movement speed         |
| `PLAYER_IFRAMES`          | Invincibility window (seconds)  |
| `PLAYER_DASH_COOLDOWN`    | Dash recharge time              |
| `WEAPONS[*].fire_rate`    | Shots per second (lower = faster)|
| `CAMERA_LERP`             | Camera smoothness               |
| `SCREEN_SHAKE_DECAY`      | Shake falloff rate              |

---

## Future Expansion Ideas

### Short-term
- [ ] Pickup items (health pack, ammo crate)
- [ ] XP system with level-up stat boosts
- [ ] Minimap (simple dot representation)
- [ ] Kill streak multiplier
- [ ] High score persistence (JSON save file)

### Medium-term
- [ ] Obstacle/wall system with pathfinding (A*)
- [ ] More zombie types (exploder, ranged spitter)
- [ ] Weapon drops from boss kills
- [ ] Animated sprite sheets (replace procedural drawing)
- [ ] Controller support

### Long-term
- [ ] Multiple arenas / map selection
- [ ] Roguelite meta-progression
- [ ] Local co-op (split screen)
- [ ] Steam integration via Pygame CE

---

## Performance Notes

Current approach supports ~200 zombies at 60 FPS on modest hardware.

**If you need more entities:**
1. Replace `list` with a simple spatial grid hash in `collision.py`
2. Batch particle draws into a single surface per frame
3. Use `pygame.sprite.Group` with dirty-rect rendering for static entities
4. Profile with `cProfile`: `python -m cProfile -s cumtime main.py`

---

## Refactoring for Larger Scale

| Current pattern        | At scale, replace with               |
|------------------------|--------------------------------------|
| Entity lists in game.py| EntityManager with type-keyed dicts  |
| Direct attribute access| Property-based interfaces            |
| String game states     | Already using IntEnum ✓              |
| O(n²) collision        | Grid spatial hash                    |
| pygame.font.SysFont    | Bundled TTF font via pygame.font.Font|
| Manual sound loading   | SoundManager with pooled channels    |

---

## License

MIT — use freely in your own projects, learning, or portfolio.
