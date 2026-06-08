"""
entities/player.py — Player entity.

SYSTEMS THIS ENTITY OWNS:
  • WASD movement + sprint (stamina-gated)
  • Dash mechanic (cooldown-gated, brief invincibility)
  • Mouse-aimed shooting (fire rate, spread, multi-pellet)
  • Weapon switching (slots 1/2/3 or scroll wheel)
  • Health + invincibility frames
  • Ammo + reload

COMMUNICATION:
  • Player.shoot() creates Bullet objects returned to game.py to add to bullets list
  • Player.take_damage() returns True when damage was actually applied (for camera shake)
  • game.py reads player.x/.y for camera targeting

DELTA TIME USAGE:
  All movement/timers multiplied by dt. NEVER frame-count-based timers.

BEGINNER MISTAKE TO AVOID:
  Don't handle input in the entity — handle it in game.py and pass booleans.
  This keeps Player testable without a display.
"""

import math
import random
import pygame
import settings

from helpers import clamp, vec_normalise
from constants import WEAPON_ORDER
from bullet import Bullet


class Player:
    def __init__(self, x: float, y: float) -> None:
        self.x      = x
        self.y      = y
        self.radius = settings.PLAYER_RADIUS

        # Health
        self.health     = settings.PLAYER_HEALTH_MAX
        self.max_health = settings.PLAYER_HEALTH_MAX
        self.alive      = True
        self._iframe_t  = 0.0       # invincibility timer

        # Stamina
        self.stamina     = settings.PLAYER_STAMINA_MAX
        self.max_stamina = settings.PLAYER_STAMINA_MAX
        self._sprinting  = False

        # Dash
        self._dash_t     = 0.0      # remaining dash duration
        self._dash_cd    = 0.0      # cooldown timer
        self._dash_vx    = 0.0
        self._dash_vy    = 0.0

        # Weapon system
        self._weapon_slot   = 0
        self._weapons       = {name: _WeaponState(name)
                               for name in WEAPON_ORDER}
        self._shoot_timer   = 0.0   # fire rate gating
        self._reloading     = False
        self._reload_timer  = 0.0

        # Facing angle (degrees) — updated toward mouse each frame
        self.facing = 0.0

        # Visual
        self._hit_flash_t = 0.0
        self._bob_t       = 0.0

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def current_weapon_name(self) -> str:
        return WEAPON_ORDER[self._weapon_slot]

    @property
    def current_weapon(self) -> dict:
        return settings.WEAPONS[self.current_weapon_name]

    @property
    def ammo(self) -> int:
        return self._weapons[self.current_weapon_name].ammo

    @property
    def ammo_max(self) -> int:
        return self.current_weapon["ammo_max"]

    @property
    def is_reloading(self) -> bool:
        return self._reloading

    @property
    def reload_progress(self) -> float:
        """0 → 1 reload progress."""
        rt = self.current_weapon["reload_time"]
        return clamp(1.0 - self._reload_timer / rt, 0.0, 1.0) if self._reloading else 1.0

    @property
    def dash_cooldown_ratio(self) -> float:
        return clamp(1.0 - self._dash_cd / settings.PLAYER_DASH_COOLDOWN, 0.0, 1.0)

    @property
    def is_dashing(self) -> bool:
        return self._dash_t > 0

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float, keys, mouse_world: tuple,
               fire_pressed: bool, reload_pressed: bool,
               dash_pressed: bool, sprint_held: bool) -> list[Bullet]:
        if not self.alive:
            return []

        self._bob_t += dt

        # Timers
        self._iframe_t    = max(0.0, self._iframe_t - dt)
        self._hit_flash_t = max(0.0, self._hit_flash_t - dt)
        self._shoot_timer = max(0.0, self._shoot_timer - dt)
        self._dash_cd     = max(0.0, self._dash_cd - dt)

        # Facing toward mouse
        dx = mouse_world[0] - self.x
        dy = mouse_world[1] - self.y
        self.facing = math.degrees(math.atan2(dy, dx))

        # Movement
        self._move(dt, keys, sprint_held)

        # Dash
        if dash_pressed and self._dash_cd <= 0 and not self.is_dashing:
            self._start_dash(keys)
        if self.is_dashing:
            self._update_dash(dt)

        # Reload
        self._update_reload(dt, reload_pressed)

        # Shoot
        bullets = []
        if fire_pressed and not self._reloading:
            bullets = self._try_shoot()

        return bullets

    # ── Movement ─────────────────────────────────────────────────────────────

    def _move(self, dt: float, keys, sprint_held: bool) -> None:
        if self.is_dashing:
            return  # Dash controls movement

        move_x, move_y = 0.0, 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    move_y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  move_y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  move_x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: move_x += 1

        if move_x != 0 or move_y != 0:
            nx, ny = vec_normalise((move_x, move_y))
            # Sprint gating
            if sprint_held and self.stamina > 0:
                speed = settings.PLAYER_SPRINT_SPEED
                self.stamina -= settings.PLAYER_SPRINT_COST * dt
                self.stamina  = max(0.0, self.stamina)
                self._sprinting = True
            else:
                speed = settings.PLAYER_SPEED
                self._sprinting = False
            self.x += nx * speed * dt
            self.y += ny * speed * dt
        else:
            self._sprinting = False

        # Stamina regen
        if not self._sprinting:
            self.stamina = min(self.max_stamina,
                               self.stamina + settings.PLAYER_STAMINA_REGEN * dt)

    def _start_dash(self, keys) -> None:
        dx, dy = 0.0, 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if dx == 0 and dy == 0:
            # Dash in facing direction if no keys held
            rad = math.radians(self.facing)
            dx, dy = math.cos(rad), math.sin(rad)
        nx, ny = vec_normalise((dx, dy))
        self._dash_vx   = nx * settings.PLAYER_DASH_SPEED
        self._dash_vy   = ny * settings.PLAYER_DASH_SPEED
        self._dash_t    = settings.PLAYER_DASH_DUR
        self._dash_cd   = settings.PLAYER_DASH_COOLDOWN
        self._iframe_t  = max(self._iframe_t, settings.PLAYER_DASH_DUR)

    def _update_dash(self, dt: float) -> None:
        step = min(dt, self._dash_t)
        self.x     += self._dash_vx * step
        self.y     += self._dash_vy * step
        self._dash_t -= dt

    # ── Shooting ─────────────────────────────────────────────────────────────

    def _try_shoot(self) -> list[Bullet]:
        if self._shoot_timer > 0:
            return []
        ws   = self._weapons[self.current_weapon_name]
        wdef = self.current_weapon
        if ws.ammo <= 0:
            self._start_reload()
            return []

        ws.ammo -= 1
        self._shoot_timer = wdef["fire_rate"]

        bullets = []
        n = wdef["bullets_per_shot"]
        for _ in range(n):
            spread = random.uniform(-wdef["spread"], wdef["spread"])
            angle  = self.facing + spread
            b      = Bullet(self.x, self.y,
                            angle, wdef["bullet_speed"], wdef["damage"])
            bullets.append(b)
        return bullets

    # ── Reload ───────────────────────────────────────────────────────────────

    def _start_reload(self) -> None:
        ws = self._weapons[self.current_weapon_name]
        if ws.ammo < self.ammo_max and not self._reloading:
            self._reloading     = True
            self._reload_timer  = self.current_weapon["reload_time"]

    def _update_reload(self, dt: float, reload_pressed: bool) -> None:
        if reload_pressed and not self._reloading:
            self._start_reload()
        if self._reloading:
            self._reload_timer -= dt
            if self._reload_timer <= 0:
                ws      = self._weapons[self.current_weapon_name]
                ws.ammo = self.ammo_max
                self._reloading = False

    # ── Weapon switching ─────────────────────────────────────────────────────

    def switch_weapon(self, slot: int) -> None:
        slot = clamp(slot, 0, len(WEAPON_ORDER) - 1)
        if slot != self._weapon_slot:
            self._weapon_slot  = slot
            self._reloading    = False
            self._shoot_timer  = 0.0

    def scroll_weapon(self, direction: int) -> None:
        """direction = +1 or -1 from mouse wheel."""
        new_slot = (self._weapon_slot + direction) % len(WEAPON_ORDER)
        self.switch_weapon(new_slot)

    # ── Health ────────────────────────────────────────────────────────────────

    def take_damage(self, amount: int) -> bool:
        """Apply damage respecting iframes. Returns True if damage landed."""
        if self._iframe_t > 0 or self.is_dashing:
            return False
        self.health    -= amount
        self._iframe_t  = settings.PLAYER_IFRAMES
        self._hit_flash_t = 0.3
        if self.health <= 0:
            self.health = 0
            self.alive  = False
        return True

    def heal(self, amount: int) -> None:
        self.health = min(self.max_health, self.health + amount)

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, cam) -> None:
        sx, sy = cam.world_to_screen(self.x, self.y)
        r      = self.radius

        # Invincibility flash (alternate every 0.06 s)
        if self._iframe_t > 0:
            cycle = int(self._iframe_t / 0.06) % 2
            if cycle == 1:
                return  # Skip draw = flicker effect

        # Body bob
        bob = math.sin(self._bob_t * 8) * 1.5 if self._sprinting else 0

        # Hit flash
        if self._hit_flash_t > 0:
            body_color = settings.C_ACCENT_RED
        else:
            body_color = settings.C_PLAYER

        # Shadow
        pygame.draw.ellipse(surface, (0, 0, 0, 80),
                            (sx - r + 4, sy - r//2 + 4 + int(bob),
                             r * 2 - 4, r - 2))

        # Dash trail
        if self.is_dashing:
            for i in range(3):
                alpha = 80 - i * 25
                tr    = r - i * 3
                trail_x = int(sx - self._dash_vx * 0.015 * (i + 1))
                trail_y = int(sy - self._dash_vy * 0.015 * (i + 1) + bob)
                trail_surf = pygame.Surface((tr * 2 + 2, tr * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(trail_surf, (*settings.C_PLAYER_ACCENT, alpha),
                                   (tr + 1, tr + 1), tr)
                surface.blit(trail_surf, (trail_x - tr - 1, trail_y - tr - 1))

        # Body circle
        pygame.draw.circle(surface, body_color,
                           (sx, sy + int(bob)), r)
        # Inner ring
        pygame.draw.circle(surface, settings.C_PLAYER_ACCENT,
                           (sx, sy + int(bob)), r - 4, 2)

        # Gun barrel line
        rad      = math.radians(self.facing)
        barrel_l = r + 10
        ex       = int(sx + math.cos(rad) * barrel_l)
        ey       = int(sy + math.sin(rad) * barrel_l + bob)
        pygame.draw.line(surface, settings.C_ACCENT_GOLD,
                         (sx, sy + int(bob)), (ex, ey), 3)

        # Eye dot
        eye_x = int(sx + math.cos(rad) * (r - 4))
        eye_y = int(sy + math.sin(rad) * (r - 4) + bob)
        pygame.draw.circle(surface, settings.C_BLACK, (eye_x, eye_y), 3)


# ── Helper ────────────────────────────────────────────────────────────────────

class _WeaponState:
    """Per-weapon mutable state (ammo count)."""
    __slots__ = ("name", "ammo")

    def __init__(self, name: str) -> None:
        self.name = name
        self.ammo = settings.WEAPONS[name]["ammo_max"]
