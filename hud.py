"""
ui/hud.py — In-game HUD rendering.

WHY THIS EXISTS:
  Keeps all UI drawing code out of game.py. The HUD reads player/wave state
  as read-only; it never mutates anything. Pure display layer.

RENDERING NOTE:
  Fonts are cached at __init__ time — never call pygame.font.Font() in a loop.
  Alpha surfaces for panel backgrounds are pre-allocated where possible.
"""

import math
import pygame
import settings
from helpers import draw_bar, clamp


class HUD:
    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.sw = screen_w
        self.sh = screen_h

        pygame.font.init()
        self._font_lg  = pygame.font.SysFont("consolas,monospace", settings.HUD_FONT_LARGE, bold=True)
        self._font_md  = pygame.font.SysFont("consolas,monospace", settings.HUD_FONT_MED)
        self._font_sm  = pygame.font.SysFont("consolas,monospace", settings.HUD_FONT_SMALL)
        self._font_xl  = pygame.font.SysFont("consolas,monospace", 64, bold=True)

        m              = settings.HUD_MARGIN
        self._margin   = m

        # Pre-build panel surface for bottom bar
        self._panel_h   = 70
        self._panel_surf = pygame.Surface((screen_w, self._panel_h), pygame.SRCALPHA)

        self._pulse_t   = 0.0   # for animated elements

    def update(self, dt: float) -> None:
        self._pulse_t += dt

    def draw(self, surface: pygame.Surface, player, wave_mgr,
             score: int, fps: int, particle_count: int) -> None:
        self._draw_bottom_panel(surface, player)
        self._draw_top_bar(surface, score, wave_mgr, fps, particle_count)
        self._draw_crosshair(surface, player)
        self._draw_reload_indicator(surface, player)
        self._draw_wave_alert(surface, wave_mgr)
        self._draw_weapon_slots(surface, player)

    # ── Bottom panel (health, stamina, ammo) ─────────────────────────────────

    def _draw_bottom_panel(self, surface: pygame.Surface, player) -> None:
        m   = self._margin
        pw  = self.sw
        ph  = self._panel_h
        py  = self.sh - ph

        # Translucent panel
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((8, 10, 16, 200))
        surface.blit(panel, (0, py))

        # Separator line
        pygame.draw.line(surface, settings.C_MID_GRAY,
                         (0, py), (pw, py), 1)

        # ─ Health ─
        bw = settings.HUD_BAR_W
        bh = settings.HUD_BAR_H
        bx = m
        by = py + 14

        # Label
        hp_label = self._font_sm.render("HP", True, settings.C_MID_GRAY)
        surface.blit(hp_label, (bx, by - 14))

        hp_ratio = player.health / player.max_health
        if hp_ratio > 0.5:
            bar_col = settings.C_HEALTH_GOOD
        elif hp_ratio > 0.25:
            bar_col = settings.C_ACCENT_GOLD
        else:
            # Pulse red when critical
            pulse = abs(math.sin(self._pulse_t * 4))
            r = int(200 + 55 * pulse)
            bar_col = (r, 30, 30)

        draw_bar(surface, bx, by, bw, bh,
                 player.health, player.max_health,
                 bar_col, settings.C_HEALTH_BAR_BG,
                 border_color=settings.C_MID_GRAY)

        hp_text = self._font_sm.render(
            f"{player.health}/{player.max_health}", True, settings.C_WHITE)
        surface.blit(hp_text, (bx + bw + 8, by - 2))

        # ─ Stamina ─
        by2 = by + bh + 10
        sta_label = self._font_sm.render("STAM", True, settings.C_MID_GRAY)
        surface.blit(sta_label, (bx, by2 - 14))
        draw_bar(surface, bx, by2, bw, bh - 4,
                 player.stamina, player.max_stamina,
                 settings.C_XP_BAR, (20, 25, 40),
                 border_color=settings.C_MID_GRAY)

        # ─ Dash cooldown indicator ─
        dcx = bx + bw + 70
        dcy = py + self._panel_h // 2
        dash_r = 14
        ratio  = player.dash_cooldown_ratio
        color  = settings.C_PLAYER if ratio >= 1.0 else settings.C_MID_GRAY
        pygame.draw.circle(surface, (20, 25, 40), (dcx, dcy), dash_r)
        # Arc fill
        if ratio > 0:
            start_angle = -math.pi / 2
            end_angle   = start_angle + math.tau * ratio
            rect        = pygame.Rect(dcx - dash_r, dcy - dash_r,
                                      dash_r * 2, dash_r * 2)
            pygame.draw.arc(surface, color, rect, start_angle, end_angle, 4)
        pygame.draw.circle(surface, color, (dcx, dcy), dash_r, 2)
        dash_lbl = self._font_sm.render("DASH", True, settings.C_MID_GRAY)
        surface.blit(dash_lbl, (dcx - dash_lbl.get_width() // 2, dcy + dash_r + 2))

    # ── Top info bar ─────────────────────────────────────────────────────────

    def _draw_top_bar(self, surface: pygame.Surface, score: int,
                       wave_mgr, fps: int, particle_count: int) -> None:
        m   = self._margin
        bh  = 36
        panel = pygame.Surface((self.sw, bh), pygame.SRCALPHA)
        panel.fill((8, 10, 16, 180))
        surface.blit(panel, (0, 0))
        pygame.draw.line(surface, settings.C_MID_GRAY,
                         (0, bh), (self.sw, bh), 1)

        # Score
        score_surf = self._font_md.render(f"SCORE  {score:,}", True,
                                          settings.C_ACCENT_GOLD)
        surface.blit(score_surf, (m, 7))

        # Wave
        wave_text = f"WAVE  {wave_mgr.wave_number}"
        if wave_mgr.is_boss_wave and not wave_mgr.in_cooldown:
            wave_text += "  ⚠ BOSS"
        wave_surf = self._font_md.render(wave_text, True, settings.C_WHITE)
        surface.blit(wave_surf,
                     (self.sw // 2 - wave_surf.get_width() // 2, 7))

        # FPS (debug)
        fps_surf  = self._font_sm.render(f"FPS {fps}  P{particle_count}", True,
                                         settings.C_MID_GRAY)
        surface.blit(fps_surf, (self.sw - fps_surf.get_width() - m, 10))

    # ── Weapon slots ─────────────────────────────────────────────────────────

    def _draw_weapon_slots(self, surface: pygame.Surface, player) -> None:
        from constants import WEAPON_ORDER
        slot_w, slot_h = 80, 52
        gap    = 6
        total  = len(WEAPON_ORDER) * (slot_w + gap) - gap
        start_x = self.sw - total - self._margin
        start_y = self.sh - self._panel_h - slot_h - 8

        for i, wname in enumerate(WEAPON_ORDER):
            sx = start_x + i * (slot_w + gap)
            sy = start_y

            active  = (i == player._weapon_slot)
            bg_col  = (30, 40, 60) if active else (12, 15, 22)
            bdr_col = settings.C_PLAYER if active else settings.C_MID_GRAY

            pygame.draw.rect(surface, bg_col, (sx, sy, slot_w, slot_h), border_radius=4)
            pygame.draw.rect(surface, bdr_col, (sx, sy, slot_w, slot_h), 2, border_radius=4)

            # Name
            name_surf = self._font_sm.render(wname.upper(), True,
                                             settings.C_WHITE if active else settings.C_MID_GRAY)
            surface.blit(name_surf,
                         (sx + slot_w // 2 - name_surf.get_width() // 2, sy + 4))

            # Ammo (only for active)
            if active:
                ws    = player._weapons[wname]
                ammo_text = f"{ws.ammo}/{player.ammo_max}"
                if player.is_reloading:
                    ammo_text = "RELOAD"
                ammo_surf = self._font_sm.render(ammo_text, True,
                                                 settings.C_ACCENT_GOLD)
                surface.blit(ammo_surf,
                             (sx + slot_w // 2 - ammo_surf.get_width() // 2, sy + 26))

                # Ammo pip bar
                if not player.is_reloading:
                    pip_w = (slot_w - 8) // player.ammo_max
                    for p in range(player.ammo_max):
                        pcol = settings.C_ACCENT_GOLD if p < ws.ammo else (40, 40, 50)
                        pygame.draw.rect(surface, pcol,
                                         (sx + 4 + p * pip_w, sy + slot_h - 8,
                                          max(1, pip_w - 1), 4))
            else:
                key_surf = self._font_sm.render(str(i + 1), True, settings.C_MID_GRAY)
                surface.blit(key_surf,
                             (sx + slot_w // 2 - key_surf.get_width() // 2, sy + 26))

    # ── Crosshair ────────────────────────────────────────────────────────────

    def _draw_crosshair(self, surface: pygame.Surface, player) -> None:
        mx, my = pygame.mouse.get_pos()
        size   = 10
        gap    = 5
        color  = settings.C_WHITE
        w      = 2

        pygame.draw.line(surface, color, (mx - size - gap, my), (mx - gap, my), w)
        pygame.draw.line(surface, color, (mx + gap, my), (mx + size + gap, my), w)
        pygame.draw.line(surface, color, (mx, my - size - gap), (mx, my - gap), w)
        pygame.draw.line(surface, color, (mx, my + gap), (mx, my + size + gap), w)
        pygame.draw.circle(surface, color, (mx, my), 2, 1)

    # ── Reload indicator ─────────────────────────────────────────────────────

    def _draw_reload_indicator(self, surface: pygame.Surface, player) -> None:
        if not player.is_reloading:
            return
        mx, my = pygame.mouse.get_pos()
        r      = 20
        progress = player.reload_progress
        start_a  = -math.pi / 2
        end_a    = start_a + math.tau * progress
        rect     = pygame.Rect(mx - r, my + 12, r * 2, r * 2)
        pygame.draw.arc(surface, settings.C_ACCENT_GOLD, rect,
                        start_a, end_a, 3)
        pygame.draw.arc(surface, settings.C_MID_GRAY, rect,
                        end_a, start_a + math.tau, 3)

    # ── Wave alert ───────────────────────────────────────────────────────────

    def _draw_wave_alert(self, surface: pygame.Surface, wave_mgr) -> None:
        if not wave_mgr.in_cooldown:
            return
        t   = wave_mgr.cooldown_remaining
        cd  = settings.WAVE_COOLDOWN

        # Fade in/out
        alpha_ratio = min(1.0, (cd - t) * 3) * min(1.0, t * 3)
        alpha       = int(255 * alpha_ratio)
        if alpha <= 0:
            return

        # Next wave number
        next_wave = wave_mgr.wave_number + 1
        is_boss   = (next_wave % settings.WAVE_BOSS_EVERY == 0)

        if is_boss:
            text  = f"⚠  BOSS WAVE  {next_wave}  ⚠"
            color = settings.C_ACCENT_RED
        else:
            text  = f"WAVE  {next_wave}  INCOMING"
            color = settings.C_WHITE

        # Count down
        count_text = f"{int(t) + 1}"

        msg_surf    = self._font_lg.render(text, True, color)
        count_surf  = self._font_xl.render(count_text, True,
                                           settings.C_ACCENT_GOLD)

        cx = self.sw // 2
        cy = self.sh // 2 - 60

        # Apply alpha via a temp surface
        tmp = pygame.Surface((self.sw, 120), pygame.SRCALPHA)
        tmp.blit(msg_surf,
                 (cx - msg_surf.get_width() // 2, 10))
        tmp.blit(count_surf,
                 (cx - count_surf.get_width() // 2, 50))
        tmp.set_alpha(alpha)
        surface.blit(tmp, (0, cy))
