"""Game states: TITLE -> COUNTDOWN -> RACE -> FINISH.

Each state implements ``handle_event`` / ``update`` / ``draw`` and asks the
owning :class:`~game.app.Game` to transition with ``game.set_state(...)``.
"""

from __future__ import annotations

import math
from typing import List

import pygame

import config


class State:
    # When True, the active input source feeds hip movement into players this
    # frame. Only the race counts; other states still track/visualise bodies.
    accumulate_movement = False

    def __init__(self, game) -> None:
        self.game = game

    def enter(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        pass


# --------------------------------------------------------------------------- #
# TITLE
# --------------------------------------------------------------------------- #
class TitleState(State):
    AUTO_START_HOLD = 1.5  # seconds with all players tracked before auto-start

    def enter(self) -> None:
        self.t = 0.0
        self.all_tracked_for = 0.0
        for p in self.game.players:
            p.reset()

    def _start(self) -> None:
        self.game.set_state(CountdownState(self.game))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self._start()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._start()

    def update(self, dt: float) -> None:
        self.t += dt
        if config.MANUAL_MODE:
            return
        if self.game.source.tracked_count >= config.NUM_PLAYERS:
            self.all_tracked_for += dt
            if self.all_tracked_for >= self.AUTO_START_HOLD:
                self._start()
        else:
            self.all_tracked_for = 0.0

    def draw(self, surface: pygame.Surface) -> None:
        self.game.assets.draw_background(surface)
        # Dark vignette to make text pop.
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, (0, 0))

        cx = surface.get_width() // 2
        pulse = 1.0 + 0.05 * math.sin(self.t * 4.0)
        title = self.game.fonts["title"].render("PolyHof", True, (240, 210, 60))
        sub = self.game.fonts["title"].render("BUTT RACE", True, (235, 64, 52))
        title = pygame.transform.rotozoom(title, 0, pulse)
        sub = pygame.transform.rotozoom(sub, 0, pulse)
        surface.blit(title, (cx - title.get_width() // 2, int(surface.get_height() * 0.18)))
        surface.blit(sub, (cx - sub.get_width() // 2, int(surface.get_height() * 0.18) + title.get_height()))

        tagline = self.game.fonts["medium"].render(
            "Twerk to win - Butt Race Day 2026", True, (235, 235, 245)
        )
        surface.blit(tagline, (cx - tagline.get_width() // 2, int(surface.get_height() * 0.55)))

        tracked = self.game.source.tracked_count
        track_color = (88, 214, 96) if tracked >= config.NUM_PLAYERS else (240, 196, 32)
        status = self.game.fonts["medium"].render(
            f"Players tracked: {tracked}/{config.NUM_PLAYERS}  ({self.game.source.name})",
            True,
            track_color,
        )
        surface.blit(status, (cx - status.get_width() // 2, int(surface.get_height() * 0.68)))

        if not config.MANUAL_MODE and (self.t * 2) % 2 < 1.4:  # blinking prompt
            prompt = self.game.fonts["medium"].render(
                "Press SPACE to start", True, (255, 255, 255)
            )
            surface.blit(prompt, (cx - prompt.get_width() // 2, int(surface.get_height() * 0.82)))

        # Live tracking overlay so players can see they are detected before the
        # race even starts.
        self.game.skeleton_view.draw(
            surface, self.game.source.get_skeletons(), self.game.source.tracked_count
        )


# --------------------------------------------------------------------------- #
# COUNTDOWN
# --------------------------------------------------------------------------- #
class CountdownState(State):
    STEPS = ["3", "2", "1", "GO!"]
    STEP_TIME = 0.8

    def enter(self) -> None:
        self.t = 0.0
        for p in self.game.players:
            p.reset()

    def update(self, dt: float) -> None:
        self.t += dt
        if self.t >= self.STEP_TIME * len(self.STEPS):
            self.game.set_state(RaceState(self.game))

    def draw(self, surface: pygame.Surface) -> None:
        self.game.draw_race_scene(surface, show_progress=False)

        idx = min(int(self.t / self.STEP_TIME), len(self.STEPS) - 1)
        local = (self.t / self.STEP_TIME) - idx  # 0..1 within this step
        scale = 1.6 - 0.6 * local  # shrink as it settles
        text = self.STEPS[idx]
        color = (88, 214, 96) if text == "GO!" else (255, 255, 255)
        glyph = self.game.fonts["huge"].render(text, True, color)
        glyph = pygame.transform.rotozoom(glyph, 0, max(0.2, scale))
        cx = surface.get_width() // 2
        cy = surface.get_height() // 2
        surface.blit(glyph, (cx - glyph.get_width() // 2, cy - glyph.get_height() // 2))


# --------------------------------------------------------------------------- #
# RACE
# --------------------------------------------------------------------------- #
class RaceState(State):
    accumulate_movement = True

    def enter(self) -> None:
        self._finish_counter = 0

    def handle_event(self, event: pygame.event.Event) -> None:
        # Movement input (debug keys) only counts during the race.
        self.game.source.process_event(event, self.game.players)

    def update(self, dt: float) -> None:
        for p in self.game.players:
            if not p.finished and p.progress >= 1.0:
                p.finished = True
                self._finish_counter += 1
                p.finish_order = self._finish_counter
        if any(p.finished for p in self.game.players):
            self.game.set_state(FinishState(self.game))

    def draw(self, surface: pygame.Surface) -> None:
        self.game.draw_race_scene(surface, show_progress=True)


# --------------------------------------------------------------------------- #
# FINISH
# --------------------------------------------------------------------------- #
class FinishState(State):
    def enter(self) -> None:
        self.t = 0.0
        winners = [p for p in self.game.players if p.finish_order == 1]
        self.winner = winners[0] if winners else max(
            self.game.players, key=lambda p: p.progress
        )

    def _next_round(self) -> None:
        self.game.advance_level()
        self.game.set_state(TitleState(self.game))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self._next_round()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._next_round()

    def update(self, dt: float) -> None:
        self.t += dt
        if not config.MANUAL_MODE and self.t >= config.WINNER_DISPLAY_TIME:
            self._next_round()

    def draw(self, surface: pygame.Surface) -> None:
        self.game.draw_race_scene(surface, show_progress=True)
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        cx = surface.get_width() // 2
        pulse = 1.0 + 0.08 * math.sin(self.t * 6.0)
        text = f"PLAYER {self.winner.index + 1} WINS!"
        glyph = self.game.fonts["huge"].render(text, True, self.winner.color)
        glyph = pygame.transform.rotozoom(glyph, 0, pulse)
        surface.blit(glyph, (cx - glyph.get_width() // 2, int(surface.get_height() * 0.30)))

        # Countdown to next level.
        next_level = (config.CURRENT_LEVEL + 1) % config.NUM_LEVELS + 1
        if not config.MANUAL_MODE:
            remaining = max(0, config.WINNER_DISPLAY_TIME - self.t)
            prompt_text = f"Next track in {remaining:.0f}s  |  SPACE to skip  |  Esc to quit"
            prompt = self.game.fonts["medium"].render(prompt_text, True, (255, 255, 255))
            surface.blit(prompt, (cx - prompt.get_width() // 2, int(surface.get_height() * 0.72)))
