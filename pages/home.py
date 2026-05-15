# pages/home.py
#
# Landing page stub — registers at /.
# Placeholder until the full landing page UI is built (Step 2).

import dash
from dash import html



layout = html.Div(
    "HOME — COMING SOON",
    style={"color": "white", "padding": "40px", "fontFamily": "monospace"},
)

dash.register_page(__name__, path="/", layout=layout)