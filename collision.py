"""
systems/collision.py — Centralised collision detection and resolution.

WHY THIS EXISTS:
  Collision logic scattered across entities creates circular import hell and
  O(n²) redundant checks. A dedicated system:
  - Owns the collision budget
  - Can add spatial partitioning later without touching entities
  - Provides a single place to profile and optimise

COLLISION PIPELINE (per frame):
  1. bullets ↔ zombies  → damage + death + particles
  2. zombies ↔ player   → player damage + iframes check
  3. zombie ↔ zombie    → separation push (prevents stacking)
  4. player bounds       → clamp inside world

PERFORMANCE NOTE:
  For <200 entities Python's O(n²) brute-force is fast enough (< 0.3 ms per
  frame). If you need more zombies, add a simple grid spatial hash here — the
  interface stays identical.
"""

import settings
from helpers import circles_overlap, push_apart, distance


class CollisionSystem:
    def __init__(self, world_w: int, world_h: int) -> None:
        self.world_w = world_w
        self.world_h = world_h

    def process(self, player, bullets: list, zombies: list,
                particles, camera) -> None:
        """
        Main entry point called once per frame.
        Mutates entities in-place; never returns values.
        """
        self._bullets_vs_zombies(bullets, zombies, particles)
        self._player_vs_zombies(player, zombies, particles, camera)
        self._zombie_separation(zombies)
        self._clamp_player(player)
        self._clamp_zombies(zombies)

    # ── Collision tests ───────────────────────────────────────────────────────

    def _bullets_vs_zombies(self, bullets: list, zombies: list,
                             particles) -> None:
        to_remove_bullets = set()
        for bi, bullet in enumerate(bullets):
            if not bullet.alive:
                continue
            for zombie in zombies:
                if not zombie.alive:
                    continue
                if circles_overlap(bullet.x, bullet.y, settings.BULLET_RADIUS,
                                   zombie.x, zombie.y, zombie.radius):
                    # Direction from zombie toward bullet origin (recoil direction)
                    dx = bullet.vx
                    dy = bullet.vy
                    length = (dx*dx + dy*dy) ** 0.5
                    if length > 0:
                        dx, dy = dx / length, dy / length

                    zombie.take_damage(bullet.damage)
                    particles.spawn_blood(zombie.x, zombie.y, (dx, dy))

                    to_remove_bullets.add(bi)
                    break  # one bullet hits one zombie

        # Remove consumed bullets (reverse order preserves indices)
        for i in sorted(to_remove_bullets, reverse=True):
            bullets[i].alive = False

    def _player_vs_zombies(self, player, zombies: list,
                            particles, camera) -> None:
        for zombie in zombies:
            if not zombie.alive:
                continue
            if circles_overlap(player.x, player.y, player.radius,
                                zombie.x, zombie.y, zombie.radius):
                # Zombie attacks based on its attack timer
                if zombie.can_attack():
                    damage = zombie.get_damage()
                    if player.take_damage(damage):
                        camera.add_shake(10.0)
                        particles.spawn_player_damage(player.x, player.y)

    def _zombie_separation(self, zombies: list) -> None:
        """Push overlapping zombies apart to prevent pile-ups."""
        r = settings.ZOMBIE_SEPARATION_RADIUS
        for i in range(len(zombies)):
            if not zombies[i].alive:
                continue
            for j in range(i + 1, len(zombies)):
                if not zombies[j].alive:
                    continue
                za, zb = zombies[i], zombies[j]
                combined_r = za.radius + zb.radius
                if circles_overlap(za.x, za.y, za.radius,
                                   zb.x, zb.y, zb.radius):
                    da, db = push_apart(za.x, za.y, za.radius,
                                        zb.x, zb.y, zb.radius, strength=0.5)
                    za.x += da[0]
                    za.y += da[1]
                    zb.x += db[0]
                    zb.y += db[1]

    def _clamp_player(self, player) -> None:
        r = player.radius
        player.x = max(r, min(self.world_w - r, player.x))
        player.y = max(r, min(self.world_h - r, player.y))

    def _clamp_zombies(self, zombies: list) -> None:
        for z in zombies:
            if not z.alive:
                continue
            r = z.radius
            z.x = max(r, min(self.world_w - r, z.x))
            z.y = max(r, min(self.world_h - r, z.y))
