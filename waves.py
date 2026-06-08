"""
systems/waves.py — Wave-based zombie spawning and difficulty scaling.

WHY THIS EXISTS:
  Separating wave logic from game.py keeps the game loop clean and lets us
  evolve the difficulty curve independently of rendering or input code.

WAVE LIFECYCLE:
  1. COOLDOWN phase — timer counts down, shows "Wave N incoming" UI
  2. SPAWNING phase — zombies are released over ~1 s (not all at once)
  3. ACTIVE phase   — wave is "live"; transition to next when all dead
  4. Next wave      — cooldown restarts

DESIGN DECISIONS:
  • Staggered spawn (not instant dump) prevents stutters from 20 simultaneous
    entity creations and feels more dramatic.
  • Wave composition is computed here, not hardcoded per wave, so it scales
    infinitely without manual tuning.
"""

import random
import math
import settings
from constants import ZombieType, ZOMBIE_TYPE_KEYS
from zombie import Zombie


class WaveManager:
    def __init__(self, world_w: int, world_h: int) -> None:
        self.world_w = world_w
        self.world_h = world_h

        self.wave_number  = 0
        self.state        = "cooldown"   # "cooldown" | "spawning" | "active"
        self._cooldown_t  = 3.0          # shorter first cooldown
        self._spawn_queue : list[str]    = []  # zombie type strings to spawn
        self._spawn_timer  = 0.0
        self._spawn_interval = 0.18      # seconds between each spawn burst

        # Public flags read by HUD
        self.cooldown_remaining = self._cooldown_t

    # ── Main update ───────────────────────────────────────────────────────────

    def update(self, dt: float, zombies: list, player) -> None:
        if self.state == "cooldown":
            self._cooldown_t -= dt
            self.cooldown_remaining = max(0.0, self._cooldown_t)
            if self._cooldown_t <= 0:
                self._start_wave()

        elif self.state == "spawning":
            self._spawn_timer -= dt
            if self._spawn_timer <= 0 and self._spawn_queue:
                # Spawn a small cluster each tick
                burst = min(2, len(self._spawn_queue))
                for _ in range(burst):
                    ztype = self._spawn_queue.pop(0)
                    z = self._create_zombie(ztype, player)
                    zombies.append(z)
                self._spawn_timer = self._spawn_interval
            if not self._spawn_queue:
                self.state = "active"

        elif self.state == "active":
            # Wave ends when all zombies are dead
            alive = sum(1 for z in zombies if z.alive)
            if alive == 0:
                self._end_wave()

    # ── Wave logic ────────────────────────────────────────────────────────────

    def _start_wave(self) -> None:
        self.wave_number += 1
        self.state = "spawning"
        self._spawn_queue = self._build_wave_composition()
        self._spawn_timer = 0.0

    def _end_wave(self) -> None:
        self.state = "cooldown"
        self._cooldown_t = settings.WAVE_COOLDOWN
        self.cooldown_remaining = self._cooldown_t

    def _build_wave_composition(self) -> list[str]:
        """
        Determine which zombie types and how many spawn this wave.
        Formula keeps it interesting without manual scripting.
        """
        wn   = self.wave_number
        base = settings.WAVE_BASE_COUNT
        total = int(base * (settings.WAVE_COUNT_SCALE ** (wn - 1)))
        total = min(total, 60)   # hard cap for performance

        pool = ["normal"] * 10   # weight pool

        if wn >= settings.WAVE_FAST_UNLOCK:
            pool += ["fast"] * 5
        if wn >= settings.WAVE_TANK_UNLOCK:
            pool += ["tank"] * 3

        composition = [random.choice(pool) for _ in range(total)]

        # Boss wave
        if wn % settings.WAVE_BOSS_EVERY == 0:
            composition.append("boss")

        random.shuffle(composition)
        return composition

    def _create_zombie(self, ztype: str, player) -> "Zombie":
        x, y = self._random_spawn(player.x, player.y)
        return Zombie(x, y, ztype)

    def _random_spawn(self, px: float, py: float) -> tuple[float, float]:
        """
        Spawn at a random edge position at least SPAWN_MIN_PLAYER_DIST away.
        Tries up to 20 times before giving up (edge case: player near border).
        """
        margin = settings.SPAWN_EDGE_MARGIN
        min_d  = settings.SPAWN_MIN_PLAYER_DIST

        for _ in range(20):
            edge = random.randint(0, 3)
            if edge == 0:    # top
                x = random.uniform(margin, self.world_w - margin)
                y = random.uniform(margin, margin * 3)
            elif edge == 1:  # bottom
                x = random.uniform(margin, self.world_w - margin)
                y = random.uniform(self.world_h - margin * 3, self.world_h - margin)
            elif edge == 2:  # left
                x = random.uniform(margin, margin * 3)
                y = random.uniform(margin, self.world_h - margin)
            else:            # right
                x = random.uniform(self.world_w - margin * 3, self.world_w - margin)
                y = random.uniform(margin, self.world_h - margin)

            if math.hypot(x - px, y - py) >= min_d:
                return (x, y)

        # Fallback: any edge point
        return (random.uniform(margin, self.world_w - margin), margin)

    # ── Properties for HUD ───────────────────────────────────────────────────

    @property
    def in_cooldown(self) -> bool:
        return self.state == "cooldown"

    @property
    def is_boss_wave(self) -> bool:
        return self.wave_number % settings.WAVE_BOSS_EVERY == 0 and self.wave_number > 0
