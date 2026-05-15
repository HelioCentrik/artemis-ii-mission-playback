# components/header.py

from dash import html


def build_header():
    return html.Div([
        html.Div([
            html.Div([
                html.Div("ARTEMIS II • MISSION PLAYBACK", className="header-title"),
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
