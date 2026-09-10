"""Interactive start/end position editor.

Run with ``python main.py --editor``. Place each horse's starting position (at
the gate) and ending position (at the finish), then save to
``data/positions.json``. Positions are stored in background space so they stay
valid at any window resolution.

Controls (also shown on screen):
  1 / 2 / 3 / 4   select player
  Tab             toggle between editing START and END of the selected player
  Mouse drag      move the nearest / active marker
  Arrow keys      nudge the active marker by 1px (Shift = 10px)
  S               save to data/positions.json
  R               reload from disk
  F               toggle fullscreen
  Esc / Q         quit editor
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import pygame

import config
from game.assets import Assets
from game.players import Player, load_players, save_players

MARKER_RADIUS = 9
PICK_RADIUS = 22


class Editor:
    def __init__(self, screen: pygame.Surface, assets: Assets) -> None:
        self.screen = screen
        self.assets = assets
        self.players: List[Player] = load_players()
        self.font = pygame.font.SysFont("consolas", 16)
        self.big_font = pygame.font.SysFont("consolas", 22, bold=True)

        self.active_player = 0
        self.active_endpoint = "start"  # or "end"
        self.dragging = False
        self.status = "Loaded positions"
        self.fullscreen = config.START_FULLSCREEN
        self.running = True

    # ------------------------------------------------------------------ #
    def _endpoint_pos(self, player: Player, endpoint: str) -> List[float]:
        return player.start_pos if endpoint == "start" else player.end_pos

    def _all_markers(self):
        """Yield (player_index, endpoint, bg_pos)."""
        for p in self.players:
            yield (p.index, "start", p.start_pos)
            yield (p.index, "end", p.end_pos)

    def _pick_marker(self, mouse) -> Optional[Tuple[int, str]]:
        best = None
        best_d = PICK_RADIUS
        for idx, endpoint, bg_pos in self._all_markers():
            sx, sy = self.assets.bg_to_screen(bg_pos)
            d = math.hypot(mouse[0] - sx, mouse[1] - sy)
            if d <= best_d:
                best_d = d
                best = (idx, endpoint)
        return best

    # ------------------------------------------------------------------ #
    def run(self) -> None:
        clock = pygame.time.Clock()
        self.assets.recompute_layout(self.screen.get_size())
        while self.running:
            for event in pygame.event.get():
                self._handle_event(event)
            self.assets.recompute_layout(self.screen.get_size())
            self._draw()
            pygame.display.flip()
            clock.tick(config.FPS)

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
            self.screen = pygame.display.set_mode(
                (event.w, event.h), pygame.RESIZABLE
            )
        elif event.type == pygame.KEYDOWN:
            self._handle_key(event)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pick = self._pick_marker(event.pos)
            if pick is not None:
                self.active_player, self.active_endpoint = pick
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_active_pos(self.assets.screen_to_bg(event.pos))

    def _handle_key(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_ESCAPE, pygame.K_q):
            self.running = False
        elif event.key in (pygame.K_1, pygame.K_KP1):
            self.active_player = 0
        elif event.key in (pygame.K_2, pygame.K_KP2):
            self.active_player = 1
        elif event.key in (pygame.K_3, pygame.K_KP3):
            self.active_player = 2
        elif event.key in (pygame.K_4, pygame.K_KP4):
            self.active_player = 3
        elif event.key == pygame.K_TAB:
            self.active_endpoint = "end" if self.active_endpoint == "start" else "start"
        elif event.key == pygame.K_s:
            save_players(self.players)
            self.status = f"Saved to {config.POSITIONS_FILE.name}"
        elif event.key == pygame.K_r:
            self.players = load_players()
            self.status = "Reloaded positions"
        elif event.key == pygame.K_f:
            self._toggle_fullscreen()
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
            self._nudge(event)

    def _nudge(self, event: pygame.event.Event) -> None:
        step = 10.0 if (event.mod & pygame.KMOD_SHIFT) else 1.0
        # convert a screen-pixel nudge into background space
        step /= max(self.assets.scale, 1e-6)
        pos = self._endpoint_pos(self.players[self.active_player], self.active_endpoint)
        if event.key == pygame.K_LEFT:
            pos[0] -= step
        elif event.key == pygame.K_RIGHT:
            pos[0] += step
        elif event.key == pygame.K_UP:
            pos[1] -= step
        elif event.key == pygame.K_DOWN:
            pos[1] += step

    def _set_active_pos(self, bg_pos: Tuple[float, float]) -> None:
        bw, bh = config.BACKGROUND_SIZE
        clamped = [max(0.0, min(bw, bg_pos[0])), max(0.0, min(bh, bg_pos[1]))]
        player = self.players[self.active_player]
        if self.active_endpoint == "start":
            player.start_pos = clamped
        else:
            player.end_pos = clamped

    def _toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            if config.FULLSCREEN_SIZE:
                import os
                os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"
                self.screen = pygame.display.set_mode(config.FULLSCREEN_SIZE, pygame.NOFRAME)
            else:
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(config.WINDOW_SIZE, pygame.RESIZABLE)

    # ------------------------------------------------------------------ #
    def _draw(self) -> None:
        self.assets.draw_background(self.screen)

        for p in self.players:
            is_active_p = p.index == self.active_player
            start_screen = self.assets.bg_to_screen(p.start_pos)
            end_screen = self.assets.bg_to_screen(p.end_pos)

            pygame.draw.line(self.screen, p.color, start_screen, end_screen, 2)

            # Ghost sprites at both endpoints.
            self.assets.draw_player(self.screen, p.index, start_screen, alpha=110)
            self.assets.draw_player(self.screen, p.index, end_screen, alpha=70)

            self._draw_marker(start_screen, p.color, "S", is_active_p and self.active_endpoint == "start")
            self._draw_marker(end_screen, p.color, "E", is_active_p and self.active_endpoint == "end")

        self._draw_hud()

    def _draw_marker(self, screen_pos, color, letter, active) -> None:
        radius = MARKER_RADIUS + (4 if active else 0)
        pygame.draw.circle(self.screen, color, screen_pos, radius)
        pygame.draw.circle(self.screen, (255, 255, 255), screen_pos, radius, 2)
        lbl = self.font.render(letter, True, (0, 0, 0))
        self.screen.blit(lbl, (screen_pos[0] - lbl.get_width() // 2, screen_pos[1] - lbl.get_height() // 2))

    def _draw_hud(self) -> None:
        player = self.players[self.active_player]
        pos = self._endpoint_pos(player, self.active_endpoint)
        lines = [
            "POSITION EDITOR",
            f"Editing: Player {self.active_player + 1}  [{self.active_endpoint.upper()}]"
            f"  ({pos[0]:.0f}, {pos[1]:.0f})",
            "1-4 select  |  Tab start/end  |  drag/arrows move  |  S save  |  R reload  |  F fullscreen  |  Esc quit",
            self.status,
        ]
        y = self.screen.get_height() - (len(lines) * 22) - 10
        panel = pygame.Surface((self.screen.get_width(), len(lines) * 22 + 8), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 160))
        self.screen.blit(panel, (0, y - 4))
        for i, text in enumerate(lines):
            font = self.big_font if i == 0 else self.font
            color = player.color if i == 1 else (235, 235, 245)
            surf = font.render(text, True, color)
            self.screen.blit(surf, (12, y + i * 22))


def run_editor(screen: pygame.Surface, assets: Assets) -> None:
    Editor(screen, assets).run()
