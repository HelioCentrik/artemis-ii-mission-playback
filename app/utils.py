# app/utils.py
#
# Stdlib-only utility helpers shared across the app.
# No Dash, Plotly, DuckDB, or app-module imports here.

import colorsys

import numpy as np



# ═════════════════════════════════════════════════════════════════════════
#  Geometry
# ═════════════════════════════════════════════════════════════════════════

def rotate_2d(x, y, angle_rad: float):
    """
    Apply a 2D counter-clockwise rotation by angle_rad.
    Accepts scalars or NumPy arrays for x and y.
    Returns (x_rotated, y_rotated).
    """
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return x * c - y * s, x * s + y * c


def circle_xy(cx: float, cy: float, r: float, n: int = 120):
    """
    Parametric circle centered at (cx, cy) with radius r.
    Returns (x_array, y_array) of length n, closed (start == end).
    """
    t = np.linspace(0, 2 * np.pi, n)
    return cx + r * np.cos(t), cy + r * np.sin(t)


# ═════════════════════════════════════════════════════════════════════════
#  Formatting
# ═════════════════════════════════════════════════════════════════════════

def fmt_met(total_seconds: int) -> str:
    """
    Format mission elapsed time as 'DDT HH:MM'.
    Example: 345_600 seconds → '04T 00:00'
    """
    d, rem = divmod(int(total_seconds), 86_400)
    h, rem = divmod(rem, 3_600)
    m = rem // 60
    return f"{d:02d}T {h:02d}:{m:02d}"


def fmt_met_long(total_seconds: int) -> str:
    """
    Format mission elapsed time as 'DDT HH:MM:SS'.
    """
    d, rem = divmod(int(total_seconds), 86_400)
    h, rem = divmod(rem, 3_600)
    m, s = divmod(rem, 60)
    return f"{d:02d}T {h:02d}:{m:02d}:{s:02d}"


# ═════════════════════════════════════════════════════════════════════════
#  Bounds checking
# ═════════════════════════════════════════════════════════════════════════

def in_range(value: float, lo: float, hi: float, margin: float = 0.0) -> bool:
    """Return True if value falls within [lo − margin, hi + margin]."""
    return (lo - margin) <= value <= (hi + margin)


# ═════════════════════════════════════════════════════════════════════════
#  Color helpers
# ═════════════════════════════════════════════════════════════════════════

def hex_to_rgb(hex_color: str) -> str:
    """
    Convert a '#rrggbb' hex string to an 'R,G,B' string.
    Used by config.py to derive rgba() component strings from theme hex values.

    Example: hex_to_rgb('#5082b4') → '80,130,180'
    """
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"

def hsl_rotate(hex_str: str, degrees: float) -> str:
    """Rotate the hue of a hex color by `degrees` (0–360). Returns hex."""
    h = hex_str.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    hue, lum, sat = colorsys.rgb_to_hls(r, g, b)   # note: colorsys is HLS not HSL
    hue = (hue + degrees / 360.0) % 1.0
    r2, g2, b2 = colorsys.hls_to_rgb(hue, lum, sat)
    return "#{:02x}{:02x}{:02x}".format(int(r2 * 255), int(g2 * 255), int(b2 * 255))
