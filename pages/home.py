# pages/home.py
#
# Landing page — registers at /.
# Layout only — no callbacks. IGNITION navigation via dcc.Link (client-side routing).

import os
import glob

import dash
from dash import html, dcc

from app.config import STATIC_VIDEO_HOST


# Scan carousel images at startup — sorted by filename gives sequence order
_CAROUSEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets', 'carousel')
_CAROUSEL_IMAGES = sorted([
    f"/assets/carousel/{os.path.basename(f)}"
    for f in glob.glob(os.path.join(_CAROUSEL_DIR, '*'))
    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
])


# ── Mission content ───────────────────────────────────────────────────────
# Copy and crew data live here as module-level constants — content, not config.

_DESCRIPTION = (
    "For 54 years, no human had travelled beyond Earth's orbit since Apollo. On April 1st, 2026, NASA's Space Launch "
    "System (SLS) carried Commander Reid Wiseman, Pilot Victor Glover, and Mission Specialists Christina Koch and "
    "Jeremy Hansen further from Earth than any crew in history. Artemis is the bridge between where we've been and "
    "where we're going. Back to the moon."
)

_CREW = [
    {
        "name":       "Reid Wiseman",
        "role":       "Commander",
        "agency":     "NASA",
        "birth":      "November 11, 1975 · Baltimore, MD",
        "flights":    "1 prior mission",
        "time":       "165 days",
        "background": (
            "Naval aviator with over 2,500 flight hours in the F/A-18. BS Electrical Engineering from RPI, "
            "MS Systems Engineering from Johns Hopkins. Selected in NASA's 2009 class. Flew ISS Expedition 40/41 "
            "in 2014, logging 165 days and three EVAs. Served as Chief of the Astronaut Office prior to Artemis II."
        ),
        "portrait":   "portrait-wiseman-reid.webp",
    },
    {
        "name":       "Victor Glover",
        "role":       "Pilot",
        "agency":     "NASA",
        "birth":      "April 30, 1976 · Pomona, CA",
        "flights":    "1 prior mission",
        "time":       "168 days",
        "background": (
            "Naval aviator and test pilot with extensive F/A-18 experience. BS Mechanical Engineering from Cal Poly, "
            "plus graduate degrees in flight test engineering, systems engineering, and leadership. Selected 2013. "
            "Flew Crew Dragon Resilience to ISS in 2020, completing 168 days aboard Expedition 64/65 — the first "
            "Black astronaut to serve a long-duration ISS mission."
        ),
        "portrait":   "portrait-glover-victor.webp",
    },
    {
        "name":       "Christina Koch",
        "role":       "Mission Specialist",
        "agency":     "NASA",
        "birth":      "January 29, 1979 · Grand Rapids, MI",
        "flights":    "1 prior mission",
        "time":       "328 days",
        "background": (
            "Electrical engineer and physicist. BS from NC State. Spent years as a NOAA field engineer in extreme "
            "remote postings including the South Pole. Selected 2013. Her 2019–2020 ISS mission ran 328 days, the "
            "longest single spaceflight by a woman in history. Conducted six EVAs including the first all-female "
            "spacewalk with Jessica Meir."
        ),
        "portrait":   "portrait-koch-christina.webp",
    },
    {
        "name":       "Jeremy Hansen",
        "role":       "Mission Specialist",
        "agency":     "CSA",
        "birth":      "August 27, 1976 · London, Ontario",
        "flights":    "0 prior missions",
        "time":       "0 days",
        "background": (
            "RCAF CF-18 fighter pilot and test pilot. BS Space Science from Royal Military College, MSc Astrophysics "
            "from Western University. Selected by CSA in 2009. Artemis II is his first spaceflight — over fifteen "
            "years of training distilled into one mission. First Canadian to travel beyond Earth orbit."
        ),
        "portrait":   "portrait-hansen-jeremy.webp",
    },
]


# ── Layout ────────────────────────────────────────────────────────────────

layout = html.Div([

    # ── Hero — title + description ─────────────────────────────────────────
    html.Div([
        html.Div([
            html.H1("ARTEMIS II", className="home-title"),
            html.P("CREWED LUNAR FLYBY · APRIL 2026", className="home-title-sub"),
            html.P("IMAGERY · NASA", className="home-title-credit"),
        ], className="home-hero-left"),
        html.Div([
            html.P(_DESCRIPTION, className="home-description"),
        ], className="home-hero-right"),
    ], className="home-hero"),

    html.Div(className="home-spacer"),

    html.Div([
        # ── Media row — video | ignition | carousel ────────────────────────────
        html.Div([

            # Left — launch video
            html.Div([
                html.Span("ARTEMIS II  ✦  LAUNCH", className="home-media-panel-label"),
                html.Video(
                    html.Source(
                        src=f"{STATIC_VIDEO_HOST}/Artemis-2-launch-short-1080.mp4",
                        type="video/mp4",
                    ),
                    controls=True,
                    loop=True,
                    autoPlay=True,
                    muted=True,
                    preload="none",
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
                    "ARTEMIS II  ✦  RECOVERY (FOUR GREEN)",
                    className="home-media-panel-label",
                    id="carousel-panel-label",
                ),

                # Recovery video — plays first, hides on ended
                html.Video(
                    html.Source(
                        src=f"{STATIC_VIDEO_HOST}/artemis-ii-splashdown-recovery-cut.mp4",
                        type="video/mp4",
                    ),
                    id="carousel-video",
                    autoPlay=True,
                    muted=True,
                    controls=False,
                    loop=False,
                    preload="none",
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

                # Controls
                html.Div([
                    html.Button("‹", className="home-carousel-btn", id="carousel-prev"),
                    html.Button("›", className="home-carousel-btn", id="carousel-next"),
                ], id="carousel-controls", className="home-carousel-controls"),

            ], className="home-media-placeholder"),
        ], className="home-media-row"),

        # ── Crew cards ────────────────────────────────────────────────────────
        html.Div([
            html.Div([

                # Portrait — absolute fill, always visible
                html.Img(
                    src=f"/assets/crew/{member['portrait']}",
                    className="home-crew-card-portrait",
                ),

                # Collapsed footer — role + name, hidden when expanded
                html.Div([
                    html.Span(member["role"], className="home-crew-card-role"),
                    html.Span(member["name"], className="home-crew-card-name"),
                ], className="home-crew-card-footer"),

                # Expanded detail — fades in after card grows
                html.Div([
                    html.Span(member["role"],   className="home-crew-detail-role"),
                    html.Span(member["name"],   className="home-crew-detail-name"),
                    html.Span(member["agency"], className="home-crew-detail-agency"),
                    html.Div([
                        html.Span("BORN",          className="home-crew-detail-label"),
                        html.Span(member["birth"], className="home-crew-detail-value"),
                    ], className="home-crew-detail-row"),
                    html.Div([
                        html.Span("PRIOR MISSIONS",  className="home-crew-detail-label"),
                        html.Span(member["flights"], className="home-crew-detail-value"),
                    ], className="home-crew-detail-row"),
                    html.Div([
                        html.Span("TIME IN SPACE", className="home-crew-detail-label"),
                        html.Span(member["time"],  className="home-crew-detail-value"),
                    ], className="home-crew-detail-row"),
                    html.P(member["background"], className="home-crew-detail-bg"),
                ], className="home-crew-card-detail"),

            ], className="home-crew-card", **{"data-card-index": str(i)})
            for i, member in enumerate(_CREW)
        ], className="home-crew-row"),

    ], className="home-media"),

    html.Div(className="home-spacer")

], className="home-root")


dash.register_page(__name__, path="/", layout=layout)