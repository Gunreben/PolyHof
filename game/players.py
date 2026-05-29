"""Player model plus start/end position persistence.

A player travels along the straight line between ``start_pos`` and ``end_pos``
(both in background space). Forward progress is driven by ``accumulated``
movement coming from whichever input source is active (Kinect or debug keys),
normalised against a shared ``target`` so everyone must move the same amount.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Tuple

import config


def _default_positions() -> List[dict]:
    """Sensible starting layout: a column at the gate, finish near the right.

    These are only used until the user places real positions with the editor.
    They spread the four lanes vertically across the lower half of the track.
    """
    bw, bh = config.BACKGROUND_SIZE
    positions = []
    for i in range(config.NUM_PLAYERS):
        # Lanes stacked vertically in the lower portion of the track.
        y = bh * (0.55 + 0.10 * i)
        positions.append(
            {
                "start": [bw * 0.10, y],
                "end": [bw * 0.88, y],
            }
        )
    return positions


@dataclass
class Player:
    index: int
    start_pos: List[float]
    end_pos: List[float]
    accumulated: float = 0.0
    target: float = field(default_factory=lambda: config.TARGET_MOVEMENT)
    finished: bool = False
    finish_order: int = 0  # 1 = first to finish, 0 = not finished

    @property
    def progress(self) -> float:
        if self.target <= 0:
            return 0.0
        return min(1.0, self.accumulated / self.target)

    @property
    def color(self) -> Tuple[int, int, int]:
        return config.PLAYER_COLORS[self.index]

    def current_pos(self) -> Tuple[float, float]:
        """Interpolated position in background space based on progress."""
        t = self.progress
        x = self.start_pos[0] + (self.end_pos[0] - self.start_pos[0]) * t
        y = self.start_pos[1] + (self.end_pos[1] - self.start_pos[1]) * t
        return (x, y)

    def add_movement(self, amount: float) -> None:
        if amount <= 0:
            return
        self.accumulated += amount

    def reset(self) -> None:
        self.accumulated = 0.0
        self.finished = False
        self.finish_order = 0


def load_players() -> List[Player]:
    """Load players from POSITIONS_FILE, falling back to defaults."""
    data = None
    if config.POSITIONS_FILE.exists():
        try:
            with open(config.POSITIONS_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            data = None

    if not data or not isinstance(data, list) or len(data) < config.NUM_PLAYERS:
        data = _default_positions()

    players: List[Player] = []
    for i in range(config.NUM_PLAYERS):
        entry = data[i]
        players.append(
            Player(
                index=i,
                start_pos=[float(entry["start"][0]), float(entry["start"][1])],
                end_pos=[float(entry["end"][0]), float(entry["end"][1])],
            )
        )
    return players


def save_players(players: List[Player]) -> None:
    """Persist start/end positions of every player to POSITIONS_FILE."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = [
        {
            "start": [p.start_pos[0], p.start_pos[1]],
            "end": [p.end_pos[0], p.end_pos[1]],
        }
        for p in players
    ]
    with open(config.POSITIONS_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
