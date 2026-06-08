"""
entities/bullet.py — Projectile entity.

ENTITY LIFECYCLE:
  Created by Player.shoot() → added to game.bullets list →
  updated each frame → marked alive=False on collision or timeout →
  purged from list by game.py (dead entity cleanup).

DESIGN NOTE:
  Bullets are kept deliberately lightweight — just position, velocity,
  lifetime, and damage. No Pygame Sprite inheritance: circle-based
  entities drawn procedurally are faster and simpler than sprite sheets
  for this style.
"""

import math
import pygame
import settings
from helpers import clamp


class Bullet:
    __slots__ = ("x", "y", "vx", "vy", "damage", "lifetime", "alive",
                 "_age", "_muzzle_flash_t")

    def __init__(self, x: float, y: float,
                 angle_deg: float, speed: float, damage: int) -> None:
        self.x      = x
        self.y      = y
        rad         = math.radians(angle_deg)
        self.vx     = math.cos(rad) * speed
        self.vy     = math.sin(rad) * speed
        self.damage = damage
        self.lifetime = settings.BULLET_LIFETIME
        self.alive  = True
        self._age   = 0.0
        self._muzzle_flash_t = 0.06  # brief bright tail near spawn

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        self._age     += dt
        self._muzzle_flash_t = max(0.0, self._muzzle_flash_t - dt)
        if self.lifetime <= 0:
            self.alive = False

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, cam) -> None:
        if not self.alive:
            return
        sx, sy = cam.world_to_screen(self.x, self.y)
        if not (0 <= sx <= surface.get_width() and 0 <= sy <= surface.get_height()):
            return

        # Trail — draw a short line behind the bullet
        speed  = math.hypot(self.vx, self.vy)
        trail  = 14.0
        if speed > 0:
            tx = sx - int(self.vx / speed * trail)
            ty = sy - int(self.vy / speed * trail)
            pygame.draw.line(surface, settings.C_BULLET_GLOW,
                             (tx, ty), (sx, sy), 2)

        # Core
        pygame.draw.circle(surface, settings.C_BULLET,
                           (sx, sy), settings.BULLET_RADIUS)

        # Muzzle-flash brightness near spawn
        if self._muzzle_flash_t > 0:
            glow_r = settings.BULLET_RADIUS + 4
            glow_a = int(180 * self._muzzle_flash_t / 0.06)
            glow_surf = pygame.Surface((glow_r * 2 + 2, glow_r * 2 + 2),
                                       pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*settings.C_MUZZLE, glow_a),
                               (glow_r + 1, glow_r + 1), glow_r)
            surface.blit(glow_surf, (sx - glow_r - 1, sy - glow_r - 1),
                         special_flags=pygame.BLEND_ADD)
