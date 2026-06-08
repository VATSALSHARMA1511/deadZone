"""
systems/particles.py — Lightweight particle effect system.

WHY THIS EXISTS:
  Visual juice lives entirely in particles. Without it the game feels sterile.
  Keeping particles in their own system means entity code just calls
  `particles.spawn_blood(x, y)` and moves on — zero rendering coupling.

ARCHITECTURE:
  ParticleSystem owns a flat list of Particle objects. We pool them loosely by
  just removing dead ones each frame rather than a true object-pool (profiling
  shows Python list removal is fine for <300 particles).

PERFORMANCE:
  Particles are drawn as small pygame.draw.circle calls — no surface blitting,
  no alpha per particle (except muzzle flash which uses a tiny alpha surface).
  Keep PARTICLE_BLOOD_COUNT ≤ 14 to stay comfortably under 300 total.
"""

import random
import math
import pygame
import settings
from helpers import vec_normalise, random_unit_vec, clamp, lerp


class Particle:
    """Single particle; fully value-type to allow easy batching later."""
    __slots__ = ("x", "y", "vx", "vy", "lifetime", "max_lifetime",
                 "radius", "color", "fade", "gravity")

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 lifetime: float, radius: int, color: tuple,
                 fade: bool = True, gravity: float = 0.0) -> None:
        self.x, self.y       = x, y
        self.vx, self.vy     = vx, vy
        self.lifetime        = lifetime
        self.max_lifetime    = lifetime
        self.radius          = radius
        self.color           = color
        self.fade            = fade
        self.gravity         = gravity

    @property
    def alive(self) -> bool:
        return self.lifetime > 0

    @property
    def alpha_ratio(self) -> float:
        """0 → dead, 1 → just spawned."""
        return clamp(self.lifetime / self.max_lifetime, 0.0, 1.0)

    def update(self, dt: float) -> None:
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        self.vy += self.gravity * dt
        self.lifetime -= dt
        # Friction
        self.vx *= (1.0 - 4.0 * dt)
        self.vy *= (1.0 - 4.0 * dt)


class ParticleSystem:
    def __init__(self) -> None:
        self._particles: list[Particle] = []

    # ── Spawn helpers ─────────────────────────────────────────────────────────

    def spawn_blood(self, x: float, y: float,
                    direction: tuple = (0.0, 0.0),
                    count: int | None = None) -> None:
        """Directional blood splatter on zombie hit."""
        n = count or settings.PARTICLE_BLOOD_COUNT
        dx, dy = direction
        has_dir = (dx != 0 or dy != 0)
        for _ in range(n):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(settings.PARTICLE_SPEED_MIN,
                                   settings.PARTICLE_SPEED_MAX)
            if has_dir:
                # Bias toward incoming direction
                bias = random.uniform(0.5, 1.0)
                vx = (math.cos(angle) * (1 - bias) + dx * bias) * speed
                vy = (math.sin(angle) * (1 - bias) + dy * bias) * speed
            else:
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
            lt = random.uniform(settings.PARTICLE_LIFETIME_MIN,
                                settings.PARTICLE_LIFETIME_MAX)
            r  = random.randint(2, 5)
            # Blood is dark red to bright red
            shade = random.randint(160, 255)
            color = (shade, random.randint(0, 40), random.randint(0, 20))
            self._particles.append(
                Particle(x, y, vx, vy, lt, r, color, fade=True, gravity=180)
            )

    def spawn_muzzle_flash(self, x: float, y: float,
                           angle_deg: float) -> None:
        """Short burst of bright particles from gun barrel."""
        n = settings.PARTICLE_MUZZLE_COUNT
        angle_rad = math.radians(angle_deg)
        for i in range(n):
            spread = random.uniform(-25, 25)
            a      = angle_rad + math.radians(spread)
            speed  = random.uniform(120, 260)
            vx     = math.cos(a) * speed
            vy     = math.sin(a) * speed
            lt     = random.uniform(0.04, 0.12)
            r      = random.randint(2, 5)
            # Yellow-white
            bright = random.randint(200, 255)
            color  = (bright, random.randint(170, 255), random.randint(30, 100))
            self._particles.append(
                Particle(x, y, vx, vy, lt, r, color, fade=True)
            )

    def spawn_zombie_death(self, x: float, y: float,
                           color: tuple) -> None:
        """Large burst of colored particles on zombie death."""
        for _ in range(20):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(80, 300)
            vx    = math.cos(angle) * speed
            vy    = math.sin(angle) * speed
            lt    = random.uniform(0.3, 0.8)
            r     = random.randint(3, 8)
            shade = random.randint(0, 40)
            c     = (clamp(color[0] + shade, 0, 255),
                     clamp(color[1] + shade, 0, 255),
                     clamp(color[2] + shade, 0, 255))
            self._particles.append(
                Particle(x, y, vx, vy, lt, r, c, fade=True, gravity=120)
            )

    def spawn_player_damage(self, x: float, y: float) -> None:
        """White sparks when player takes damage."""
        for _ in range(8):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(100, 240)
            vx    = math.cos(angle) * speed
            vy    = math.sin(angle) * speed
            lt    = random.uniform(0.1, 0.3)
            self._particles.append(
                Particle(x, y, vx, vy, lt, 3, (255, 255, 255), fade=True)
            )

    # ── Update / Draw ─────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        for p in self._particles:
            p.update(dt)
        # Remove dead particles
        self._particles = [p for p in self._particles if p.alive]

    def draw(self, surface: pygame.Surface, cam) -> None:
        """Draw all particles transformed by camera."""
        for p in self._particles:
            sx, sy = cam.world_to_screen(p.x, p.y)
            if not (-20 < sx < surface.get_width() + 20 and
                    -20 < sy < surface.get_height() + 20):
                continue
            if p.fade:
                ratio = p.alpha_ratio
                r = int(p.color[0] * ratio)
                g = int(p.color[1] * ratio)
                b = int(p.color[2] * ratio)
                draw_color = (r, g, b)
            else:
                draw_color = p.color
            radius = max(1, int(p.radius * (0.5 + 0.5 * p.alpha_ratio)))
            pygame.draw.circle(surface, draw_color, (sx, sy), radius)

    @property
    def count(self) -> int:
        return len(self._particles)
