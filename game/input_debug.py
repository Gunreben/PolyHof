"""Keyboard debug input: advance players by tapping 1 / 2 / 3 / 4.

Lets the whole game be tested without a Kinect attached. Each key press adds
``config.DEBUG_INCREMENT`` to the matching player's accumulated movement, so
"twerking" becomes "mashing your number key".
"""

from __future__ import annotations

from typing import List

import pygame

import config
from game.players import Player


class DebugInput:
    name = "debug"

    # Map pygame key codes (both number row and numpad) to a player index.
    KEY_TO_PLAYER = {
        pygame.K_1: 0,
        pygame.K_2: 1,
        pygame.K_3: 2,
        pygame.K_4: 3,
        pygame.K_KP1: 0,
        pygame.K_KP2: 1,
        pygame.K_KP3: 2,
        pygame.K_KP4: 3,
    }

    def __init__(self) -> None:
        self.available = True

    def start(self) -> None:  # symmetry with KinectInput
        pass

    def close(self) -> None:
        pass

    def process_event(self, event: pygame.event.Event, players: List[Player]) -> None:
        if event.type != pygame.KEYDOWN:
            return
        idx = self.KEY_TO_PLAYER.get(event.key)
        if idx is not None and idx < len(players):
            players[idx].add_movement(config.DEBUG_INCREMENT)

    def update(self, players: List[Player]) -> None:  # nothing polled per frame
        pass

    @property
    def tracked_count(self) -> int:
        # In debug mode we pretend all players are "tracked" so the start gate
        # logic can proceed.
        return config.NUM_PLAYERS

    def get_skeletons(self):
        return []
