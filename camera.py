"""
systems/camera.py — Smooth-follow camera with screen-shake.

WHY THIS EXISTS:
  Without a camera, the world either has to fit on screen (boring) or you hard-
  code offsets everywhere (nightmare to maintain). The camera is a single
  authoritative coordinate transform: world → screen.

HOW IT WORKS:
  • camera.x / camera.y are the top-left world coordinates currently visible.
  • update() lerps toward the target (player centre) each frame.
  • Screen shake is a random pixel offset added on top. It decays over time.
  • Every draw call in the game passes (wx - cam.x, wy - cam.y) to get screen pos.

PERFORMANCE NOTE:
  Camera is just two floats + a shake vector. Zero allocations per frame.
"""

import random
import pygame
import settings
from helpers import lerp, clamp


class Camera:
    def __init__(self, screen_w: int, screen_h: int,
                 world_w: int, world_h: int) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.world_w  = world_w
        self.world_h  = world_h

        # Top-left corner of the visible window in world space
        self.x = 0.0
        self.y = 0.0

        # Screen shake
        self._shake_magnitude = 0.0
        self._shake_offset_x  = 0.0
        self._shake_offset_y  = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def add_shake(self, magnitude: float) -> None:
        """Trigger a screen-shake burst. Magnitude is in pixels."""
        self._shake_magnitude = max(self._shake_magnitude, magnitude)

    def update(self, target_x: float, target_y: float, dt: float) -> None:
        """Smoothly follow (target_x, target_y) — these are the centre of the
        entity we're tracking (player world position)."""
        # Desired top-left so target is centred
        desired_x = target_x - self.screen_w / 2
        desired_y = target_y - self.screen_h / 2

        # Lerp current position toward desired
        t = clamp(settings.CAMERA_LERP * dt, 0.0, 1.0)
        self.x = lerp(self.x, desired_x, t)
        self.y = lerp(self.y, desired_y, t)

        # Clamp so camera never shows outside world bounds
        self.x = clamp(self.x, 0, self.world_w - self.screen_w)
        self.y = clamp(self.y, 0, self.world_h - self.screen_h)

        # Decay shake
        if self._shake_magnitude > 0:
            self._shake_magnitude -= settings.SCREEN_SHAKE_DECAY * dt
            self._shake_magnitude = max(0.0, self._shake_magnitude)
            m = self._shake_magnitude
            self._shake_offset_x = random.uniform(-m, m)
            self._shake_offset_y = random.uniform(-m, m)
        else:
            self._shake_offset_x = 0.0
            self._shake_offset_y = 0.0

    def world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        """Convert a world coordinate to screen pixel (with shake applied)."""
        sx = wx - self.x + self._shake_offset_x
        sy = wy - self.y + self._shake_offset_y
        return (int(sx), int(sy))

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        """Convert screen pixel back to world coordinate (for mouse aiming)."""
        return (sx + self.x - self._shake_offset_x,
                sy + self.y - self._shake_offset_y)

    def is_visible(self, wx: float, wy: float, margin: int = 60) -> bool:
        """Frustum cull: is the world point within the visible + margin region?"""
        return (self.x - margin <= wx <= self.x + self.screen_w + margin and
                self.y - margin <= wy <= self.y + self.screen_h + margin)
