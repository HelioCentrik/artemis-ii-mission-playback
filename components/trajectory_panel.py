# components/trajectory_panel.py

from dash import html, dcc

from app.config import PLAYBACK_SPEED_LABEL
from viz.trajectory import build_starfield_svg


def build_trajectory_content(fig) -> html.Div:
    """
    Starfield SVG (z=0) + Plotly graph (z=1) + HUD overlay (z=2)
    inside a relative container.

    dcc.Graph gets id="trajectory-graph" so the clientside frame-update
    callback can locate it via document.getElementById. React reconciles
    the graph in-place when the figure prop changes (same id = no teardown).
    Pointer-events disabled — the scrubber overlay handles all clicks.
    """
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
            id="trajectory-graph",
            figure=fig,
            config=dict(displayModeBar=False),
            style={
                "position": "absolute",
                "inset": "0",
                "height": "100%",
                "zIndex": "1",
                "pointerEvents": "none",
            },
        ),
        # ── HUD overlay — GMT · MET · Phase · Playback rate ──────────────
        html.Div([
            html.Div([
                html.Span(className="status-dot"),
                html.Span(
                    "GMT ---:--:--:-- · MET --T --:--:-- · ----:---",
                    id="status-text",
                ),
            ], className="traj-hud-left"),
            html.Span(PLAYBACK_SPEED_LABEL, className="traj-hud-right"),
        ], className="traj-hud-overlay"),
    ], style={"position": "relative", "height": "100%"})
