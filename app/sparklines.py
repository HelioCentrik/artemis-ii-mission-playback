# app/sparklines.py
#
# SVG sparkline path builder for KPI tiles.
#
# build_sparkline_points() is called once per metric at startup and the
# result is stored in the preload store. The SVG itself is rendered by
# kpi.py — this module only produces the points string.

from __future__ import annotations

import numpy as np

from app.config import (
    SPARKLINE_VIEWBOX_WIDTH,
    SPARKLINE_VIEWBOX_HEIGHT,
    SPARKLINE_Y_PAD,
    SPARKLINE_DOWNSAMPLE_N,
)


def build_sparkline_points(series: list[float]) -> str:
    """
    Normalize a full-mission metric series into an SVG polyline points string.

    X axis : frame index → 0..SPARKLINE_VIEWBOX_WIDTH  (left = mission start)
    Y axis : min–max     → Y_PAD..HEIGHT-Y_PAD          (inverted: high = top)

    Downsamples to SPARKLINE_DOWNSAMPLE_N evenly-spaced frames to keep
    the SVG payload small without visible loss of fidelity.

    Parameters
    ----------
    series : list[float]
        Raw metric values in chronological order (12,836 frames).

    Returns
    -------
    str
        SVG polyline points attribute value, e.g. "0.0,38.2 0.5,37.1 ..."
        Empty string if series is empty or all-null.
    """
    if not series:
        return ""

    arr = np.array(series, dtype=float)

    # Downsample — evenly spaced indices across the full series
    n       = min(SPARKLINE_DOWNSAMPLE_N, len(arr))
    indices = np.linspace(0, len(arr) - 1, n, dtype=int)
    arr     = arr[indices]

    # Guard: all-same values produce a flat line (avoid divide-by-zero)
    v_min, v_max = arr.min(), arr.max()
    v_range      = v_max - v_min if v_max != v_min else 1.0

    usable_h = SPARKLINE_VIEWBOX_HEIGHT - 2 * SPARKLINE_Y_PAD

    # Normalize
    x_vals = np.linspace(0, SPARKLINE_VIEWBOX_WIDTH,  n)
    y_norm = (arr - v_min) / v_range              # 0.0 (min) → 1.0 (max)
    y_vals = (SPARKLINE_VIEWBOX_HEIGHT - SPARKLINE_Y_PAD) - y_norm * usable_h
    # ↑ inverted: 1.0 (max value) → Y_PAD (top of SVG)

    return " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(x_vals, y_vals))