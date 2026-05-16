# components/header.py

from dash import html, dcc


def build_header():
    return html.Div([
        html.Div([
            html.Div([
                dcc.Link(
                    "ARTEMIS II • MISSION PLAYBACK",
                    href="/",
                    className="header-title",
                    title="Return to mission home",
                ),
            ], className="header-brand-left"),
            html.Div([
                html.A(
                    "deanallton.com",
                    href="https://deanallton.com",
                    target="_blank",
                    className="header-credit",
                ),
            ], className="header-brand-right"),
        ], className="header-brand"),
    ])
