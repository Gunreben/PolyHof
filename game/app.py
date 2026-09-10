"""Game orchestration: window, input source, state machine, shared rendering."""

from __future__ import annotations

from typing import List

import pygame

import config
from game.assets import Assets
from game.players import Player, load_players
from game.skeleton_view import SkeletonView
from game.states import State, TitleState


class Game:
    def __init__(self, screen: pygame.Surface, assets: Assets, source) -> None:
        self.screen = screen
        self.assets = assets
        self.source = source
        self.players: List[Player] = load_players()
        self.skeleton_view = SkeletonView()
        self.fullscreen = config.START_FULLSCREEN
        self.running = True

        self.fonts = {
            "huge": pygame.font.SysFont("impact,arialblack,sans", 96),
            "title": pygame.font.SysFont("impact,arialblack,sans", 64),
            "medium": pygame.font.SysFont("consolas", 24),
            "small": pygame.font.SysFont("consolas", 16),
        }

        self.state: State = TitleState(self)
        self.state.enter()

    # ------------------------------------------------------------------ #
    def advance_level(self) -> None:
        """Switch to the next level (cycling), reload background and positions."""
        next_level = (config.CURRENT_LEVEL + 1) % config.NUM_LEVELS
        config.set_level(next_level)
        self.assets.reload_background()
        self.players = load_players()

    # ------------------------------------------------------------------ #
    def set_state(self, state: State) -> None:
        self.state = state
        self.state.enter()

    # ------------------------------------------------------------------ #
    def run(self) -> None:
        clock = pygame.time.Clock()
        self.source.start()
        try:
            while self.running:
                dt = clock.tick(config.FPS) / 1000.0
                for event in pygame.event.get():
                    self._handle_global_event(event)
                    if self.running:
                        self.state.handle_event(event)
                if not self.running:
                    break
                self.assets.recompute_layout(self.screen.get_size())
                # Poll tracking every frame in every state so the skeleton
                # overlay and "players tracked" count stay live; only the race
                # state lets that motion advance the horses.
                self.source.update(
                    self.players, accumulate=self.state.accumulate_movement
                )
                self.state.update(dt)
                self.state.draw(self.screen)
                pygame.display.flip()
        finally:
            self.source.close()

    def _handle_global_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
            self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key == pygame.K_f:
                self._toggle_fullscreen()

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
    # Shared rendering used by several states
    # ------------------------------------------------------------------ #
    def draw_race_scene(self, surface: pygame.Surface, show_progress: bool) -> None:
        self.assets.draw_background(surface)

        # Draw horses back-to-front (smaller y = farther away = behind).
        for p in sorted(self.players, key=lambda pl: pl.current_pos()[1]):
            screen_pos = self.assets.bg_to_screen(p.current_pos())
            self.assets.draw_player(surface, p.index, screen_pos)

        if show_progress:
            self._draw_progress(surface)

        self.skeleton_view.draw(
            surface, self.source.get_skeletons(), self.source.tracked_count
        )

    def _draw_progress(self, surface: pygame.Surface) -> None:
        panel_x, panel_y, panel_w, _ = config.SKELETON_PANEL_RECT
        x = panel_x + panel_w + 20
        y = panel_y
        bar_w = 240
        bar_h = 22
        gap = 10
        for p in self.players:
            label = self.fonts["small"].render(f"P{p.index + 1}", True, p.color)
            surface.blit(label, (x, y + 2))
            bx = x + 30
            pygame.draw.rect(surface, (30, 30, 36), (bx, y, bar_w, bar_h), border_radius=4)
            fill_w = int(bar_w * p.progress)
            if fill_w > 0:
                pygame.draw.rect(surface, p.color, (bx, y, fill_w, bar_h), border_radius=4)
            pygame.draw.rect(surface, (210, 210, 220), (bx, y, bar_w, bar_h), width=1, border_radius=4)
            pct = self.fonts["small"].render(f"{int(p.progress * 100):3d}%", True, (235, 235, 245))
            surface.blit(pct, (bx + bar_w + 8, y + 2))
            if p.finished:
                flag = self.fonts["small"].render("FINISH!", True, (88, 214, 96))
                surface.blit(flag, (bx + bar_w + 60, y + 2))
            y += bar_h + gap
