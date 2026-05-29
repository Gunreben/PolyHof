"""PolyHof - Butt Race: entry point.

Usage:
    python main.py            Run the full game (Kinect v2; falls back to debug
                              keys 1-4 if no sensor is available).
    python main.py --debug    Force keyboard debug input (keys 1/2/3/4).
    python main.py --editor    Interactive start/end position editor.
"""

from __future__ import annotations

import argparse
import sys

import pygame

import config
from game.assets import Assets


def _create_screen() -> pygame.Surface:
    flags = pygame.RESIZABLE
    if config.START_FULLSCREEN:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    return pygame.display.set_mode(config.WINDOW_SIZE, flags)


def _make_source(force_debug: bool):
    from game.input_debug import DebugInput

    if force_debug:
        print("[input] Debug mode: advance players with keys 1 / 2 / 3 / 4.")
        return DebugInput()

    from game.kinect_input import KinectInput

    kinect = KinectInput()
    if kinect.available:
        print("[input] Kinect v2 connected. Twerk to move.")
        return kinect

    print(f"[input] Kinect unavailable ({kinect.error}); falling back to debug keys 1-4.")
    return DebugInput()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="PolyHof - Butt Race")
    parser.add_argument("--editor", action="store_true", help="run the position editor")
    parser.add_argument("--debug", action="store_true", help="force keyboard debug input")
    args = parser.parse_args(argv)

    pygame.init()
    pygame.display.set_caption("PolyHof - Butt Race")
    screen = _create_screen()
    assets = Assets()
    assets.recompute_layout(screen.get_size())

    if args.editor:
        from game.editor import run_editor

        run_editor(screen, assets)
        pygame.quit()
        return 0

    from game.app import Game

    source = _make_source(force_debug=args.debug)
    Game(screen, assets, source).run()
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
