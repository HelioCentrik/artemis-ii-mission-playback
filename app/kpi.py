# app/kpi.py
#
# KPI tile builder for telemetry panels.
#
# build_kpi_tile() produces a single html.Div using the existing .tile CSS
# classes. Value span and needle line carry stable DOM ids so playback.js
# can update them directly without touching React or Dash callbacks.

from __future__ import annotations

from dash import html

from app.config import (
    SPARKLINE_VIEWBOX_WIDTH,
    SPARKLINE_VIEWBOX_HEIGHT,
    SPARKLINE_PATH_OPACITY,
    SPARKLINE_PATH_WIDTH,
    SPARKLINE_NEEDLE_OPACITY,
    SPARKLINE_NEEDLE_WIDTH,
)


def build_kpi_tile(
    metric_cfg: dict,
    value: float,
    sparkline_points: str,
    current_pct: float,
) -> html.Div:
    """
    Build a single KPI tile Div for a telemetry panel.

    Parameters
    ----------
    metric_cfg : dict
        One metric entry from TELEMETRY_METRICS — keys: column, label,
        unit, fmt, decimals, locale.
    value : float
        Current metric value for server-side formatted display.
    sparkline_points : str
        Pre-built SVG polyline points string from build_sparkline_points().
        Empty string renders a blank sparkline area.
    current_pct : float
        Needle x-position in SVG coordinate space (0–SPARKLINE_VIEWBOX_WIDTH).
        Corresponds to current frame index as a fraction of total frames × width.

    Returns
    -------
    html.Div
        Tile div using .tile CSS classes. Value span and needle line have
        stable DOM ids for direct JS writes during playback:
          tile-val--{column}    → innerHTML  (formatted number string)
          tile-needle--{column} → x1 / x2 attributes (needle position)
    """
    column       = metric_cfg["column"]
    fmt_value    = metric_cfg["fmt"].format(value)
    needle_x     = f"{current_pct:.1f}"

    sparkline = html.Div(
        html.Svg(
            viewBox=f"0 0 {SPARKLINE_VIEWBOX_WIDTH} {SPARKLINE_VIEWBOX_HEIGHT}",
            width="100%",
            height="100%",
            preserveAspectRatio="none",
            style={"display": "block"},
            children=[
                html.Polyline(
                    points=sparkline_points,
                    fill="none",
                    stroke="var(--panel-accent)",
                    strokeWidth=str(SPARKLINE_PATH_WIDTH),
                    opacity=str(SPARKLINE_PATH_OPACITY),
                ),
                html.Line(
                    id=f"tile-needle--{column}",
                    x1=needle_x,
                    y1="0",
                    x2=needle_x,
                    y2=str(SPARKLINE_VIEWBOX_HEIGHT),
                    stroke="var(--panel-accent)",
                    strokeWidth=str(SPARKLINE_NEEDLE_WIDTH),
                    opacity=str(SPARKLINE_NEEDLE_OPACITY),
                ),
            ],
        ),
        className="tile-sparkline",
    )

    return html.Div(
        [
            html.Div(
                [
                    html.Span(metric_cfg["label"], className="tile-label"),
                    html.Span(metric_cfg["unit"],  className="tile-unit"),
                ],
                className="tile-header",
            ),
            html.Span(
                fmt_value,
                id=f"tile-val--{column}",
                className="tile-value",
            ),
            sparkline,
        ],
        className="tile",
    )