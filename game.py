"""
game.py — Core game orchestrator.

ARCHITECTURE ROLE:
  game.py is the conductor. It owns:
    • The game state machine (MAIN_MENU → PLAYING → PAUSED → GAME_OVER)
    • All entity lists (player, zombies, bullets)
    • All subsystem instances (camera, particles, collision, waves, hud, menus)
    • The world renderer (grid, border)

  It does NOT contain collision logic, particle math, or UI layout — those live
  in their own modules. game.py wires them together.

UPDATE/RENDER LOOP:
  main.py → game.update(dt) → processes input, updates all systems/entities
  main.py → game.draw(screen) → renders world then HUD then menu overlays

  The order within update() matters:
    1. Handle input → produce intent
    2. Update player (returns new bullets)
    3. Update zombies
    4. Update bullets
    5. Run collision pipeline
    6. Run wave manager
    7. Update camera
    8. Update particles
    9. Update HUD/menus

ENTITY LIFECYCLE / CLEANUP:
  Entities set self.alive = False when dead. Dead entity purging happens at the
  END of each update() tick (after collision) to avoid modifying lists mid-loop.
  This is the "tombstone" pattern — safe and predictable.

PERFORMANCE CONSIDERATIONS:
  • Dead-entity purge is O(n) list comprehension — fine for <500 entities.
  • World grid is cached as a Surface and only re-blit (fast).
  • Frustum culling in Camera.is_visible() prevents drawing off-screen entities.
"""

import pygame
import settings

from constants import GameState

from player import Player
from zombie import Zombie
from bullet import Bullet

from camera import Camera
from particles import ParticleSystem
from collision import CollisionSystem
from waves import WaveManager

from hud import HUD
from menus import MainMenu, PauseMenu, GameOverScreen


class Game:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen   = screen
        self.sw       = settings.SCREEN_W
        self.sh       = settings.SCREEN_H
        self.ww       = settings.WORLD_W
        self.wh       = settings.WORLD_H

        # ── Systems ─────────────────────────────────────────────────────────
        self.camera    = Camera(self.sw, self.sh, self.ww, self.wh)
        self.particles = ParticleSystem()
        self.collision = CollisionSystem(self.ww, self.wh)

        # ── UI ──────────────────────────────────────────────────────────────
        self.hud       = HUD(self.sw, self.sh)
        self.main_menu = MainMenu(self.sw, self.sh)
        self.pause_menu= PauseMenu(self.sw, self.sh)
        self.gameover  = GameOverScreen(self.sw, self.sh)

        # ── State ───────────────────────────────────────────────────────────
        self.state     = GameState.MAIN_MENU
        self._best_score = 0

        # ── Gameplay data ────────────────────────────────────────────────────
        self.player  : Player | None = None
        self.zombies : list[Zombie]  = []
        self.bullets : list[Bullet]  = []
        self.waves   : WaveManager | None = None
        self.score   = 0
        self.kills   = 0
        self._score_tick = 0.0   # time-based score accumulator

        # ── World surface (pre-rendered background) ──────────────────────────
        self._world_surf = self._build_world_surface()

        # ── Audio ────────────────────────────────────────────────────────────
        self._sfx = {}
        self._load_audio()

        # ── Cursor ───────────────────────────────────────────────────────────
        pygame.mouse.set_visible(False)

    # ── Audio setup ──────────────────────────────────────────────────────────

    def _load_audio(self) -> None:
        """
        Load sound effects. If files are missing the game continues silently.
        Drop .wav files into assets/sounds/ with these names to enable audio.
        """
        import os
        sound_map = {
            "shoot_pistol": "assets/sounds/shoot_pistol.wav",
            "shoot_shotgun": "assets/sounds/shoot_shotgun.wav",
            "shoot_smg":    "assets/sounds/shoot_smg.wav",
            "zombie_hit":   "assets/sounds/zombie_hit.wav",
            "zombie_die":   "assets/sounds/zombie_die.wav",
            "player_hit":   "assets/sounds/player_hit.wav",
            "reload":       "assets/sounds/reload.wav",
            "dash":         "assets/sounds/dash.wav",
        }
        if pygame.mixer.get_init():
            for key, path in sound_map.items():
                if os.path.exists(path):
                    try:
                        sfx = pygame.mixer.Sound(path)
                        sfx.set_volume(settings.SFX_VOLUME)
                        self._sfx[key] = sfx
                    except Exception:
                        pass
            # Background music
            music_path = "assets/music/ambient.ogg"
            if os.path.exists(music_path):
                try:
                    pygame.mixer.music.load(music_path)
                    pygame.mixer.music.set_volume(settings.MUSIC_VOLUME)
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass

    def _play_sfx(self, name: str) -> None:
        sfx = self._sfx.get(name)
        if sfx:
            sfx.play()

    # ── World surface ────────────────────────────────────────────────────────

    def _build_world_surface(self) -> pygame.Surface:
        """
        Pre-render the static world background once.
        Blit this each frame instead of redrawing all grid lines — huge speedup.
        """
        surf = pygame.Surface((self.ww, self.wh))
        surf.fill(settings.C_BG)

        # Grid lines
        ts = settings.TILE_SIZE
        for x in range(0, self.ww, ts):
            pygame.draw.line(surf, settings.C_GRID, (x, 0), (x, self.wh))
        for y in range(0, self.wh, ts):
            pygame.draw.line(surf, settings.C_GRID, (0, y), (self.ww, y))

        # World border (bright so player knows the edge)
        border_col = (40, 55, 80)
        border_w   = 6
        pygame.draw.rect(surf, border_col, (0, 0, self.ww, self.wh), border_w)

        # Corner markers
        corner_size = 40
        for cx, cy in [(0, 0), (self.ww, 0), (0, self.wh), (self.ww, self.wh)]:
            pygame.draw.circle(surf, settings.C_PLAYER, (cx, cy), corner_size, 3)

        return surf

    # ── Game setup / teardown ─────────────────────────────────────────────────

    def _start_new_game(self) -> None:
        cx, cy       = self.ww // 2, self.wh // 2
        self.player  = Player(cx, cy)
        self.zombies = []
        self.bullets = []
        self.waves   = WaveManager(self.ww, self.wh)
        self.score   = 0
        self.kills   = 0
        self._score_tick = 0.0
        self.particles = ParticleSystem()
        # Snap camera to player immediately (no lerp on first frame)
        self.camera.x = cx - self.sw / 2
        self.camera.y = cy - self.sh / 2

    # ── State machine ────────────────────────────────────────────────────────

    def change_state(self, new_state: GameState) -> None:
        if new_state == GameState.PLAYING and self.state != GameState.PAUSED:
            self._start_new_game()
        if new_state == GameState.GAME_OVER:
            self._best_score = max(self._best_score, self.score)
            self.gameover.set_results(
                self.score, self.waves.wave_number, self.kills, self._best_score)
        self.state = new_state

    # ── Main update ──────────────────────────────────────────────────────────

    def update(self, dt: float, events: list) -> None:
        if self.state == GameState.MAIN_MENU:
            self._update_main_menu(dt, events)
        elif self.state == GameState.PLAYING:
            self._update_playing(dt, events)
        elif self.state == GameState.PAUSED:
            self._update_paused(dt, events)
        elif self.state == GameState.GAME_OVER:
            self._update_game_over(dt, events)

    def _update_main_menu(self, dt: float, events: list) -> None:
        self.main_menu.update(dt)
        for event in events:
            action = self.main_menu.handle_event(event)
            if action == "start":
                self.change_state(GameState.PLAYING)
            elif action == "quit":
                pygame.quit()
                raise SystemExit

    def _update_paused(self, dt: float, events: list) -> None:
        self.pause_menu.update(dt)
        for event in events:
            action = self.pause_menu.handle_event(event)
            if action == "resume":
                self.state = GameState.PLAYING
            elif action == "main_menu":
                self.state = GameState.MAIN_MENU
            elif action == "quit":
                pygame.quit()
                raise SystemExit

    def _update_game_over(self, dt: float, events: list) -> None:
        self.gameover.update(dt)
        for event in events:
            action = self.gameover.handle_event(event)
            if action == "restart":
                self.change_state(GameState.PLAYING)
            elif action == "main_menu":
                self.state = GameState.MAIN_MENU
            elif action == "quit":
                pygame.quit()
                raise SystemExit

    def _update_playing(self, dt: float, events: list) -> None:
        # ── Input parsing ────────────────────────────────────────────────────
        keys           = pygame.key.get_pressed()
        fire_pressed   = pygame.mouse.get_pressed()[0]
        mouse_screen   = pygame.mouse.get_pos()
        mouse_world    = self.camera.screen_to_world(*mouse_screen)
        sprint_held    = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        dash_pressed   = False
        reload_pressed = False

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = GameState.PAUSED
                    return
                if event.key == pygame.K_r:
                    reload_pressed = True
                if event.key == pygame.K_SPACE:
                    dash_pressed = True
                if event.key == pygame.K_1:
                    self.player.switch_weapon(0)
                if event.key == pygame.K_2:
                    self.player.switch_weapon(1)
                if event.key == pygame.K_3:
                    self.player.switch_weapon(2)
            if event.type == pygame.MOUSEWHEEL:
                self.player.scroll_weapon(event.y)

        # ── Player update ────────────────────────────────────────────────────
        prev_ammo = self.player.ammo
        new_bullets = self.player.update(
            dt, keys, mouse_world, fire_pressed,
            reload_pressed, dash_pressed, sprint_held
        )

        # Audio cues on shoot
        if new_bullets:
            weapon_name = self.player.current_weapon_name
            self._play_sfx(f"shoot_{weapon_name}")
            # Muzzle flash particle
            self.particles.spawn_muzzle_flash(
                self.player.x, self.player.y, self.player.facing)

        # Reload SFX
        if prev_ammo > 0 and self.player.ammo == self.player.ammo_max:
            self._play_sfx("reload")

        self.bullets.extend(new_bullets)

        # ── Zombie update ────────────────────────────────────────────────────
        for zombie in self.zombies:
            if zombie.alive:
                zombie.update(dt, self.player)

        # ── Bullet update ────────────────────────────────────────────────────
        for bullet in self.bullets:
            bullet.update(dt)

        # ── Collision ────────────────────────────────────────────────────────
        self.collision.process(
            self.player, self.bullets, self.zombies,
            self.particles, self.camera
        )

        # ── Dead entity cleanup + scoring ─────────────────────────────────────
        for zombie in self.zombies:
            if not zombie.alive and zombie.score_value > 0:
                self.score  += zombie.score_value
                self.kills  += 1
                self.particles.spawn_zombie_death(
                    zombie.x, zombie.y, zombie.base_color)
                self._play_sfx("zombie_die")
                zombie.score_value = 0   # prevent double-counting

        self.zombies = [z for z in self.zombies if z.alive]
        self.bullets = [b for b in self.bullets if b.alive]

        # ── Survival score (time bonus) ────────────────────────────────────
        self._score_tick += dt
        if self._score_tick >= 1.0:
            self.score += self.waves.wave_number  # score per second = wave level
            self._score_tick -= 1.0

        # ── Wave manager ────────────────────────────────────────────────────
        self.waves.update(dt, self.zombies, self.player)

        # ── Camera ──────────────────────────────────────────────────────────
        self.camera.update(self.player.x, self.player.y, dt)

        # ── Particles ───────────────────────────────────────────────────────
        self.particles.update(dt)

        # ── HUD ─────────────────────────────────────────────────────────────
        self.hud.update(dt)

        # ── Game over check ──────────────────────────────────────────────────
        if not self.player.alive:
            self.change_state(GameState.GAME_OVER)

    # ── Main draw ────────────────────────────────────────────────────────────

    def draw(self, fps: int) -> None:
        if self.state == GameState.MAIN_MENU:
            self.main_menu.draw(self.screen)
            return

        if self.state == GameState.GAME_OVER:
            # Draw last frame of gameplay behind overlay
            self._draw_world(fps)
            self.gameover.draw(self.screen)
            return

        self._draw_world(fps)

        if self.state == GameState.PAUSED:
            self.pause_menu.draw(self.screen)

    def _draw_world(self, fps) -> None:
        # 1. Background (pre-rendered static world)
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)
        self.screen.blit(self._world_surf, (0, 0),
                         area=pygame.Rect(cam_x, cam_y, self.sw, self.sh))

        # 2. Bullets (behind entities)
        for bullet in self.bullets:
            bullet.draw(self.screen, self.camera)

        # 3. Zombies
        for zombie in self.zombies:
            if self.camera.is_visible(zombie.x, zombie.y, margin=60):
                zombie.draw(self.screen, self.camera)

        # 4. Player
        if self.player and self.player.alive:
            self.player.draw(self.screen, self.camera)

        # 5. Particles (above entities)
        self.particles.draw(self.screen, self.camera)

        # 6. HUD (screen-space — always on top of world)
        if self.state == GameState.PLAYING and self.player:
            self.hud.draw(self.screen, self.player, self.waves,
                          self.score, fps, self.particles.count)
