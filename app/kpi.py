# app/kpi.py

from __future__ import annotations

from dash import html, dcc

from app.config import (
    SPARKLINE_VIEWBOX_WIDTH,
    SPARKLINE_VIEWBOX_HEIGHT,
    SPARKLINE_HEIGHT,
    SPARKLINE_PATH_OPACITY,
    SPARKLINE_PATH_WIDTH,
    SPARKLINE_NEEDLE_OPACITY,
    SPARKLINE_NEEDLE_WIDTH,
)


def _build_sparkline_svg(
    column:           str,
    sparkline_points: str,
    needle_x:         str,
) -> str:
    vw = SPARKLINE_VIEWBOX_WIDTH
    vh = SPARKLINE_VIEWBOX_HEIGHT

    return (
        f'<div style="line-height:0">'
        f'<svg viewBox="0 0 {vw} {vh}" '          # ← space fixed
        f'width="100%" height="{SPARKLINE_HEIGHT}" '
        f'preserveAspectRatio="none" style="display:block;">'

        f'<polyline points="{sparkline_points}" fill="none" '
        f'style="stroke:var(--panel-accent);stroke-width:{SPARKLINE_PATH_WIDTH};'
        f'opacity:{SPARKLINE_PATH_OPACITY};"/>'

        f'<line id="tile-needle--{column}" '
        f'x1="{needle_x}" y1="0" x2="{needle_x}" y2="{vh}" '
        f'style="stroke:var(--panel-accent);stroke-width:{SPARKLINE_NEEDLE_WIDTH};'
        f'opacity:{SPARKLINE_NEEDLE_OPACITY};"/>'

        f'</svg></div>'
    )


def build_kpi_tile(
    metric_cfg:       dict,
    value:            float,
    sparkline_points: str,
    current_pct:      float,
) -> html.Div:
    column    = metric_cfg["column"]
    fmt_value = metric_cfg["fmt"].format(value)
    needle_x  = f"{current_pct:.1f}"

    svg_string = _build_sparkline_svg(column, sparkline_points, needle_x)

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
            html.Div(
                dcc.Markdown(
                    svg_string,
                    dangerously_allow_html=True,
                    style={"lineHeight": "0", "height": "100%"},
                ),
                className="tile-sparkline",
            ),
        ],
        className="tile",
    )