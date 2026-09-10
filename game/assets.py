"""Asset loading and background <-> screen coordinate mapping.

The whole game reasons about positions in *background space* (the native
4096x1140 pixel grid of the track art). At render time those coordinates are
mapped into the letterboxed rectangle the background occupies inside the
current window. This keeps saved start/end positions valid at any resolution.
"""

from __future__ import annotations

from typing import Tuple

import pygame

import config


class Assets:
    """Loads images and provides background<->screen coordinate transforms."""

    def __init__(self) -> None:
        self.background_raw = pygame.image.load(
            str(config.BACKGROUND_IMAGE)
        ).convert()
        self.bg_native_w, self.bg_native_h = config.BACKGROUND_SIZE

        # Player sprites keep their alpha channel.
        self.player_raw = []
        for path in config.PLAYER_IMAGES:
            surf = pygame.image.load(str(path)).convert_alpha()
            self.player_raw.append(surf)

        # Filled in by recompute_layout().
        self._window_size: Tuple[int, int] = (0, 0)
        self.scale: float = 1.0
        self.offset: Tuple[int, int] = (0, 0)
        self.background_scaled: pygame.Surface | None = None
        self.player_scaled: list[pygame.Surface] = []

    # ------------------------------------------------------------------ #
    # Level switching
    # ------------------------------------------------------------------ #
    def reload_background(self) -> None:
        """Reload the background image and native size from the current config level."""
        self.background_raw = pygame.image.load(
            str(config.BACKGROUND_IMAGE)
        ).convert()
        self.bg_native_w, self.bg_native_h = config.BACKGROUND_SIZE
        # Force recompute on next frame.
        self._window_size = (0, 0)
        self.background_scaled = None

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def recompute_layout(self, window_size: Tuple[int, int]) -> None:
        """Recompute scaling/offset and rescale cached surfaces for a window."""
        if window_size == self._window_size and self.background_scaled is not None:
            return
        self._window_size = window_size
        win_w, win_h = window_size

        # Fit the background inside the window preserving aspect ratio.
        scale = min(win_w / self.bg_native_w, win_h / self.bg_native_h)
        self.scale = scale
        draw_w = max(1, int(round(self.bg_native_w * scale)))
        draw_h = max(1, int(round(self.bg_native_h * scale)))
        self.offset = ((win_w - draw_w) // 2, (win_h - draw_h) // 2)

        self.background_scaled = pygame.transform.smoothscale(
            self.background_raw, (draw_w, draw_h)
        )

        # Rescale each player sprite to a fraction of the track height while
        # preserving its own aspect ratio, then bake a coloured outline version.
        target_h = int(round(self.bg_native_h * config.PLAYER_SPRITE_HEIGHT_FRAC * scale))
        target_h = max(1, target_h)
        outline_px = max(1, int(round(target_h * 0.015)))
        self.player_scaled = []
        for i, surf in enumerate(self.player_raw):
            ratio = surf.get_width() / surf.get_height()
            w = max(1, int(round(target_h * ratio)))
            scaled = pygame.transform.smoothscale(surf, (w, target_h))
            self.player_scaled.append(
                self._make_outlined(scaled, config.PLAYER_COLORS[i], outline_px)
            )

    @staticmethod
    def _make_outlined(sprite: pygame.Surface, color: Tuple[int, ...], thickness: int) -> pygame.Surface:
        """Return a new surface with *sprite* drawn over a coloured outline."""
        w, h = sprite.get_size()
        pad = thickness
        out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)

        # Build a solid-colour silhouette of the sprite.
        silhouette = sprite.copy()
        silhouette.fill((*color[:3], 255), special_flags=pygame.BLEND_RGBA_MIN)
        silhouette.fill((*color[:3], 0), special_flags=pygame.BLEND_RGBA_MAX)

        # Stamp the silhouette at offsets around the centre to form the outline.
        for dx in range(-thickness, thickness + 1):
            for dy in range(-thickness, thickness + 1):
                if dx * dx + dy * dy <= thickness * thickness:
                    out.blit(silhouette, (pad + dx, pad + dy))

        # Draw the original sprite on top.
        out.blit(sprite, (pad, pad))
        return out

    # ------------------------------------------------------------------ #
    # Coordinate transforms
    # ------------------------------------------------------------------ #
    def bg_to_screen(self, pos: Tuple[float, float]) -> Tuple[int, int]:
        ox, oy = self.offset
        return (
            int(round(pos[0] * self.scale + ox)),
            int(round(pos[1] * self.scale + oy)),
        )

    def screen_to_bg(self, pos: Tuple[float, float]) -> Tuple[float, float]:
        ox, oy = self.offset
        if self.scale == 0:
            return (0.0, 0.0)
        return ((pos[0] - ox) / self.scale, (pos[1] - oy) / self.scale)

    # ------------------------------------------------------------------ #
    # Drawing helpers
    # ------------------------------------------------------------------ #
    def draw_background(self, surface: pygame.Surface) -> None:
        surface.fill(config.BACKGROUND_LETTERBOX_COLOR)
        if self.background_scaled is not None:
            surface.blit(self.background_scaled, self.offset)

    def get_player_sprite(self, index: int) -> pygame.Surface:
        return self.player_scaled[index]

    def player_rect_at(self, index: int, screen_pos: Tuple[int, int]) -> pygame.Rect:
        """Rect for a player sprite anchored by its bottom-center (feet/wheel)."""
        rect = self.player_scaled[index].get_rect()
        rect.midbottom = screen_pos
        return rect

    def draw_player(
        self,
        surface: pygame.Surface,
        index: int,
        screen_pos: Tuple[int, int],
        alpha: int = 255,
    ) -> pygame.Rect:
        sprite = self.player_scaled[index]
        rect = sprite.get_rect()
        rect.midbottom = screen_pos
        if alpha < 255:
            sprite = sprite.copy()
            sprite.set_alpha(alpha)
        surface.blit(sprite, rect)
        return rect
