# PolyHof - Butt Race

A 4-player party game: each player rides a horse-on-a-unicycle down a derelict
racetrack by **twerking**. A Kinect v2 tracks every player's hips; the up/down
and back/forth hip oscillation is accumulated, and the first horse to bounce its
way to the `FINISH` line wins. Everyone has to move the same total amount, so
it's a pure stamina battle.

```
TITLE  ->  COUNTDOWN (3-2-1-GO)  ->  RACE  ->  WINNER
```

## Features

- Interactive **position editor** to place each horse's start (the gate) and end
  (the finish) positions, saved to `data/positions.json`.
- **Debug mode**: play/test with no hardware by tapping keys `1` `2` `3` `4`.
- **Kinect v2** hip-oscillation tracking with per-player accumulation.
- Animated startup sequence and a **skeleton tracking overlay** (upper-left) so
  it's obvious all four players are being tracked.

## Install

Python 3.8+ recommended.

```bash
pip install -r requirements.txt
```

`pygame` and `numpy` are all you need for the editor and debug mode (any OS).
The Kinect-only packages (`pykinect2`, `comtypes`) install on Windows only.

### Kinect v2 setup (Windows)

1. Install the [Kinect for Windows SDK 2.0](https://www.microsoft.com/en-us/download/details.aspx?id=44561).
2. Plug the sensor (with the Kinect Adapter for Windows) into a **USB 3.0** port.
3. `pip install pykinect2 comtypes`
4. Run the one-time patch helper:

   ```bash
   python setup_kinect.py
   ```

PyKinect2 (released 2016) targets 32-bit Python <=3.4 and won't import on modern
64-bit CPython without three small fixes. `setup_kinect.py` applies them
idempotently (re-run it after any reinstall):

- `time.clock()` -> `time.perf_counter()` in the PyKinect2 sources (removed in
  Python 3.8).
- Relax the 32-bit `tagSTATSTG` struct-size asserts in `PyKinectV2.py` (they are
  80/8 on x64 and only used by unused IStream plumbing, not body tracking).
- Early-return from `comtypes/_tlib_version_checker.py::_check_version` so the
  bundled `Kinect.tlb` is accepted by newer comtypes.

If the SDK/sensor isn't found, the game prints a notice and automatically falls
back to debug keys, so you can still develop without hardware.

## Run

```bash
# Place and save start/end positions for each player
python main.py --editor

# Race using keyboard input (no Kinect needed) - tap 1/2/3/4
python main.py --debug

# Full game with the Kinect v2
python main.py
```

### Global keys (game)

| Key     | Action                          |
|---------|---------------------------------|
| `Space` | Start race / race again         |
| `1`-`4` | (debug) advance that player     |
| `F`     | Toggle fullscreen               |
| `Esc`   | Quit                            |

### Editor keys

| Key          | Action                                       |
|--------------|----------------------------------------------|
| `1`-`4`      | Select player                                |
| `Tab`        | Toggle editing START vs END                  |
| Mouse drag   | Move nearest / active marker                 |
| Arrow keys   | Nudge active marker 1px (`Shift` = 10px)     |
| `S`          | Save to `data/positions.json`                |
| `R`          | Reload from disk                             |
| `F`          | Toggle fullscreen                            |
| `Esc` / `Q`  | Quit editor                                  |

## Tuning (`config.py`)

All gameplay/sensor parameters live in `config.py`:

- `TARGET_MOVEMENT` - total accumulated movement needed to win (same for all).
- `DEBUG_INCREMENT` - progress added per debug key press.
- `MOTION_AXIS_WEIGHTS` - how much hip `x`/`y`/`z` motion counts (default mixes
  vertical `y` and depth `z`, which is what twerking produces).
- `MOTION_NOISE_THRESHOLD` - ignore jitter below this per-frame metre delta.
- `MOTION_GAIN` - converts metres of hip travel into progress (higher = easier).
- `MOTION_MAX_FRAME_DELTA` - clamp glitchy tracking jumps.
- `PLAYER_SPRITE_HEIGHT_FRAC` - horse size relative to the track height.
- `WINDOW_SIZE` / `START_FULLSCREEN` - display setup.

## How tracking maps to players

Up to four tracked bodies are assigned to lanes 1-4 by their `SpineBase` X
position (left to right in front of the sensor). Each body's hip path length is
accumulated independently and drives its horse from `start_pos` to `end_pos`.

## Project layout

```
PolyHof/
  main.py                 entry point + arg parsing
  config.py               all tunable parameters
  data/positions.json     saved start/end positions (edited by --editor)
  images/                 background + 4 player sprites
  game/
    assets.py             image loading + bg<->screen coordinate mapping
    players.py            Player model + positions load/save
    editor.py             interactive position editor
    input_debug.py        keyboard 1/2/3/4 input source
    kinect_input.py       Kinect v2 body tracking + hip accumulation
    skeleton_view.py      upper-left tracking overlay
    states.py             TITLE / COUNTDOWN / RACE / FINISH
    app.py                main loop + shared rendering
```
