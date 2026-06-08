"""
main.py — Entry point and game loop.

WHY THIS EXISTS AS A SEPARATE FILE:
  Keeps pygame initialisation, the clock, and the core loop in one place.
  game.py contains ZERO pygame.init() or display.set_mode() — that's always
  main.py's job. This means you can instantiate Game in tests without a display.

GAME LOOP PATTERN (Fixed timestep with dt cap):
  dt is capped at 0.05 s (20 FPS minimum effective) to prevent the "spiral of
  death" — if the game lags severely, entities won't teleport across the map.

BEGINNER MISTAKE TO AVOID:
  Never multiply movement by raw clock.tick() — always divide by 1000 to get
  seconds, or use clock.tick() / 1000.0. Use the cap.
"""

import sys
import os

# Ensure the project root is on sys.path regardless of how/where Python is invoked.
# This fixes "ModuleNotFoundError: No module named 'utils'" on Windows.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
import settings
from game import Game


def main() -> None:
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

    # Display
    screen = pygame.display.set_mode(
        (settings.SCREEN_W, settings.SCREEN_H),
        pygame.DOUBLEBUF | pygame.HWSURFACE
    )
    pygame.display.set_caption(settings.TITLE)

    # Hide default cursor (HUD draws a custom crosshair)
    pygame.mouse.set_visible(False)

    clock = pygame.time.Clock()
    game  = Game(screen)

    # ── Main loop ────────────────────────────────────────────────────────────
    running = True
    while running:
        # Delta time — cap to prevent spiral of death on lag spikes
        raw_dt = clock.tick(settings.FPS_TARGET) / 1000.0
        dt     = min(raw_dt, 0.05)

        # ── Event collection ──────────────────────────────────────────────────
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        # ── Update ────────────────────────────────────────────────────────────
        try:
            game.update(dt, events)
        except SystemExit:
            running = False
            break

        # ── Render ────────────────────────────────────────────────────────────
        fps = int(clock.get_fps())
        game.draw(fps)
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()