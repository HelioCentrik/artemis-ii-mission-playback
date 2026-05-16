# pages/home.py
#
# Landing page — registers at /.
# Layout only — no callbacks. IGNITION navigation via dcc.Link (client-side routing).

import os
import glob

import dash
from dash import html, dcc



# Scan carousel images at startup — sorted by filename gives sequence order
_CAROUSEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets', 'carousel')
_CAROUSEL_IMAGES = sorted([
    f"/assets/carousel/{os.path.basename(f)}"
    for f in glob.glob(os.path.join(_CAROUSEL_DIR, '*'))
    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
])


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
        html.Div([
            html.H1("ARTEMIS II", className="home-title"),
            html.P("CREWED LUNAR FLYBY · APRIL 2026", className="home-title-sub"),
        ], className="home-hero-left"),
        html.Div([
            html.P(_DESCRIPTION, className="home-description"),
        ], className="home-hero-right"),
    ], className="home-hero"),

    html.Div(className="home-spacer"),

    html.Div([
        # ── Media row — video | ignition | carousel ────────────────────────────
        html.Div([

            # Left — launch video placeholder
            html.Div([
                html.Span("ARTEMIS II  •  LAUNCH", className="home-media-panel-label"),
                html.Video(
                    html.Source(src="/assets/video/Artemis-2-launch-short-1080.mp4", type="video/mp4"),
                    controls=True,
                    loop=True,
                    autoPlay=True,
                    muted=True,
                    className="home-launch-video",
                ),
            ], className="home-media-placeholder"),

            # Center — IGNITION navigation button
            html.Div([
                dcc.Link(
                    [html.Span(letter, className="home-ignition-letter") for letter in "IGNITION"],
                    href="/playback/",
                    className="home-ignition-btn",
                ),
            ], className="home-ignition-wrap"),

            # Right — splashdown video → image carousel
            html.Div([
                html.Span(
                    "ARTEMIS II  ✦  SPLASHDOWN & RECOVERY",
                    className="home-media-panel-label",
                    id="carousel-panel-label",
                ),

                # Recovery video — plays first, hides on ended
                html.Video(
                    html.Source(
                        src="/assets/video/artemis-ii-splashdown-recovery-cut.mp4",
                        type="video/mp4",
                    ),
                    id="carousel-video",
                    autoPlay=True,
                    muted=True,
                    controls=False,
                    loop=False,
                    className="home-carousel-video",
                ),

                # Images — all in DOM, JS cycles active class
                html.Div([
                    html.Img(
                        src=src,
                        className="home-carousel-img active" if i == 0 else "home-carousel-img",
                        **{"data-index": str(i)},
                    )
                    for i, src in enumerate(_CAROUSEL_IMAGES)
                ], id="carousel-imgs", className="home-carousel-imgs"),

                # Controls — hidden until video ends
                html.Div([
                    html.Button("‹", className="home-carousel-btn", id="carousel-prev"),
                    html.Div([
                        html.Span(
                            className="home-carousel-dot active" if i == 0 else "home-carousel-dot",
                            **{"data-index": str(i)},
                        )
                        for i in range(len(_CAROUSEL_IMAGES))
                    ], className="home-carousel-dots"),
                    html.Button("›", className="home-carousel-btn", id="carousel-next"),
                ], id="carousel-controls", className="home-carousel-controls"),

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

    html.Div(className="home-spacer")

], className="home-root")


dash.register_page(__name__, path="/", layout=layout)