# components/scrubber.py

from dash import html

from app.phases import get_scrubber_phases


def build_scrubber():
    scrubber_phases = get_scrubber_phases()
    dots = []
    for i, phase in enumerate(scrubber_phases):
        dots.append(
            html.Div(
                className=f"scrubber-dot{' active' if i == 0 else ''}",
                style={"left": f"{phase['scrubber_pct']:.2f}%"},
                id={"type": "scrubber-dot", "index": i},
                title=phase["label"],
            )
        )
    return html.Div([
        html.Div("▶", id="playback-btn", className="playback-btn"),
        html.Div([
            *dots,
            html.Div(id="scrubber-seek-indicator", className="scrubber-seek-indicator"),
        ], className="scrubber-track"),
    ], className="scrubber")
