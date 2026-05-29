"""Kinect v2 body tracking and hip-oscillation accumulation.

Wraps :mod:`pykinect2`. Up to four tracked bodies are assigned to lanes 1-4 by
their ``SpineBase`` X position (left to right). For each body we accumulate the
path length of a weighted Y/Z combination of the ``SpineBase`` joint, which is
what twerking produces, and feed that to the matching player.

If the Kinect runtime, SDK or sensor is unavailable the module reports
``available == False`` so the app can fall back to debug input instead of
crashing.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import config
from game.players import Player

# SpineBase is joint 0 in the Kinect v2 skeleton. We hardcode it so this module
# imports cleanly even when pykinect2 is missing.
JOINT_SPINE_BASE = 0
JOINT_COUNT = 25

try:
    from pykinect2 import PyKinectV2
    from pykinect2 import PyKinectRuntime

    _PYKINECT_IMPORTED = True
except Exception:  # pragma: no cover - depends on Windows + SDK
    PyKinectV2 = None
    PyKinectRuntime = None
    _PYKINECT_IMPORTED = False


class Skeleton:
    """Lightweight per-body snapshot used by the tracking overlay."""

    __slots__ = ("lane", "joints", "tracked")

    def __init__(self, lane: Optional[int]) -> None:
        self.lane = lane
        # camera-space (x, y) per joint, y is up
        self.joints: List[Tuple[float, float]] = []
        self.tracked: List[bool] = []


class KinectInput:
    name = "kinect"

    def __init__(self) -> None:
        self._kinect = None
        self.available = False
        # tracking_id -> previous (x, y, z) of SpineBase, for path length
        self._prev: Dict[int, Tuple[float, float, float]] = {}
        self._skeletons: List[Skeleton] = []
        self._error: Optional[str] = None

        if not _PYKINECT_IMPORTED:
            self._error = "pykinect2 not installed"
            return
        try:
            self._kinect = PyKinectRuntime.PyKinectRuntime(
                PyKinectV2.FrameSourceTypes_Body
            )
            self.available = True
        except Exception as exc:  # pragma: no cover - hardware dependent
            self._error = f"Kinect init failed: {exc}"
            self._kinect = None
            self.available = False

    @property
    def error(self) -> Optional[str]:
        return self._error

    def start(self) -> None:
        pass

    def close(self) -> None:
        if self._kinect is not None:
            try:
                self._kinect.close()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Frame processing
    # ------------------------------------------------------------------ #
    def process_event(self, event, players: List[Player]) -> None:
        # Kinect is polled, not event driven.
        pass

    def update(self, players: List[Player], accumulate: bool = True) -> None:
        # Always poll the sensor so the tracking count and skeleton overlay stay
        # live in every game state; only feed movement into players when
        # ``accumulate`` is True (i.e. during the actual race).
        if not self.available or self._kinect is None:
            return
        if not self._kinect.has_new_body_frame():
            return
        frame = self._kinect.get_last_body_frame()
        if frame is None:
            return

        tracked_bodies = []  # (tracking_id, spine_xyz, body)
        for i in range(self._kinect.max_body_count):
            body = frame.bodies[i]
            if not body.is_tracked:
                continue
            joints = body.joints
            sb = joints[JOINT_SPINE_BASE].Position
            tracked_bodies.append((body.tracking_id, (sb.x, sb.y, sb.z), body))

        # Assign to lanes left -> right by SpineBase X.
        tracked_bodies.sort(key=lambda t: t[1][0])

        live_ids = set()
        self._skeletons = []
        for lane, (tid, spine_xyz, body) in enumerate(tracked_bodies):
            live_ids.add(tid)
            assigned_player = lane if lane < len(players) else None
            player = players[assigned_player] if assigned_player is not None else None
            self._track(tid, spine_xyz, player, accumulate)
            self._skeletons.append(
                self._build_skeleton(body, assigned_player)
            )

        # Drop history for bodies that left the frame.
        for tid in list(self._prev.keys()):
            if tid not in live_ids:
                del self._prev[tid]

    def _track(
        self,
        tid: int,
        spine_xyz: Tuple[float, float, float],
        player: Optional[Player],
        accumulate: bool,
    ) -> None:
        prev = self._prev.get(tid)
        # Always keep history fresh so race movement is continuous from the
        # moment the race starts (no big first-frame jump).
        self._prev[tid] = spine_xyz
        if prev is None or player is None or not accumulate:
            return

        w = config.MOTION_AXIS_WEIGHTS
        dx = (spine_xyz[0] - prev[0]) * w.get("x", 0.0)
        dy = (spine_xyz[1] - prev[1]) * w.get("y", 0.0)
        dz = (spine_xyz[2] - prev[2]) * w.get("z", 0.0)
        delta = math.sqrt(dx * dx + dy * dy + dz * dz)

        if delta < config.MOTION_NOISE_THRESHOLD:
            return
        delta = min(delta, config.MOTION_MAX_FRAME_DELTA)
        player.add_movement(delta * config.MOTION_GAIN)

    def _build_skeleton(self, body, lane: Optional[int]) -> Skeleton:
        skel = Skeleton(lane)
        joints = body.joints
        for j in range(JOINT_COUNT):
            pos = joints[j].Position
            state = joints[j].TrackingState
            skel.joints.append((pos.x, pos.y))
            skel.tracked.append(state != 0)  # 0 == NotTracked
        return skel

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    @property
    def tracked_count(self) -> int:
        return len(self._skeletons)

    def get_skeletons(self) -> List[Skeleton]:
        return self._skeletons
