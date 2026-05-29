"""Small upper-left overlay that draws a stick figure per tracked body.

Shows one cell per lane (1-4) so it is immediately obvious whether every player
is being tracked. A lit, coloured figure means tracked; a dim placeholder means
that lane has no body yet.
"""

from __future__ import annotations

from typing import List, Optional

import pygame

import config

# Standard Kinect v2 bone connections (joint index pairs).
BONES = [
    (0, 1), (1, 20), (20, 2), (2, 3),                 # spine + head
    (20, 4), (4, 5), (5, 6), (6, 7), (7, 21), (6, 22),  # left arm
    (20, 8), (8, 9), (9, 10), (10, 11), (11, 23), (10, 24),  # right arm
    (0, 12), (12, 13), (13, 14), (14, 15),            # left leg
    (0, 16), (16, 17), (17, 18), (18, 19),            # right leg
]

DIM_COLOR = (90, 90, 100)


class SkeletonView:
    def __init__(self) -> None:
        self.font = pygame.font.SysFont("consolas", 14)
        self.title_font = pygame.font.SysFont("consolas", 14, bold=True)

    def draw(self, surface: pygame.Surface, skeletons, tracked_count: int) -> None:
        x, y, w, h = config.SKELETON_PANEL_RECT

        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill(config.SKELETON_PANEL_BG)
        surface.blit(panel, (x, y))
        pygame.draw.rect(surface, (200, 200, 210), (x, y, w, h), width=1)

        header = self.title_font.render(
            f"TRACKING  {tracked_count}/{config.NUM_PLAYERS}", True, (235, 235, 245)
        )
        surface.blit(header, (x + 8, y + 5))

        # Map skeletons to lanes.
        by_lane: dict[int, object] = {}
        for skel in skeletons:
            lane = getattr(skel, "lane", None)
            if lane is not None and 0 <= lane < config.NUM_PLAYERS:
                by_lane[lane] = skel

        cell_top = y + 26
        cell_h = h - 34
        cell_w = w / config.NUM_PLAYERS
        for lane in range(config.NUM_PLAYERS):
            cx = x + cell_w * lane
            cell_rect = pygame.Rect(int(cx) + 2, cell_top, int(cell_w) - 4, cell_h)
            self._draw_cell(surface, cell_rect, lane, by_lane.get(lane))

    def _draw_cell(self, surface, rect, lane, skel) -> None:
        color = config.PLAYER_COLORS[lane]
        label = self.font.render(str(lane + 1), True, color if skel else DIM_COLOR)
        surface.blit(label, (rect.x + 2, rect.bottom - 16))

        if skel is None:
            txt = self.font.render("--", True, DIM_COLOR)
            surface.blit(txt, (rect.centerx - 8, rect.centery - 8))
            return

        joints = skel.joints
        tracked = skel.tracked

        # Bounding box of tracked joints in camera space (y is up).
        pts = [j for j, t in zip(joints, tracked) if t]
        if len(pts) < 2:
            return
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1e-3)
        span_y = max(max_y - min_y, 1e-3)

        margin = 8
        avail_w = rect.width - 2 * margin
        avail_h = rect.height - 20 - 2 * margin
        scale = min(avail_w / span_x, avail_h / span_y)
        # Center horizontally; anchor near the top.
        off_x = rect.x + margin + (avail_w - span_x * scale) / 2
        off_y = rect.y + margin

        def project(j):
            px = off_x + (j[0] - min_x) * scale
            # flip Y: camera up -> screen down
            py = off_y + (max_y - j[1]) * scale
            return (int(px), int(py))

        for a, b in BONES:
            if a < len(joints) and b < len(joints) and tracked[a] and tracked[b]:
                pygame.draw.line(surface, color, project(joints[a]), project(joints[b]), 2)
        for j, t in zip(joints, tracked):
            if t:
                pygame.draw.circle(surface, (245, 245, 245), project(j), 2)
