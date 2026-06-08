"""
ui/menus.py — Main menu, pause screen, and game-over screen.

GAME STATE MANAGEMENT:
  Each menu returns a string action from handle_event():
    "start"   → transition to PLAYING
    "quit"    → exit application
    "resume"  → un-pause
    "restart" → reset and play again
    None      → no transition this frame

  game.py reads these actions and calls game.change_state() accordingly.
  Menus never directly mutate game state — they're pure UI that emit signals.

VISUAL DESIGN:
  Dark atmospheric panels with neon accents. Animated scanline effect on main
  menu for retro-arcade feel. Buttons have hover glow states.
"""

import math
import time
import pygame
import settings
from helpers import clamp


class _Button:
    """Reusable button widget with hover detection and glow effect."""

    def __init__(self, x: int, y: int, w: int, h: int,
                 text: str, font: pygame.font.Font,
                 action: str,
                 color_normal=(30, 40, 60),
                 color_hover=(50, 70, 110),
                 text_color=None) -> None:
        self.rect   = pygame.Rect(x - w // 2, y - h // 2, w, h)
        self.text   = text
        self.font   = font
        self.action = action
        self.c_norm = color_normal
        self.c_hov  = color_hover
        self.t_col  = text_color or settings.C_WHITE
        self._hover = False
        self._pulse = 0.0

    def update(self, dt: float, mouse_pos: tuple) -> None:
        self._hover = self.rect.collidepoint(mouse_pos)
        self._pulse = (self._pulse + dt * 3) % math.tau

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return self.action
        return None

    def draw(self, surface: pygame.Surface) -> None:
        color = self.c_hov if self._hover else self.c_norm
        pygame.draw.rect(surface, color, self.rect, border_radius=6)

        if self._hover:
            glow_alpha = int(60 + 30 * math.sin(self._pulse))
            glow_surf  = pygame.Surface(
                (self.rect.w + 16, self.rect.h + 16), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf,
                             (*settings.C_PLAYER, glow_alpha),
                             (0, 0, self.rect.w + 16, self.rect.h + 16),
                             border_radius=8)
            surface.blit(glow_surf,
                         (self.rect.x - 8, self.rect.y - 8))
            pygame.draw.rect(surface, settings.C_PLAYER,
                             self.rect, 2, border_radius=6)
        else:
            pygame.draw.rect(surface, settings.C_MID_GRAY,
                             self.rect, 1, border_radius=6)

        text_surf = self.font.render(self.text, True,
                                     settings.C_PLAYER_ACCENT if self._hover
                                     else self.t_col)
        tx = self.rect.centerx - text_surf.get_width() // 2
        ty = self.rect.centery - text_surf.get_height() // 2
        surface.blit(text_surf, (tx, ty))


# ─── Main Menu ────────────────────────────────────────────────────────────────

class MainMenu:
    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.sw, self.sh = screen_w, screen_h
        pygame.font.init()

        self._font_title = pygame.font.SysFont("consolas,monospace", 80, bold=True)
        self._font_sub   = pygame.font.SysFont("consolas,monospace", 22)
        self._font_btn   = pygame.font.SysFont("consolas,monospace", 24, bold=True)

        cx = screen_w // 2
        self._buttons = [
            _Button(cx, screen_h // 2 + 20,  260, 52, "PLAY",         self._font_btn, "start"),
            _Button(cx, screen_h // 2 + 90,  260, 52, "QUIT",         self._font_btn, "quit",
                    color_normal=(40, 20, 20), color_hover=(80, 30, 30)),
        ]

        self._t = 0.0
        self._scanline_surf = self._make_scanlines(screen_w, screen_h)

    def _make_scanlines(self, w: int, h: int) -> pygame.Surface:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 4):
            pygame.draw.line(s, (0, 0, 0, 30), (0, y), (w, y))
        return s

    def update(self, dt: float) -> None:
        self._t += dt
        mouse_pos = pygame.mouse.get_pos()
        for btn in self._buttons:
            btn.update(dt, mouse_pos)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        for btn in self._buttons:
            result = btn.handle_event(event)
            if result:
                return result
        return None

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.C_BG)

        # Animated grid background
        grid_surf = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        spacing = 64
        offset  = int(self._t * 20) % spacing
        for x in range(-spacing, self.sw + spacing, spacing):
            pygame.draw.line(grid_surf, (*settings.C_GRID, 180),
                             (x + offset, 0), (x + offset, self.sh))
        for y in range(-spacing, self.sh + spacing, spacing):
            pygame.draw.line(grid_surf, (*settings.C_GRID, 180),
                             (0, y + offset), (self.sw, y + offset))
        surface.blit(grid_surf, (0, 0))

        # Scanlines
        surface.blit(self._scanline_surf, (0, 0))

        # Title glow
        pulse = abs(math.sin(self._t * 1.5))
        glow_alpha = int(80 + 60 * pulse)
        title_surf = self._font_title.render("DEADZONE", True, settings.C_PLAYER)
        glow_surf  = self._font_title.render("DEADZONE", True, settings.C_PLAYER_ACCENT)
        tx = self.sw // 2 - title_surf.get_width() // 2
        ty = self.sh // 2 - 180
        # Glow layer (blurred by offset blitting)
        for off in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
            g = glow_surf.copy()
            g.set_alpha(glow_alpha // 2)
            surface.blit(g, (tx + off[0], ty + off[1]))
        surface.blit(title_surf, (tx, ty))

        # Subtitle
        sub  = self._font_sub.render("ZOMBIE SURVIVAL  •  WAVE SHOOTER", True,
                                      settings.C_MID_GRAY)
        surface.blit(sub, (self.sw // 2 - sub.get_width() // 2, ty + 90))

        # Controls hint
        controls = [
            "WASD — Move    SHIFT — Sprint    SPACE — Dash",
            "LMB — Shoot    R — Reload    1/2/3 — Weapon",
            "ESC — Pause",
        ]
        cy = self.sh - 100
        for line in controls:
            s = self._font_sub.render(line, True, settings.C_MID_GRAY)
            surface.blit(s, (self.sw // 2 - s.get_width() // 2, cy))
            cy += 22

        for btn in self._buttons:
            btn.draw(surface)


# ─── Pause Menu ───────────────────────────────────────────────────────────────

class PauseMenu:
    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.sw, self.sh = screen_w, screen_h
        self._font_title = pygame.font.SysFont("consolas,monospace", 48, bold=True)
        self._font_btn   = pygame.font.SysFont("consolas,monospace", 24, bold=True)
        self._font_hint  = pygame.font.SysFont("consolas,monospace", 18)

        cx = screen_w // 2
        cy = screen_h // 2
        self._buttons = [
            _Button(cx, cy,        240, 48, "RESUME",  self._font_btn, "resume"),
            _Button(cx, cy + 66,   240, 48, "MAIN MENU", self._font_btn, "main_menu",
                    color_normal=(20, 30, 50)),
            _Button(cx, cy + 132,  240, 48, "QUIT",    self._font_btn, "quit",
                    color_normal=(40, 20, 20), color_hover=(80, 30, 30)),
        ]
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        mp = pygame.mouse.get_pos()
        for btn in self._buttons:
            btn.update(dt, mp)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "resume"
        for btn in self._buttons:
            r = btn.handle_event(event)
            if r:
                return r
        return None

    def draw(self, surface: pygame.Surface) -> None:
        # Darken game behind
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        # Panel
        pw, ph = 340, 340
        panel  = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((10, 14, 24, 230))
        pygame.draw.rect(panel, settings.C_PLAYER, (0, 0, pw, ph), 2, border_radius=8)
        px = self.sw // 2 - pw // 2
        py = self.sh // 2 - ph // 2 - 20
        surface.blit(panel, (px, py))

        title = self._font_title.render("PAUSED", True, settings.C_WHITE)
        surface.blit(title, (self.sw // 2 - title.get_width() // 2, py + 24))

        for btn in self._buttons:
            btn.draw(surface)

        hint = self._font_hint.render("ESC to resume", True, settings.C_MID_GRAY)
        surface.blit(hint, (self.sw // 2 - hint.get_width() // 2, py + ph - 30))


# ─── Game Over Screen ─────────────────────────────────────────────────────────

class GameOverScreen:
    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.sw, self.sh = screen_w, screen_h
        self._font_big   = pygame.font.SysFont("consolas,monospace", 72, bold=True)
        self._font_med   = pygame.font.SysFont("consolas,monospace", 28)
        self._font_btn   = pygame.font.SysFont("consolas,monospace", 24, bold=True)

        cx = screen_w // 2
        cy = screen_h // 2
        self._buttons = [
            _Button(cx, cy + 80,  240, 48, "PLAY AGAIN", self._font_btn, "restart"),
            _Button(cx, cy + 146, 240, 48, "MAIN MENU",  self._font_btn, "main_menu",
                    color_normal=(20, 30, 50)),
            _Button(cx, cy + 212, 240, 48, "QUIT",       self._font_btn, "quit",
                    color_normal=(40, 20, 20), color_hover=(80, 30, 30)),
        ]
        self._t    = 0.0
        self._score    = 0
        self._wave     = 0
        self._kills    = 0
        self._best_score = 0
        self._new_best = False

    def set_results(self, score: int, wave: int, kills: int,
                    best_score: int) -> None:
        self._score     = score
        self._wave      = wave
        self._kills     = kills
        self._best_score = best_score
        self._new_best  = (score >= best_score)
        self._t         = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        mp = pygame.mouse.get_pos()
        for btn in self._buttons:
            btn.update(dt, mp)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        for btn in self._buttons:
            r = btn.handle_event(event)
            if r:
                return r
        return None

    def draw(self, surface: pygame.Surface) -> None:
        # Animated red overlay
        pulse     = abs(math.sin(self._t * 0.8))
        ov_alpha  = int(120 + 60 * pulse) if self._t < 1.5 else 140
        overlay   = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill((30, 0, 0, ov_alpha))
        surface.blit(overlay, (0, 0))

        cx = self.sw // 2
        cy = self.sh // 2

        # Title (slides in)
        slide = clamp(self._t * 3, 0.0, 1.0)
        title_y = int(cy - 160 - (1 - slide) * 80)
        title = self._font_big.render("YOU DIED", True, settings.C_ACCENT_RED)
        surface.blit(title, (cx - title.get_width() // 2, title_y))

        # Stats
        if self._t > 0.4:
            stats = [
                ("SCORE",    f"{self._score:,}"),
                ("WAVE",     str(self._wave)),
                ("KILLS",    str(self._kills)),
                ("BEST",     f"{self._best_score:,}" + (" ★" if self._new_best else "")),
            ]
            for i, (label, value) in enumerate(stats):
                alpha = min(255, int((self._t - 0.4 - i * 0.1) * 500))
                lsurf = self._font_med.render(f"{label:<8}{value:>10}", True, settings.C_WHITE)
                lsurf.set_alpha(alpha)
                surface.blit(lsurf, (cx - lsurf.get_width() // 2,
                                     cy - 50 + i * 32))

        if self._t > 1.0:
            for btn in self._buttons:
                btn.draw(surface)
