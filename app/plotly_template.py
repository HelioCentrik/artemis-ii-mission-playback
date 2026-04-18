# app/plotly_template.py
#
# Registers the "artemis2" Plotly template at import time. Any module that
# builds a figure just sets template="artemis2" (or gets it automatically
# if we set it as the default). Import this module once at app startup.

import plotly.graph_objects as go
import plotly.io as pio

from app.config import (
    PLOTLY_BG,
    FONT_SIZE_LABEL,
)
from app.themes import THEME_DARK



T = THEME_DARK

# ── Build the template ─────────────────────────────────────────────────

_layout = go.Layout(

    # Transparent — CSS owns the panel background
    paper_bgcolor=PLOTLY_BG,
    plot_bgcolor=PLOTLY_BG,

    # Typography
    font=dict(
        family=T["font_family"],
        color=T["text_dim"],
        size=FONT_SIZE_LABEL,
    ),

    # Margins — tight by default; individual figures override as needed
    margin=dict(l=0, r=0, t=0, b=0, pad=0),

    # X axis defaults
    xaxis=dict(
        showgrid=True,
        gridcolor=T["grid"],
        gridwidth=1,
        zeroline=False,
        linecolor=T["axis_line"],
        linewidth=1,
        tickfont=dict(
            color=T["tick_text"],
            size=FONT_SIZE_LABEL,
        ),
    ),

    # Y axis defaults
    yaxis=dict(
        showgrid=True,
        gridcolor=T["grid"],
        gridwidth=1,
        zeroline=False,
        linecolor=T["axis_line"],
        linewidth=1,
        tickfont=dict(
            color=T["tick_text"],
            size=FONT_SIZE_LABEL,
        ),
    ),

    # Legend
    legend=dict(
        font=dict(color=T["text_dim"], size=FONT_SIZE_LABEL),
        bgcolor=PLOTLY_BG,
        borderwidth=0,
    ),

    # Hover label
    hoverlabel=dict(
        bgcolor=T["panel_bg"],
        bordercolor=T["panel_border"],
        font=dict(
            family=T["font_family"],
            color=T["text"],
            size=FONT_SIZE_LABEL,
        ),
    ),

    # Colorway — panel accent colors as the default trace color cycle.
    # First trace gets vectors teal, second gets trajectory cyan, etc.
    colorway=[
        T["accent"]["vectors"],
        T["accent"]["trajectory"],
        T["accent"]["gravity"],
        T["accent"]["range"],
    ],
)

# ── Register and set as default ────────────────────────────────────────

pio.templates["artemis2"] = go.layout.Template(layout=_layout)
pio.templates.default = "artemis2"