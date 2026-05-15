# components/telemetry_panel.py

from dash import html

from app.config import TELEMETRY_METRICS, PANEL_GROUPS
from viz.kpi import build_kpi_tile


def build_telemetry_panel(
    group_key:           str,
    group:               dict,
    values_dict:         dict | None = None,
    current_pct:         float       = 0.0,
    series_stats:        dict        = {},
    sparkline_points_map: dict       = {},
) -> html.Div:
    """
    Build one telemetry panel with 3 KPI tiles.

    values_dict          : {column: float} from get_telemetry_at(); None → stub tiles
    current_pct          : SVG x-coord for sparkline needle (0–KPI_SVG_VIEWBOX_WIDTH)
    series_stats         : {column: {min, max}} for bar/bidir range scaling
    sparkline_points_map : {column: points_str} precomputed polyline points
    """
    if values_dict is None:
        stub_tile = html.Div([
            html.Div([
                html.Span("---", className="tile-label"),
                html.Span("---", className="tile-unit"),
            ], className="tile-header"),
            html.Span("--", className="tile-value"),
            html.Div(className="tile-sparkline"),
        ], className="tile")

        tiles = [stub_tile, stub_tile, stub_tile]

    else:
        tiles = [
            build_kpi_tile(
                metric_cfg       = m,
                value            = values_dict.get(m["column"], 0.0),
                series_stats     = series_stats,
                sparkline_points = sparkline_points_map.get(m["column"], ""),
                current_pct      = current_pct,
            )
            for m in TELEMETRY_METRICS[group_key]
        ]

    return html.Div([
        html.Div([
            html.Div([
                html.Span(className="accent-dot"),
                html.Span(group["label"]),
            ], className="telemetry-panel-label"),
            html.Span(group["code"], className="telemetry-panel-code"),
        ], className="telemetry-panel-header"),
        html.Div(tiles, className="tile-grid"),
    ], className=f"panel telemetry-panel telemetry-panel--{group_key}")


def build_telemetry_grid() -> html.Div:
    return html.Div(
        id="telemetry-grid",
        className="telemetry-grid",
        children=[
            build_telemetry_panel(key, grp)
            for key, grp in PANEL_GROUPS.items()
        ],
    )
