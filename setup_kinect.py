"""Patch an installed PyKinect2 + comtypes so they import on modern 64-bit Python.

PyKinect2 (last released 2016) targets 32-bit Python <=3.4. On current CPython
it fails to import for three reasons; this script fixes all of them idempotently
so you can re-run it any time you reinstall the packages.

    python setup_kinect.py

Fixes applied:
  1. PyKinectRuntime.py / PyKinectV2.py : time.clock() -> time.perf_counter()
     (time.clock was removed in Python 3.8)
  2. PyKinectV2.py : relax the 32-bit `tagSTATSTG` struct-size asserts, which are
     80/8 on x64 and only used by unused IStream plumbing (not body tracking).
  3. comtypes/_tlib_version_checker.py : early-return from `_check_version` so the
     bundled Kinect.tlb is accepted by newer comtypes.
  4. PyKinectRuntime.py : numpy.object -> object (numpy.object removed in NumPy 1.24+).

This does NOT install the Kinect for Windows SDK 2.0 runtime - that still has to
be installed separately (see README).
"""

from __future__ import annotations

import sys
from pathlib import Path


def _patch_file(path: Path, replacements, marker: str | None = None) -> bool:
    if not path.exists():
        print(f"  skip (missing): {path}")
        return False
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    original = text
    for old, new in replacements:
        text = text.replace(old, new)
    if text == original:
        print(f"  already patched: {path.name}")
        return False
    path.write_text(text, encoding="utf-8", errors="surrogateescape")
    print(f"  patched: {path.name}")
    return True


def main() -> int:
    try:
        import pykinect2
        import comtypes
    except ImportError as exc:
        print(f"Cannot import a package to patch: {exc}")
        print("Run:  pip install pykinect2 comtypes")
        return 1

    pk_dir = Path(pykinect2.__file__).resolve().parent
    ct_dir = Path(comtypes.__file__).resolve().parent

    print("Patching PyKinect2 ...")
    _patch_file(
        pk_dir / "PyKinectRuntime.py",
        [
            ("time.clock()", "time.perf_counter()"),
            ("dtype=numpy.object)", "dtype=object)"),
        ],
    )
    _patch_file(
        pk_dir / "PyKinectV2.py",
        [
            ("time.clock()", "time.perf_counter()"),
            (
                "assert sizeof(tagSTATSTG) == 72, sizeof(tagSTATSTG)",
                "assert sizeof(tagSTATSTG) in (72, 80), sizeof(tagSTATSTG)",
            ),
            (
                "assert alignment(tagSTATSTG) == 8, alignment(tagSTATSTG)",
                "assert alignment(tagSTATSTG) in (4, 8), alignment(tagSTATSTG)",
            ),
        ],
    )

    print("Patching comtypes ...")
    _patch_file(
        ct_dir / "_tlib_version_checker.py",
        [
            (
                "def _check_version(actual, tlib_cached_mtime=None):\n"
                "    from comtypes.tools.codegenerator import version as required",
                "def _check_version(actual, tlib_cached_mtime=None):\n"
                "    return  # patched for PyKinect2: skip strict typelib version match\n"
                "    from comtypes.tools.codegenerator import version as required",
            )
        ],
    )

    print("Verifying import ...")
    try:
        from pykinect2 import PyKinectV2  # noqa: F401
        from pykinect2 import PyKinectRuntime  # noqa: F401
    except Exception as exc:  # pragma: no cover
        print(f"  import still failing: {exc}")
        return 1
    print("  pykinect2 imports successfully.")
    print("\nDone. If a Kinect v2 + SDK runtime is connected, `python main.py` will use it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
