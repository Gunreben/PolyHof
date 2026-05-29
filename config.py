"""Central configuration for PolyHof - Butt Race.

All tunable gameplay, display and Kinect parameters live here so the game can be
calibrated for a venue without touching the rest of the code.
"""

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT_DIR = Path(__file__).resolve().parent
IMAGES_DIR = ROOT_DIR / "images"
DATA_DIR = ROOT_DIR / "data"
POSITIONS_FILE = DATA_DIR / "positions.json"

BACKGROUND_IMAGE = IMAGES_DIR / "Background_1.png"
# Player 4 ships with an uppercase extension; keep the exact names here.
PLAYER_IMAGES = [
    IMAGES_DIR / "Player_1.png",
    IMAGES_DIR / "Player_2.png",
    IMAGES_DIR / "Player_3.png",
    IMAGES_DIR / "Player_4.PNG",
]

NUM_PLAYERS = 4

# --------------------------------------------------------------------------- #
# Background / coordinate space
# --------------------------------------------------------------------------- #
# Native size of the background art. All saved positions are expressed in this
# coordinate space so they are independent of the runtime window resolution.
BACKGROUND_SIZE = (4096, 1140)

# --------------------------------------------------------------------------- #
# Display
# --------------------------------------------------------------------------- #
# Default windowed size. The background aspect (~3.59:1) is preserved and the
# image is letterboxed inside whatever window/monitor we render to.
WINDOW_SIZE = (1280, 357)
START_FULLSCREEN = False
FPS = 60
BACKGROUND_LETTERBOX_COLOR = (12, 10, 14)

# Visual scale of the player sprites relative to the background height.
# 1.0 would draw a sprite as tall as the whole background; the horses should be
# a fraction of the track height.
PLAYER_SPRITE_HEIGHT_FRAC = 0.42

# --------------------------------------------------------------------------- #
# Gameplay
# --------------------------------------------------------------------------- #
# Total accumulated hip movement (in the abstract unit produced by the active
# input source) required to travel from start_pos to end_pos. Same for everyone.
TARGET_MOVEMENT = 100.0

# How much a single debug key press (1/2/3/4) contributes towards the target.
DEBUG_INCREMENT = 1.5

# --------------------------------------------------------------------------- #
# Kinect motion analysis
# --------------------------------------------------------------------------- #
# The hip oscillation signal is built from the SpineBase joint. We accumulate
# the path length of a weighted combination of the vertical (Y, up/down) and
# depth (Z, toward/away from the sensor) components. Twerking shows up strongly
# on both, so the default mixes them.
MOTION_AXIS_WEIGHTS = {"x": 0.0, "y": 1.0, "z": 1.0}

# Per-frame joint delta (in metres) below this is treated as sensor noise and
# ignored, so a perfectly still player does not creep forward.
MOTION_NOISE_THRESHOLD = 0.004

# Scales raw accumulated metres into the abstract movement unit used by
# TARGET_MOVEMENT. Larger == players reach the finish with less effort.
MOTION_GAIN = 90.0

# Maximum metres counted from a single frame delta. Guards against tracking
# glitches (a body jumping across the frame) adding a huge burst of progress.
MOTION_MAX_FRAME_DELTA = 0.20

# --------------------------------------------------------------------------- #
# Skeleton overlay (upper-left tracking panel)
# --------------------------------------------------------------------------- #
SKELETON_PANEL_RECT = (16, 16, 300, 220)  # x, y, w, h in window pixels
SKELETON_PANEL_BG = (0, 0, 0, 150)

# --------------------------------------------------------------------------- #
# Theme colours (per player, used for labels / skeleton tint / progress bars)
# --------------------------------------------------------------------------- #
PLAYER_COLORS = [
    (235, 64, 52),    # P1 red
    (52, 168, 235),   # P2 blue
    (88, 214, 96),    # P3 green
    (240, 196, 32),   # P4 yellow
]
