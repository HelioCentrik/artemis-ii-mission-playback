# app/utils.py
#
# Stdlib-only utility helpers shared across the app.
# No Dash, Plotly, DuckDB, or app-module imports here.

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