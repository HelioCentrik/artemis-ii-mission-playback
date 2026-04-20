# app/plotly_template.py
#
# Registers the "artemis2" Plotly template at import time. Any module that
# builds a figure just sets template="artemis2" (or gets it automatically
# if we set it as the default). Import this module once at app startup.

import plotly.graph_objects as go
import plotly.io as pio

from app.config import (
    PLOTLY_BG,
    PANEL_BG, PANEL_BORDER,
    FONT_FAMILY, FONT_PRIMARY, FONT_DIM,
    CHART_GRID_COLOR,
    ACCENT_VECTORS, ACCENT_TRAJECTORY, ACCENT_GRAVITY, ACCENT_RANGE,
    FONT_SIZE_LABEL,
)



_layout = go.Layout(

    paper_bgcolor=PLOTLY_BG,
    plot_bgcolor=PLOTLY_BG,

    font=dict(
        family=FONT_FAMILY,
        color=FONT_DIM,
        size=FONT_SIZE_LABEL,
    ),

    margin=dict(l=0, r=0, t=0, b=0, pad=0),

    xaxis=dict(
        showgrid=True,
        gridcolor=CHART_GRID_COLOR,
        gridwidth=1,
        zeroline=False,
        linecolor=PANEL_BORDER,
        linewidth=1,
        tickfont=dict(color=FONT_DIM, size=FONT_SIZE_LABEL),
    ),

    yaxis=dict(
        showgrid=True,
        gridcolor=CHART_GRID_COLOR,
        gridwidth=1,
        zeroline=False,
        linecolor=PANEL_BORDER,
        linewidth=1,
        tickfont=dict(color=FONT_DIM, size=FONT_SIZE_LABEL),
    ),

    legend=dict(
        font=dict(color=FONT_DIM, size=FONT_SIZE_LABEL),
        bgcolor=PLOTLY_BG,
        borderwidth=0,
    ),

    hoverlabel=dict(
        bgcolor=PANEL_BG,
        bordercolor=PANEL_BORDER,
        font=dict(
            family=FONT_FAMILY,
            color=FONT_PRIMARY,
            size=FONT_SIZE_LABEL,
        ),
    ),

    colorway=[
        ACCENT_VECTORS,
        ACCENT_TRAJECTORY,
        ACCENT_GRAVITY,
        ACCENT_RANGE,
    ],
)

pio.templates["artemis2"] = go.layout.Template(layout=_layout)
pio.templates.default = "artemis2"