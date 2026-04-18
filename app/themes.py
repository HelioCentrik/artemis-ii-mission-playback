# app/themes.py
#
# Theme dictionaries that map semantic roles to color values from config.
# The Plotly template and component builders import from here — not from
# config directly — so the theming layer is swappable in one place.

from app.config import (
    BG_BASE, PANEL_BG, PANEL_BORDER,
    FONT_PRIMARY, FONT_DIM,
    STATUS_LIVE,
    ACCENT_VECTORS, ACCENT_TRAJECTORY, ACCENT_GRAVITY, ACCENT_RANGE,
    COLOR_TRAJECTORY, COLOR_TRAJECTORY_DIM,
    COLOR_EARTH_FILL, COLOR_EARTH_GLOW,
    COLOR_MOON_FILL, COLOR_MOON_GLOW,
    COLOR_STARFIELD, COLOR_SPACECRAFT,
    FONT_FAMILY,
)


THEME_DARK = {

    # ── Surfaces ──
    "bg":           BG_BASE,
    "panel_bg":     PANEL_BG,
    "panel_border": PANEL_BORDER,

    # ── Typography ──
    "text":         FONT_PRIMARY,
    "text_dim":     FONT_DIM,
    "font_family":  FONT_FAMILY,

    # ── Status indicators ──
    "status_live":  STATUS_LIVE,

    # ── Panel group accents ──
    "accent": {
        "vectors":    ACCENT_VECTORS,
        "trajectory": ACCENT_TRAJECTORY,
        "gravity":    ACCENT_GRAVITY,
        "range":      ACCENT_RANGE,
    },

    # ── Plotly axis / grid ──
    "axis_line":    PANEL_BORDER,       # Axis lines match panel border
    "grid":         "#0f1f35",          # Subtle grid — between bg and panel border
    "tick_text":    FONT_DIM,           # Axis tick labels
    "zero_line":    PANEL_BORDER,

    # ── Trajectory viz ──
    "trajectory":       COLOR_TRAJECTORY,
    "trajectory_dim":   COLOR_TRAJECTORY_DIM,
    "earth_fill":       COLOR_EARTH_FILL,
    "earth_glow":       COLOR_EARTH_GLOW,
    "moon_fill":        COLOR_MOON_FILL,
    "moon_glow":        COLOR_MOON_GLOW,
    "starfield":        COLOR_STARFIELD,
    "spacecraft":       COLOR_SPACECRAFT,
}