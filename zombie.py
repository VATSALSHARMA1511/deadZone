"""
entities/zombie.py — Zombie entity with type system and simple chase AI.

AI DESIGN (intentionally simple):
  Direct-chase works well for top-down shooters and is O(1) per zombie.
  The separation system in collision.py prevents them clumping into a blob.
  "Interesting" zombie behavior comes from mixing types, not complex path-finding.

TYPE SYSTEM:
  ZombieType string key → ZOMBIE_TYPES dict in settings.
  Visual colors, radius, speed, health are all data-driven so adding a new
  type only requires a settings entry + a color constant.

ENTITY LIFECYCLE:
  spawn → alive=True → take_damage() → health<=0 → alive=False →
  on_death() called (score, particles, sounds) → removed from list by game.py.
"""

import math
import random
import pygame
import settings
from helpers import clamp, lerp


# Color map — parallel to ZOMBIE_TYPES
_ZOMBIE_COLOR_MAP = {
    "normal": settings.C_ZOMBIE,
    "fast":   settings.C_ZOMBIE_FAST,
    "tank":   settings.C_ZOMBIE_TANK,
    "boss":   (220, 30, 80),   # Crimson boss
}


class Zombie:
    def __init__(self, x: float, y: float, ztype: str = "normal") -> None:
        self.x     = x
        self.y     = y
        self.ztype = ztype

        cfg          = settings.ZOMBIE_TYPES[ztype]
        self.speed   = cfg["speed"]
        self.health  = cfg["health"]
        self.max_health = cfg["health"]
        self.damage  = cfg["damage"]
        self.radius  = cfg["radius"]
        self.score_value = cfg["score_value"]
        self._attack_rate = cfg["attack_rate"]
        self._attack_timer = 0.0

        self.base_color = _ZOMBIE_COLOR_MAP.get(ztype, settings.C_ZOMBIE)
        self.color      = self.base_color

        self.alive      = True
        self._hit_flash = 0.0
        self._wobble_t  = random.uniform(0, math.tau)  # phase offset for animation
        self._vel_x     = 0.0
        self._vel_y     = 0.0

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float, player) -> None:
        if not self.alive:
            return

        self._wobble_t    += dt * 6.0
        self._hit_flash    = max(0.0, self._hit_flash - dt)
        self._attack_timer = max(0.0, self._attack_timer - dt)

        # Chase AI — move toward player
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)

        if dist > 0:
            nx, ny = dx / dist, dy / dist
            target_vx = nx * self.speed
            target_vy = ny * self.speed
            # Smooth velocity (avoids instant direction snap)
            accel = 8.0
            self._vel_x = lerp(self._vel_x, target_vx, clamp(accel * dt, 0, 1))
            self._vel_y = lerp(self._vel_y, target_vy, clamp(accel * dt, 0, 1))

            # Only move if not overlapping player (collision handles resolution)
            if dist > player.radius + self.radius:
                self.x += self._vel_x * dt
                self.y += self._vel_y * dt

        # Update color with hit flash
        self.color = self._compute_color()

    def _compute_color(self) -> tuple:
        if self._hit_flash > 0:
            ratio = self._hit_flash / 0.2
            r = int(lerp(self.base_color[0], settings.C_ZOMBIE_HIT[0], ratio))
            g = int(lerp(self.base_color[1], settings.C_ZOMBIE_HIT[1], ratio))
            b = int(lerp(self.base_color[2], settings.C_ZOMBIE_HIT[2], ratio))
            return (clamp(r, 0, 255), clamp(g, 0, 255), clamp(b, 0, 255))
        return self.base_color

    # ── Combat ────────────────────────────────────────────────────────────────

    def take_damage(self, amount: int) -> None:
        self.health     -= amount
        self._hit_flash  = 0.2
        if self.health <= 0:
            self.health = 0
            self.alive  = False

    def can_attack(self) -> bool:
        return self._attack_timer <= 0

    def get_damage(self) -> int:
        if self._attack_timer <= 0:
            self._attack_timer = self._attack_rate
            return self.damage
        return 0

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, cam) -> None:
        if not self.alive:
            return
        sx, sy = cam.world_to_screen(self.x, self.y)
        r      = self.radius

        # Frustum cull
        if not (-r < sx < surface.get_width() + r and
                -r < sy < surface.get_height() + r):
            return

        # Wobble (slight scale pulse)
        wobble   = math.sin(self._wobble_t) * 1.5
        draw_r   = max(4, int(r + wobble))

        # Shadow
        pygame.draw.ellipse(surface, (0, 0, 0),
                            (sx - draw_r + 3, sy + draw_r - 4,
                             draw_r * 2 - 3, draw_r // 2))

        # Body
        pygame.draw.circle(surface, self.color, (sx, sy), draw_r)

        # Outline (thicker for boss/tank)
        outline_w = 3 if self.ztype in ("boss", "tank") else 1
        outline_c = (20, 20, 20) if self.ztype == "boss" else (0, 0, 0)
        pygame.draw.circle(surface, outline_c, (sx, sy), draw_r, outline_w)

        # Boss crown spikes
        if self.ztype == "boss":
            self._draw_boss_crown(surface, sx, sy, draw_r)

        # X eyes
        eye_r  = max(2, draw_r // 5)
        offset = draw_r // 3
        for ex_off in (-offset, offset):
            ex = sx + ex_off
            ey = sy - offset // 2
            pygame.draw.line(surface, (20, 20, 20),
                             (ex - eye_r, ey - eye_r), (ex + eye_r, ey + eye_r), 2)
            pygame.draw.line(surface, (20, 20, 20),
                             (ex + eye_r, ey - eye_r), (ex - eye_r, ey + eye_r), 2)

        # Health bar (only when damaged)
        if self.health < self.max_health:
            bar_w = draw_r * 2
            bar_h = 4
            bx    = sx - draw_r
            by    = sy - draw_r - 8
            pygame.draw.rect(surface, settings.C_HEALTH_BAR_BG,
                             (bx, by, bar_w, bar_h))
            fill_w = int(bar_w * self.health / self.max_health)
            pygame.draw.rect(surface, settings.C_HEALTH_GOOD,
                             (bx, by, fill_w, bar_h))

    def _draw_boss_crown(self, surface: pygame.Surface,
                          sx: int, sy: int, r: int) -> None:
        """Triangular crown spikes around boss zombie."""
        n      = 6
        outer  = r + 10
        inner  = r + 2
        for i in range(n):
            angle = math.tau / n * i - math.pi / 2
            tip_x = int(sx + math.cos(angle) * outer)
            tip_y = int(sy + math.sin(angle) * outer)
            la    = angle - 0.25
            ra    = angle + 0.25
            lx    = int(sx + math.cos(la) * inner)
            ly    = int(sy + math.sin(la) * inner)
            rx    = int(sx + math.cos(ra) * inner)
            ry    = int(sy + math.sin(ra) * inner)
            pygame.draw.polygon(surface, settings.C_ACCENT_GOLD,
                                [(tip_x, tip_y), (lx, ly), (rx, ry)])
