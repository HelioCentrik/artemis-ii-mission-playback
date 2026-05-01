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
    KPI_SVG_VIEWBOX_WIDTH,
    KPI_SVG_VIEWBOX_HEIGHT,
    SPARKLINE_HEIGHT,
    SPARKLINE_PAD_Y,
    SPARKLINE_DOWNSAMPLE_N,
    SPARKLINE_PATH_OPACITY,
    SPARKLINE_PATH_WIDTH,
    SPARKLINE_FUTURE_OPACITY,
    SPARKLINE_STAR_RADIUS,
    SPARKLINE_STAR_GLOW_BLUR,
    # Bar tokens
    BAR_HEIGHT, BAR_BORDER_RADIUS,
    # Bidir tokens
    BIDIR_NEGATIVE_COLOR,
    # Dial tokens
    DIAL_CY_OFFSET, DIAL_RADIUS, DIAL_STROKE_WIDTH, DIAL_STROKE_LINECAP,
    DIAL_ANGLE_MIN, DIAL_ANGLE_MAX, DIAL_VAL_MIN, DIAL_VAL_MAX,
)

# Shared shorthand — used by all builders
_VW = KPI_SVG_VIEWBOX_WIDTH   # 100
_VH = KPI_SVG_VIEWBOX_HEIGHT  # 40


# ── Sparkline ─────────────────────────────────────────────────────────────

def build_sparkline_points(series: list[float]) -> str:
    """
    Normalize a full-mission metric series into an SVG polyline points string.

    X axis : frame index → 0..KPI_SVG_VIEWBOX_WIDTH  (left = mission start)
    Y axis : min–max     → Y_PAD..HEIGHT-Y_PAD        (inverted: high = top)

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
    usable_h     = _VH - 2 * SPARKLINE_PAD_Y

    x_vals = np.linspace(0, _VW, n)
    y_norm = (arr - v_min) / v_range
    y_vals = (_VH - SPARKLINE_PAD_Y) - y_norm * usable_h

    return " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(x_vals, y_vals))


# ── Sparkline ─────────────────────────────────────────────────────────────

def build_sparkline_points(series: list[float]) -> str:
    """
    Normalize a full-mission metric series into an SVG polyline points string.

    X axis : frame index → 0..KPI_SVG_VIEWBOX_WIDTH  (left = mission start)
    Y axis : min–max     → Y_PAD..HEIGHT-Y_PAD        (inverted: high = top)

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
    usable_h     = _VH - 2 * SPARKLINE_PAD_Y

    x_vals = np.linspace(0, _VW, n)
    y_norm = (arr - v_min) / v_range
    y_vals = (_VH - SPARKLINE_PAD_Y) - y_norm * usable_h

    return " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(x_vals, y_vals))


def _parse_sparkline_points(points_str: str) -> list[tuple[float, float]]:
    """Parse 'x1,y1 x2,y2 ...' into a list of (x, y) tuples."""
    pts = []
    for token in points_str.split():
        x, y = token.split(",")
        pts.append((float(x), float(y)))
    return pts


def _approx_path_length(pts: list[tuple[float, float]]) -> float:
    """Euclidean sum of polyline segment lengths — approximates getTotalLength()."""
    total = 0.0
    for i in range(1, len(pts)):
        dx = pts[i][0] - pts[i - 1][0]
        dy = pts[i][1] - pts[i - 1][1]
        total += math.sqrt(dx * dx + dy * dy)
    return total if total > 0 else 9999.0


def _star_and_offset(
    pts: list[tuple[float, float]],
    tlen: float,
    needle_x: float,
) -> tuple[float, float, float]:
    """
    Return (star_cx, star_cy, reveal_len) computed from the same source.

    Finds the point in pts closest to needle_x, accumulates Euclidean path
    length up to that point, and returns it as reveal_len. This matches what
    SVG's getTotalLength()/getPointAtLength() computes for a polyline, so
    dashoffset and star position are derived consistently.

    Using x-fraction (needle_x / _VW * tlen) is wrong when y varies —
    path length is not proportional to x unless the line is horizontal.
    """
    if not pts:
        return needle_x, _VH / 2.0, tlen * needle_x / _VW

    cumlen   = 0.0
    best_idx = 0
    best_dist = abs(pts[0][0] - needle_x)
    cumulative: list[float] = [0.0]

    for i in range(1, len(pts)):
        dx = pts[i][0] - pts[i - 1][0]
        dy = pts[i][1] - pts[i - 1][1]
        cumlen += math.sqrt(dx * dx + dy * dy)
        cumulative.append(cumlen)
        dist = abs(pts[i][0] - needle_x)
        if dist < best_dist:
            best_dist = dist
            best_idx  = i

    return pts[best_idx][0], pts[best_idx][1], cumulative[best_idx]


def build_sparkline_svg(column: str, sparkline_points: str, needle_x: str) -> str:
    """
    Two-polyline sparkline with a traveling star marker.

    Dim polyline  — full path at SPARKLINE_FUTURE_OPACITY; static, no id.
    Bright polyline — same path, stroke-dasharray reveal; id tile-sparkline-past--{col}.
                      JS drives dashoffset each tick via getPointAtLength().
    Star circle   — CSS drop-shadow glow; id tile-star--{col}.
                      Python bakes an approximate initial cx/cy from the points array.
                      JS corrects to exact geometry on the first tick.

    stroke-dasharray/dashoffset survive dcc.Markdown sanitization (kebab-case).
    CSS filter: drop-shadow() in a style attribute also survives.
    No clipPath, no feGaussianBlur — nothing for the sanitizer to mangle.
    """
    nx   = float(needle_x)
    pts  = _parse_sparkline_points(sparkline_points) if sparkline_points else []
    tlen = _approx_path_length(pts)

    star_x, star_y, reveal_len = _star_and_offset(pts, tlen, nx)
    dash_offset = tlen - reveal_len

    glow = f"drop-shadow(0 0 {SPARKLINE_STAR_GLOW_BLUR}px var(--panel-accent))"

    return (
        f'<div style="line-height:0">'
        f'<svg viewBox="0 0 {_VW} {_VH}" '
        f'width="100%" height="100%" '
        f'preserveAspectRatio="none" style="display:block;">'

        # Dim future trace — static, no id
        f'<polyline points="{sparkline_points}" fill="none" '
        f'stroke="var(--panel-accent)" '
        f'stroke-width="{SPARKLINE_PATH_WIDTH}" '
        f'opacity="{SPARKLINE_FUTURE_OPACITY}"/>'

        # Bright past trace — dashoffset derived from cumulative path length
        f'<polyline id="tile-sparkline-past--{column}" '
        f'points="{sparkline_points}" fill="none" '
        f'stroke="var(--panel-accent)" '
        f'stroke-width="{SPARKLINE_PATH_WIDTH}" '
        f'opacity="{SPARKLINE_PATH_OPACITY}" '
        f'stroke-dasharray="{tlen:.1f}" '
        f'stroke-dashoffset="{dash_offset:.1f}"/>'

        # Star — ellipse so JS can correct ry for preserveAspectRatio="none" distortion
        f'<ellipse id="tile-star--{column}" '
        f'cx="{star_x:.1f}" cy="{star_y:.1f}" '
        f'rx="{SPARKLINE_STAR_RADIUS}" ry="{SPARKLINE_STAR_RADIUS}" '
        f'fill="var(--panel-accent)" '
        f'style="filter:{glow};"/>'

        f'</svg></div>'
    )


# ── Standard bar ──────────────────────────────────────────────────────────

def build_bar_svg(
    column:     str,
    value:      float,
    series_min: float,
    series_max: float,
    log_scale:  bool = False,
) -> str:
    """
    Horizontal fill bar, left-anchored.
    log_scale=False : linear 0 → series_max
    log_scale=True  : log10 series_min → series_max (left edge = min, not zero)
    JS target: tile-bar--{column} → width attribute (SVG user units, 0–100).
    """
    by = (_VH - BAR_HEIGHT) / 2

    if log_scale:
        log_min = math.log10(max(series_min, 1e-300))
        log_max = math.log10(max(series_max, 1e-300))
        log_val = math.log10(max(value,      1e-300))
        log_range = max(log_max - log_min, 1e-9)
        fill_w = max(0.0, min(_VW, ((log_val - log_min) / log_range) * _VW))
    else:
        max_val = max(abs(series_max), 1e-9)
        fill_w  = max(0.0, min(_VW, (value / max_val) * _VW))

    return (
        f'<div style="line-height:0">'
        f'<svg viewBox="0 0 {_VW} {_VH}" '
        f'width="100%" height="100%" '
        f'preserveAspectRatio="none" style="display:block;">'

        f'<rect x="0" y="{by:.1f}" width="{_VW}" height="{BAR_HEIGHT}" '
        f'rx="{BAR_BORDER_RADIUS}" '
        f'style="fill:var(--panel-accent);opacity:0.15;"/>'

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
    center:     float = 0.0,
    pos_color:  str = "var(--panel-accent)",
    neg_color:  str = BIDIR_NEGATIVE_COLOR,
    bidir_mid:  float = 0.5,
) -> str:
    """
    Midline-anchored bar. Bar center represents `center` (default 0.0).
    For eccentricity: center=1.0, left=elliptical, right=hyperbolic.
    Deviation is scaled against max departure from center in each direction
    across the full mission series.

    pos_color / neg_color: concrete hex or CSS var for each side's fill.
    Background track is split at the midline so each half mirrors its fill.
    JS target: tile-bidir--{column} → x, width, style.fill attributes.
    """
    by   = (_VH - BAR_HEIGHT) / 2
    mid  = _VW * bidir_mid   # 50.0 — the anchor point

    deviation = value - center
    dev_pos   = max(series_max - center, 1e-9)
    dev_neg   = max(center - series_min, 1e-9)

    right_w = _VW - mid

    if deviation >= 0:
        fill_w     = min((deviation / dev_pos) * right_w, right_w)
        fill_x     = mid
        fill_color = pos_color
    else:
        fill_w     = min((abs(deviation) / dev_neg) * mid, mid)
        fill_x     = mid - fill_w
        fill_color = neg_color

    return (
        f'<div style="line-height:0">'
        f'<svg viewBox="0 0 {_VW} {_VH}" '
        f'width="100%" height="100%" '
        f'preserveAspectRatio="none" style="display:block;">'

        # Background track — split at midline so each half mirrors its fill color
        f'<rect x="0" y="{by:.1f}" width="{mid:.1f}" height="{BAR_HEIGHT}" '
        f'rx="{BAR_BORDER_RADIUS}" '
        f'style="fill:{neg_color};opacity:0.15;"/>'
        f'<rect x="{mid:.1f}" y="{by:.1f}" width="{_VW - mid:.1f}" height="{BAR_HEIGHT}" '
        f'rx="{BAR_BORDER_RADIUS}" '
        f'style="fill:{pos_color};opacity:0.15;"/>'

        # Center tick
        f'<rect x="{mid - 0.5:.1f}" y="{by - 2:.1f}" '
        f'width="1" height="{BAR_HEIGHT + 4}" '
        f'style="fill:var(--panel-accent);opacity:0.55;"/>'

        # Fill — id targeted by JS
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
    Arc gauge sweeping DIAL_ANGLE_MIN → crown → DIAL_ANGLE_MAX.
    DIAL_VAL_MIN maps to leftmost; DIAL_VAL_MAX to rightmost.
    JS target: tile-dial--{column} → d attribute (SVG arc path string).

    cy is computed from the actual angle endpoints so the arc (including
    stroke) stays vertically centered in the viewBox regardless of the
    offset. Formula: cy = (_VH + r + r·sin(ang_max°)) / 2.
    The stroke terms cancel, so this holds for any stroke width.

    preserveAspectRatio="xMidYMid meet" keeps the arc circular.
    """
    r  = DIAL_RADIUS
    sw = DIAL_STROKE_WIDTH
    cx = _VW / 2  # 50 — horizontal center

    ang_min   = float(DIAL_ANGLE_MIN)         # e.g. 170
    ang_max   = float(DIAL_ANGLE_MAX)         # e.g. 10
    ang_range = ang_min - ang_max             # e.g. 160

    # cy: balance stroke-top padding (at crown) and stroke-bottom padding (at endpoints).
    # Endpoints sit at y = cy - r·sin(ang_max°); crown at y = cy - r.
    ang_max_rad = math.radians(ang_max)
    cy = ((_VH + r + r * math.sin(ang_max_rad)) / 2) + DIAL_CY_OFFSET

    val_range = max(DIAL_VAL_MAX - DIAL_VAL_MIN, 1e-9)
    frac      = max(0.0, min(1.0, (value - DIAL_VAL_MIN) / val_range))

    def arc_pt(deg: float) -> tuple[float, float]:
        rad = math.radians(deg)
        return cx + r * math.cos(rad), cy - r * math.sin(rad)

    x0,     y0     = arc_pt(ang_min)                  # left endpoint
    x_full, y_full = arc_pt(ang_max)                  # right endpoint
    curr_deg       = ang_min - frac * ang_range        # frac 0→1 maps to ang_min→ang_max
    x_curr, y_curr = arc_pt(curr_deg)

    # sweep-flag=1 routes upward through 12 o'clock in SVG screen space ✓
    # large-arc-flag=0: ang_range ≤ 180° so the filled arc is always the minor arc
    bg_d = (
        f"M {x0:.2f},{y0:.2f} "
        f"A {r} {r} 0 0 1 {x_full:.2f},{y_full:.2f}"
    )

    if frac < 0.005:
        # Near-zero: degenerate path so the element exists for JS targeting
        fill_d = f"M {x0:.2f},{y0:.2f} L {x0:.2f},{y0:.2f}"
    else:
        fill_d = (
            f"M {x0:.2f},{y0:.2f} "
            f"A {r} {r} 0 0 1 {x_curr:.2f},{y_curr:.2f}"
        )

    return (
        f'<div style="line-height:0">'
        f'<svg viewBox="0 0 {_VW} {_VH}" '
        f'width="100%" height="100%" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'overflow="visible" '
        f'style="display:block;">'

        # Background arc — dim, full sweep
        f'<path d="{bg_d}" fill="none" '
        f'style="stroke:var(--panel-accent);stroke-width:{sw};opacity:0.2;'
        f'stroke-linecap:{DIAL_STROKE_LINECAP};"/>'

        # Filled arc — id targeted by JS
        f'<path id="tile-dial--{column}" d="{fill_d}" fill="none" '
        f'style="stroke:var(--panel-accent);stroke-width:{sw};opacity:0.9;'
        f'stroke-linecap:{DIAL_STROKE_LINECAP};"/>'

        f'</svg></div>'
    )