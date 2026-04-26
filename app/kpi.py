# app/kpi.py

from __future__ import annotations

from dash import html, dcc

from app.config import SPARKLINE_VIEWBOX_WIDTH
from app.viz_builders import (
    build_sparkline_svg,
    build_bar_svg,
    build_bidir_bar_svg,
    build_dial_svg,
)


def _sub_viz(metric_cfg: dict, column: str, value: float,
             sparkline_points: str, needle_x: str,
             series_stats: dict[str, dict]) -> str | None:
    """
    Return the SVG string for the tile's sub-viz slot, or None for value_only.
    Routing is purely on viz_type — no fallbacks that could silently misrender.
    """
    vt = metric_cfg["viz_type"]

    if vt == "sparkline":
        return build_sparkline_svg(column, sparkline_points, needle_x)

    if vt == "bar":
        stats = series_stats.get(column, {})
        return build_bar_svg(
            column, value,
            stats.get("min", 0.0),
            stats.get("max", 1.0),
            log_scale=metric_cfg.get("log_scale", False),
        )

    if vt == "bidir_bar":
        stats = series_stats.get(column, {})
        return build_bidir_bar_svg(
            column, value,
            stats.get("min", -1.0),
            stats.get("max",  1.0),
        )

    if vt == "dial":
        return build_dial_svg(column, value)

    if vt == "value_only":
        return None

    # Unrecognised viz_type — fail loud during development
    raise ValueError(f"Unknown viz_type {vt!r} for column {column!r}")


def build_kpi_tile(
    metric_cfg:       dict,
    value:            float,
    series_stats:     dict[str, dict],
    sparkline_points: str  = "",
    current_pct:      float = 0.0,
) -> html.Div:
    column    = metric_cfg["column"]
    fmt_value = metric_cfg["fmt"].format(value)
    needle_x  = f"{current_pct:.1f}"

    svg_string = _sub_viz(
        metric_cfg, column, value,
        sparkline_points, needle_x,
        series_stats,
    )

    sub_viz_div = (
        html.Div(
            dcc.Markdown(
                svg_string,
                dangerously_allow_html=True,
                style={"lineHeight": "0", "height": "100%"},
            ),
            className="tile-sparkline",   # same class — CSS slot unchanged
        )
        if svg_string is not None
        else None
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
            sub_viz_div,
        ],
        className="tile",
    )