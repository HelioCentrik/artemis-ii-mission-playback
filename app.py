# app.py
#
# Dash application entry point. Layout structure and callback wiring only.
# Business logic lives in dedicated modules under app/.

import dash
from dash import html, dcc, Input, Output, ctx
from dash.dependencies import ALL

from app.config import PANEL_GROUPS
from app.index_string import INDEX_STRING
from app.trajectory import build_trajectory_fig, build_starfield_svg
from app.phases import get_scrubber_phases, get_phases

# Register the artemis2 Plotly template as a side effect of import
import app.plotly_template  # noqa: F401



# ═══════════════════════════════════════════════════════════════════════════
#  APP INIT
# ═══════════════════════════════════════════════════════════════════════════

app = dash.Dash(
    __name__,
    title="Artemis II · Mission Playback",
    update_title=None,             # don't flash "Updating..." in the tab
    index_string=INDEX_STRING,
)

server = app.server                # for deployment (gunicorn, etc.)


# ═══════════════════════════════════════════════════════════════════════════
#  LAYOUT HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _build_header():
    """Branding bar + status bar."""
    return html.Div([

        # ── Branding bar ──
        html.Div([
            html.Div([
                html.Div("ARTEMIS II : MISSION PLAYBACK", className="header-title"),
            ], className="header-brand-left"),
        ], className="header-brand"),

        # ── Status bar ──
        html.Div([
            html.Div([
                html.Span(className="status-dot"),
                html.Span(
                    "GMT ---:--:--:-- · MET --T --:--:-- · ----:---",
                    id="status-text",
                ),
            ]),
            html.Span("PLAYBACK · 1.0×"),
        ], className="header-status"),

    ])


def _build_scrubber():
    """
    Phase scrubber — horizontal track with clickable phase marker dots.

    Dots are sourced from get_scrubber_phases() and positioned using
    scrubber_pct (0–100, proportional to dataset MET span) rather than
    even spacing. This means the dot positions reflect the real time gaps
    between mission events.
    """
    scrubber_phases = get_scrubber_phases()
    dots = []
    for i, phase in enumerate(scrubber_phases):
        dots.append(
            html.Div(
                # Active class is set dynamically by update_scrubber_dots callback.
                # Index 0 starts active on first load.
                className=f"scrubber-dot{' active' if i == 0 else ''}",
                style={"left": f"{phase['scrubber_pct']:.2f}%"},
                id={"type": "scrubber-dot", "index": i},
                title=phase["label"],
            )
        )
    return html.Div([
        html.Div(dots, className="scrubber-track"),
    ], className="scrubber")


def _build_telemetry_panel(group_key, group):
    """Single telemetry panel with header and placeholder KPI tiles."""
    return html.Div([

        # Panel header — accent dot, label, short code
        html.Div([
            html.Div([
                html.Span(className="accent-dot"),
                html.Span(group["label"]),
            ], className="telemetry-panel-label"),
            html.Span(group["code"], className="telemetry-panel-code"),
        ], className="telemetry-panel-header"),

        # Placeholder tile grid — two empty tiles per panel for now
        html.Div([
            html.Div([
                html.Div([
                    html.Span("---", className="tile-label"),
                    html.Span("---", className="tile-unit"),
                ], className="tile-header"),
                html.Div("--", className="tile-value"),
                html.Div(className="tile-sparkline"),
            ], className="tile"),

            html.Div([
                html.Div([
                    html.Span("---", className="tile-label"),
                    html.Span("---", className="tile-unit"),
                ], className="tile-header"),
                html.Div("--", className="tile-value"),
                html.Div(className="tile-sparkline"),
            ], className="tile"),
        ], className="tile-grid"),

    ], className=f"panel telemetry-panel telemetry-panel--{group_key}")


def _build_telemetry_grid():
    """2×2 grid of telemetry panel groups."""
    return html.Div(
        [_build_telemetry_panel(key, grp) for key, grp in PANEL_GROUPS.items()],
        className="telemetry-grid",
    )


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE LAYOUT
# ═══════════════════════════════════════════════════════════════════════════

app.layout = html.Div([

    # Phase state — scrubber dot index (0-based into get_scrubber_phases()).
    # Scrubber clicks write here; trajectory + telemetry callbacks read it.
    dcc.Store(id="phase-store", data=0),

    # Header
    _build_header(),

    # Trajectory panel
    html.Div([
        html.Div(
            "FDO · TRAJECTORY · ORION / UPPER STAGE · EARTH-MOON",
            className="panel-trajectory-header",
        ),
        html.Div(
            id="trajectory-viz",
            className="panel-trajectory-viz",
        ),
        _build_scrubber(),
    ], className="panel panel-trajectory"),

    # Telemetry panels
    _build_telemetry_grid(),

], className="dashboard")


# ═══════════════════════════════════════════════════════════════════════════
#  CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("phase-store", "data"),
    Input({"type": "scrubber-dot", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def update_phase(n_clicks):
    """Scrubber dot click → write selected scrubber index to phase-store."""
    triggered = ctx.triggered_id
    if triggered is None:
        return 0
    return triggered["index"]


@app.callback(
    Output({"type": "scrubber-dot", "index": ALL}, "className"),
    Input("phase-store", "data"),
)
def update_scrubber_dots(phase_idx):
    """
    Highlight the active scrubber dot and dim the rest.
    Runs on initial load (sets dot 0 active) and on every phase-store change.
    """
    n = len(get_scrubber_phases())
    active = phase_idx or 0
    return [
        "scrubber-dot active" if i == active else "scrubber-dot"
        for i in range(n)
    ]


@app.callback(
    Output("trajectory-viz", "children"),
    Input("phase-store", "data"),
)
def update_trajectory(phase_idx):
    """
    phase-store change → rebuild trajectory figure.

    phase_idx is a scrubber-relative index (0-based into get_scrubber_phases()).
    build_trajectory_fig expects a global index into get_phases(), so we
    resolve via phase key before calling.

    Returns a position:relative wrapper containing two absolute layers:
      1. Static SVG starfield (z=0) — always fills panel edge to edge.
      2. Plotly figure (z=1) — transparent background, trajectory on top.
    """
    scrubber_phases = get_scrubber_phases()
    all_phases      = get_phases()

    scrubber_idx  = phase_idx or 0
    phase_key     = scrubber_phases[scrubber_idx]["key"]
    global_idx    = next(i for i, p in enumerate(all_phases) if p["key"] == phase_key)

    fig = build_trajectory_fig(global_idx)

    return html.Div([
        dcc.Markdown(
            build_starfield_svg(),
            dangerously_allow_html=True,
            style={
                "position": "absolute",
                "inset": "0",
                "zIndex": "0",
                "lineHeight": "0",
            },
        ),
        dcc.Graph(
            figure=fig,
            config=dict(displayModeBar=False),
            style={
                "position": "absolute",
                "inset": "0",
                "height": "100%",
                "zIndex": "1",
            },
        ),
    ], style={"position": "relative", "height": "100%"})


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, port=8050)