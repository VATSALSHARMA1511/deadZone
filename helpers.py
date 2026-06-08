"""
utils/helpers.py — Shared math and drawing utilities.

WHY THIS EXISTS:
  Keeps entity/system code free of repetitive math. Functions here are pure
  (no side effects, no Pygame imports beyond drawing calls) so they're trivially
  testable and reusable across every module.

BEGINNER MISTAKE TO AVOID:
  Don't scatter math helpers inside entity classes — they become impossible to
  reuse and you end up copy-pasting the same normalise_vector everywhere.
"""

import math
import random
import pygame
from typing import Tuple

Vec2 = Tuple[float, float]


# ─── Vector math ──────────────────────────────────────────────────────────────

def vec_length(v: Vec2) -> float:
    return math.hypot(v[0], v[1])


def vec_normalise(v: Vec2) -> Vec2:
    """Return unit vector; returns (0,0) for zero-length input."""
    length = vec_length(v)
    if length == 0:
        return (0.0, 0.0)
    return (v[0] / length, v[1] / length)


def vec_scale(v: Vec2, s: float) -> Vec2:
    return (v[0] * s, v[1] * s)


def vec_add(a: Vec2, b: Vec2) -> Vec2:
    return (a[0] + b[0], a[1] + b[1])


def vec_sub(a: Vec2, b: Vec2) -> Vec2:
    return (a[0] - b[0], a[1] - b[1])


def vec_dot(a: Vec2, b: Vec2) -> float:
    return a[0] * b[0] + a[1] * b[1]


def vec_lerp(a: Vec2, b: Vec2, t: float) -> Vec2:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (a[1] - b[1]) * -t
            ) if False else (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def distance(a: Vec2, b: Vec2) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def angle_to(origin: Vec2, target: Vec2) -> float:
    """Return angle in degrees from origin pointing toward target."""
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    return math.degrees(math.atan2(dy, dx))


def rotate_vec(v: Vec2, degrees: float) -> Vec2:
    """Rotate a 2-D vector by `degrees` clockwise."""
    rad = math.radians(degrees)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    return (v[0] * cos_a - v[1] * sin_a,
            v[0] * sin_a + v[1] * cos_a)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def random_unit_vec() -> Vec2:
    """Random direction as unit vector."""
    angle = random.uniform(0, math.tau)
    return (math.cos(angle), math.sin(angle))


# ─── Circles collision ─────────────────────────────────────────────────────────

def circles_overlap(ax: float, ay: float, ar: float,
                    bx: float, by: float, br: float) -> bool:
    """True if two circles (x,y,radius) overlap."""
    dx = bx - ax
    dy = by - ay
    return dx * dx + dy * dy < (ar + br) ** 2


def push_apart(ax: float, ay: float, ar: float,
               bx: float, by: float, br: float,
               strength: float = 1.0) -> Tuple[Vec2, Vec2]:
    """
    Return displacement vectors to push two overlapping circles apart.
    Returns (delta_a, delta_b) — add delta_a to entity A's position, etc.
    """
    dx, dy = bx - ax, by - ay
    dist = math.hypot(dx, dy)
    if dist == 0:
        # Exactly on top of each other — nudge randomly
        dx, dy = random.uniform(-1, 1), random.uniform(-1, 1)
        dist = math.hypot(dx, dy)
    overlap = (ar + br) - dist
    if overlap <= 0:
        return (0.0, 0.0), (0.0, 0.0)
    nx, ny = dx / dist, dy / dist
    push = overlap * 0.5 * strength
    return (-nx * push, -ny * push), (nx * push, ny * push)


# ─── Rendering helpers ────────────────────────────────────────────────────────

def draw_circle_aa(surface: pygame.Surface, color: tuple,
                   pos: Vec2, radius: int, width: int = 0) -> None:
    """Pygame's built-in circle aliasing is rough; this wraps gfxdraw for
    anti-aliased filled circles when available, falling back gracefully."""
    try:
        import pygame.gfxdraw
        ix, iy = int(pos[0]), int(pos[1])
        if width == 0:
            pygame.gfxdraw.aacircle(surface, ix, iy, radius, color)
            pygame.gfxdraw.filled_circle(surface, ix, iy, radius, color)
        else:
            pygame.gfxdraw.aacircle(surface, ix, iy, radius, color)
    except Exception:
        pygame.draw.circle(surface, color, (int(pos[0]), int(pos[1])), radius, width)


def draw_bar(surface: pygame.Surface,
             x: int, y: int, w: int, h: int,
             value: float, max_value: float,
             color_full: tuple, color_bg: tuple,
             border_color: tuple = (0, 0, 0),
             border: int = 1) -> None:
    """Generic horizontal fill bar — used for health, stamina, ammo, etc."""
    ratio = clamp(value / max_value, 0.0, 1.0)
    pygame.draw.rect(surface, color_bg, (x, y, w, h))
    pygame.draw.rect(surface, color_full, (x, y, int(w * ratio), h))
    if border:
        pygame.draw.rect(surface, border_color, (x, y, w, h), border)


def alpha_surface(w: int, h: int) -> pygame.Surface:
    """Create a transparent surface with per-pixel alpha."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    return s


def tint_color(color: tuple, amount: float) -> tuple:
    """Blend color toward white by `amount` (0–1)."""
    r = int(color[0] + (255 - color[0]) * amount)
    g = int(color[1] + (255 - color[1]) * amount)
    b = int(color[2] + (255 - color[2]) * amount)
    return (clamp(r, 0, 255), clamp(g, 0, 255), clamp(b, 0, 255))


def world_to_screen(wx: float, wy: float, cam_x: float, cam_y: float) -> Tuple[int, int]:
    """Convert world position to screen pixel coordinates."""
    return (int(wx - cam_x), int(wy - cam_y))


def screen_to_world(sx: float, sy: float, cam_x: float, cam_y: float) -> Vec2:
    return (sx + cam_x, sy + cam_y)
