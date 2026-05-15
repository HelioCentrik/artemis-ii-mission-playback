# pages/home.py
#
# Landing page — registers at /.
# Layout only — no callbacks. IGNITION navigation via dcc.Link (client-side routing).

import dash
from dash import html, dcc



# ── Mission content ───────────────────────────────────────────────────────
# Copy and crew data live here as module-level constants — content, not config.
# Bios stored now for expand-on-click (next step), not yet rendered.

_DESCRIPTION = (
    "No human had travelled beyond Earth's orbit for 54 years since Apollo. "
    "On April 1st, 2026, NASA's Space Launch System (SLS) carried Commander Reid Wiseman, "
    "Pilot Victor Glover, and Mission Specialists Christina Koch and Jeremy Hansen further "
    "from Earth than any crew in history. Artemis is the bridge between where we've been "
    "and where we're going. Back to the moon."
)

_CREW = [
    {
        "name": "Reid Wiseman",
        "role": "Commander",
        "bio":  "USN test pilot · ISS Expedition 41 · Selected 2009",
    },
    {
        "name": "Victor Glover",
        "role": "Pilot",
        "bio":  "USN test pilot · ISS Expedition 64 · Selected 2013",
    },
    {
        "name": "Christina Koch",
        "role": "Mission Specialist",
        "bio":  "Engineer · ISS 328-day record mission · Selected 2013",
    },
    {
        "name": "Jeremy Hansen",
        "role": "Mission Specialist",
        "bio":  "RCAF fighter pilot · First Canadian to lunar vicinity · Selected 2009",
    },
]


# ── Layout ────────────────────────────────────────────────────────────────

layout = html.Div([

    # ── Hero — title + description ─────────────────────────────────────────
    html.Div([
        html.H1("ARTEMIS II", className="home-title"),
        html.P("CREWED LUNAR FLYBY · APRIL 2026", className="home-title-sub"),
        html.P(_DESCRIPTION, className="home-description"),
    ], className="home-hero"),

    html.Div([
        # ── Media row — video | ignition | carousel ────────────────────────────
        html.Div([

            # Left — launch video placeholder
            html.Div([
                html.Span(
                    "▶",
                    style={"fontSize": "28px", "color": "var(--font-dim)", "opacity": "0.25"},
                ),
                html.Span("LAUNCH VIDEO", className="home-media-placeholder-label"),
            ], className="home-media-placeholder"),

            # Center — IGNITION navigation button
            html.Div([
                dcc.Link(
                    [html.Span(letter, className="home-ignition-letter") for letter in "IGNITION"],
                    href="/playback/",
                    className="home-ignition-btn",
                ),
            ], className="home-ignition-wrap"),

            # Right — image carousel placeholder
            html.Div([
                html.Span(
                    "⬚",
                    style={"fontSize": "28px", "color": "var(--font-dim)", "opacity": "0.25"},
                ),
                html.Span("IMAGE CAROUSEL", className="home-media-placeholder-label"),
            ], className="home-media-placeholder"),
        ], className="home-media-row"),

        # ── Crew cards ────────────────────────────────────────────────────────
        html.Div([
            html.Div([
                html.Span(member["role"], className="home-crew-card-role"),
                html.Span(member["name"], className="home-crew-card-name"),
            ], className="home-crew-card")
            for member in _CREW
        ], className="home-crew-row"),
    ], className="home-media"),
], className="home-root")


dash.register_page(__name__, path="/", layout=layout)