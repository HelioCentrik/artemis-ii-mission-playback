# app/viz_builders.py
#
# SVG viz builders for KPI tiles.
#
# build_sparkline_points()  — normalize full-mission series → polyline points string
# build_sparkline_svg()     — sparkline + needle SVG string
# build_bar_svg()           — standard horizontal fill bar
# build_bidir_bar_svg()     — midline-anchored bi-directional bar
# build_dial_svg()          — semicircle arc gauge

from __future__ import annotations

import math

import numpy as np

from app.config import (
    # Sparkline tokens
    SPARKLINE_VIEWBOX_WIDTH,
    SPARKLINE_VIEWBOX_HEIGHT,
    SPARKLINE_HEIGHT,
    SPARKLINE_Y_PAD,
    SPARKLINE_DOWNSAMPLE_N,
    SPARKLINE_PATH_OPACITY,
    SPARKLINE_PATH_WIDTH,
    SPARKLINE_NEEDLE_OPACITY,
    SPARKLINE_NEEDLE_WIDTH,
    # Bar tokens
    BAR_HEIGHT,
    BAR_BORDER_RADIUS,
    # Bidir tokens
    BIDIR_NEGATIVE_COLOR,
    # Dial tokens
    DIAL_RADIUS,
    DIAL_STROKE_WIDTH,
    DIAL_VAL_MIN,
    DIAL_VAL_MAX,
)

# Shared shorthand — used by all builders
_VW = SPARKLINE_VIEWBOX_WIDTH   # 100
_VH = SPARKLINE_VIEWBOX_HEIGHT  # 40


# ── Sparkline ─────────────────────────────────────────────────────────────

def build_sparkline_points(series: list[float]) -> str:
    """
    Normalize a full-mission metric series into an SVG polyline points string.

    X axis : frame index → 0..SPARKLINE_VIEWBOX_WIDTH  (left = mission start)
    Y axis : min–max     → Y_PAD..HEIGHT-Y_PAD          (inverted: high = top)

    Downsamples to SPARKLINE_DOWNSAMPLE_N evenly-spaced frames to keep
    the SVG payload small without visible loss of fidelity.
    """
    if not series:
        return ""

    arr = np.array(series, dtype=float)

    n       = min(SPARKLINE_DOWNSAMPLE_N, len(arr))
    indices = np.linspace(0, len(arr) - 1, n, dtype=int)
    arr     = arr[indices]

    v_min, v_max = arr.min(), arr.max()
    v_range      = v_max - v_min if v_max != v_min else 1.0
    usable_h     = _VH - 2 * SPARKLINE_Y_PAD

    x_vals = np.linspace(0, _VW, n)
    y_norm = (arr - v_min) / v_range
    y_vals = (_VH - SPARKLINE_Y_PAD) - y_norm * usable_h

    return " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(x_vals, y_vals))


def build_sparkline_svg(column: str, sparkline_points: str, needle_x: str) -> str:
    return (
        f'<div style="line-height:0">'
        f'<svg viewBox="0 0 {_VW} {_VH}" '
        f'width="100%" height="{SPARKLINE_HEIGHT}" '
        f'preserveAspectRatio="none" style="display:block;">'

        f'<polyline points="{sparkline_points}" fill="none" '
        f'style="stroke:var(--panel-accent);stroke-width:{SPARKLINE_PATH_WIDTH};'
        f'opacity:{SPARKLINE_PATH_OPACITY};"/>'

        f'<line id="tile-needle--{column}" '
        f'x1="{needle_x}" y1="0" x2="{needle_x}" y2="{_VH}" '
        f'style="stroke:var(--panel-accent);stroke-width:{SPARKLINE_NEEDLE_WIDTH};'
        f'opacity:{SPARKLINE_NEEDLE_OPACITY};"/>'

        f'</svg></div>'
    )


# ── Standard bar ──────────────────────────────────────────────────────────

def build_bar_svg(column: str, value: float, series_max: float) -> str:
    """
    Horizontal fill bar, left-anchored, 0 → series_max range.
    JS target: tile-bar--{column} → width attribute (SVG user units, 0–100).
    """
    by      = (_VH - BAR_HEIGHT) / 2          # vertical center
    max_val = max(abs(series_max), 1e-9)
    fill_w  = max(0.0, min(_VW, (value / max_val) * _VW))

    return (
        f'<div style="line-height:0">'
        f'<svg viewBox="0 0 {_VW} {_VH}" '
        f'width="100%" height="{SPARKLINE_HEIGHT}" '
        f'preserveAspectRatio="none" style="display:block;">'

        # Background track
        f'<rect x="0" y="{by:.1f}" width="{_VW}" height="{BAR_HEIGHT}" '
        f'rx="{BAR_BORDER_RADIUS}" '
        f'style="fill:var(--panel-accent);opacity:0.15;"/>'

        # Fill — id targeted by JS
        f'<rect id="tile-bar--{column}" '
        f'x="0" y="{by:.1f}" width="{fill_w:.2f}" height="{BAR_HEIGHT}" '
        f'rx="{BAR_BORDER_RADIUS}" '
        f'style="fill:var(--panel-accent);opacity:0.9;"/>'

        f'</svg></div>'
    )


# ── Bi-directional bar ────────────────────────────────────────────────────

def build_bidir_bar_svg(
    column:     str,
    value:      float,
    series_min: float,
    series_max: float,
) -> str:
    """
    Midline-anchored bar. Positive → accent color, fills right.
    Negative → BIDIR_NEGATIVE_COLOR, fills left.
    JS target: tile-bidir--{column} → x, width, style.fill attributes.
    """
    by   = (_VH - BAR_HEIGHT) / 2
    mid  = _VW / 2   # 50.0 — the anchor point

    pos_max = max(abs(series_max), 1e-9)
    neg_max = max(abs(series_min), 1e-9)

    if value >= 0:
        fill_w     = min((value / pos_max) * mid, mid)
        fill_x     = mid
        fill_color = "var(--panel-accent)"
    else:
        fill_w     = min((abs(value) / neg_max) * mid, mid)
        fill_x     = mid - fill_w
        fill_color = BIDIR_NEGATIVE_COLOR

    return (
        f'<div style="line-height:0">'
        f'<svg viewBox="0 0 {_VW} {_VH}" '
        f'width="100%" height="{SPARKLINE_HEIGHT}" '
        f'preserveAspectRatio="none" style="display:block;">'

        # Background track
        f'<rect x="0" y="{by:.1f}" width="{_VW}" height="{BAR_HEIGHT}" '
        f'rx="{BAR_BORDER_RADIUS}" '
        f'style="fill:var(--panel-accent);opacity:0.15;"/>'

        # Center tick — slightly taller than the bar so it reads as a midline
        f'<rect x="{mid - 0.5:.1f}" y="{by - 2:.1f}" '
        f'width="1" height="{BAR_HEIGHT + 4}" '
        f'style="fill:var(--panel-accent);opacity:0.55;"/>'

        # Fill — id targeted by JS (updates x, width, fill)
        f'<rect id="tile-bidir--{column}" '
        f'x="{fill_x:.2f}" y="{by:.1f}" '
        f'width="{fill_w:.2f}" height="{BAR_HEIGHT}" '
        f'rx="{BAR_BORDER_RADIUS}" '
        f'style="fill:{fill_color};opacity:0.9;"/>'

        f'</svg></div>'
    )


# ── Dial ──────────────────────────────────────────────────────────────────

def build_dial_svg(column: str, value: float) -> str:
    """
    Semicircle arc gauge. Sweeps 9 o'clock → 12 o'clock → 3 o'clock.
    DIAL_VAL_MIN maps to leftmost position; DIAL_VAL_MAX to rightmost.
    JS target: tile-dial--{column} → d attribute (SVG arc path string).

    preserveAspectRatio="xMidYMid meet" keeps the arc circular — "none"
    would squash it into an oval as the tile width varies.
    """
    r  = DIAL_RADIUS
    sw = DIAL_STROKE_WIDTH
    cx = _VW / 2           # 50 — horizontal center
    cy = _VH * 0.82        # ~33 — low enough that arc crown clears the top

    val_range = max(DIAL_VAL_MAX - DIAL_VAL_MIN, 1e-9)
    frac      = max(0.0, min(1.0, (value - DIAL_VAL_MIN) / val_range))

    # Angle: 180° at frac=0 (9 o'clock), 0° at frac=1 (3 o'clock), through 90° (top).
    # y = cy - r*sin(θ) because SVG y increases downward.
    def arc_pt(deg: float) -> tuple[float, float]:
        rad = math.radians(deg)
        return cx + r * math.cos(rad), cy - r * math.sin(rad)

    x0, y0       = arc_pt(180)                          # leftmost (always start)
    x_full, y_full = arc_pt(0)                          # rightmost (full fill end)
    curr_deg     = 180.0 - frac * 180.0
    x_curr, y_curr = arc_pt(curr_deg)

    # sweep-flag=0 → counterclockwise in SVG screen space → routes through top ✓
    bg_d = (
        f"M {x0:.2f},{y0:.2f} "
        f"A {r} {r} 0 0 0 {x_full:.2f},{y_full:.2f}"
    )

    if frac < 0.005:
        # Near-zero: emit a degenerate move so the element exists for JS targeting
        fill_d = f"M {x0:.2f},{y0:.2f} L {x0:.2f},{y0:.2f}"
    else:
        fill_d = (
            f"M {x0:.2f},{y0:.2f} "
            f"A {r} {r} 0 0 0 {x_curr:.2f},{y_curr:.2f}"
        )

    return (
        f'<div style="line-height:0">'
        f'<svg viewBox="0 0 {_VW} {_VH}" '
        f'width="100%" height="{SPARKLINE_HEIGHT}" '
        f'preserveAspectRatio="xMidYMid meet" style="display:block;">'

        # Background arc — dim, full sweep
        f'<path d="{bg_d}" fill="none" '
        f'style="stroke:var(--panel-accent);stroke-width:{sw};opacity:0.2;'
        f'stroke-linecap:round;"/>'

        # Filled arc — id targeted by JS
        f'<path id="tile-dial--{column}" d="{fill_d}" fill="none" '
        f'style="stroke:var(--panel-accent);stroke-width:{sw};opacity:0.9;'
        f'stroke-linecap:round;"/>'

        f'</svg></div>'
    )