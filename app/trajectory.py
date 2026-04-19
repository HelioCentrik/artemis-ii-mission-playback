# app/trajectory.py
#
# build_trajectory_fig(phase_idx) — 2D top-down Earth–Moon trajectory viz.
#
# Camera model: fixed viewport across all phases, driven by constants in
# config.py (VIEW_ROTATION_DEG, VIEW_ZOOM, VIEW_X/Y_OFFSET_KM).
# Geometry helpers live in utils.py. This module is figure logic only.
#
# Equal-scale (circles not ovals):
#   xaxis uses scaleanchor="y" with no explicit range. Plotly derives
#   xaxis range = container_pixel_width / pixel_height × y_span.
#
# View stability:
#   An invisible 2-point anchor trace at fixed x bounds is added to every
#   figure. This forces Plotly to center on the same x midpoint regardless
#   of which Moon/trajectory traces are present at each phase.
#   Stars are scattered across those same fixed x bounds so they always
#   fill whatever width Plotly computes for the panel.

import numpy as np
import plotly.graph_objects as go

from app.config import (
    PLOTLY_BG,
    COLOR_TRAJECTORY,
    COLOR_TRAJECTORY_DIM,
    COLOR_SPACECRAFT,
    FONT_SIZE_LABEL,
    VIEW_ROTATION_DEG,
    VIEW_ZOOM,
    VIEW_X_OFFSET_KM,
    VIEW_Y_OFFSET_KM,
    STAR_SEED,
    STAR_COUNT,
)
from app.themes import THEME_DARK
from app.utils import rotate_2d, circle_xy, fmt_met, in_range
from app.db import get_con
from app.phases import get_phases


# ── Module-level caches ───────────────────────────────────────────────────
_BODY_RADII:   dict | None = None
_FIXED_RANGES: dict | None = None

# How far the anchor trace extends in x, expressed as a multiple of y_half.
# 2.8 comfortably covers a 2.5:1 panel at any window width.
_X_ANCHOR_RATIO = 2.8


# ═════════════════════════════════════════════════════════════════════════
#  Trace helpers
# ═════════════════════════════════════════════════════════════════════════

def _filled(cx, cy, r, rgba, n=120):
    xs, ys = circle_xy(cx, cy, r, n)
    return go.Scatter(
        x=xs, y=ys, mode="lines",
        fill="toself", fillcolor=rgba,
        line=dict(color="rgba(0,0,0,0)", width=0),
        hoverinfo="skip", showlegend=False,
    )


def _line(xs, ys, color, width, dash=None):
    ld = dict(color=color, width=width)
    if dash:
        ld["dash"] = dash
    return go.Scatter(
        x=xs, y=ys, mode="lines", line=ld,
        hoverinfo="skip", showlegend=False,
    )


# ═════════════════════════════════════════════════════════════════════════
#  Startup caches
# ═════════════════════════════════════════════════════════════════════════

def _get_body_radii() -> dict:
    """
    Earth fill = 65% of min(rg_km) so trajectory always clears the body.
    Moon fill  = Earth fill × real Moon/Earth radius ratio (0.2727).
    All glow layers are multiples of their fill radii.
    Cached after first call.
    """
    global _BODY_RADII
    if _BODY_RADII is not None:
        return _BODY_RADII
    con = get_con()
    row = con.execute("SELECT MIN(rg_km) FROM orion_trajectory").fetchone()
    er = float(row[0]) * 0.65
    mr = er * (1_737.4 / 6_371.0)
    _BODY_RADII = dict(
        ER=er,  EG2=er*1.45, EG3=er*2.1, EG4=er*3.1, EG5=er*4.5,
        MR=mr,  MG2=mr*1.625, MG3=mr*2.75, MG4=mr*4.5,
    )
    return _BODY_RADII


def _get_fixed_ranges() -> dict:
    """
    Compute the fixed viewport, anchor bounds, and starfield once from
    the full mission. Cached after first call — never recomputes.

    Keys returned:
        y_range       — [y_lo, y_hi] passed to yaxis.range
        x_center      — midpoint of the x anchor; Plotly centers on this
        x_half        — half-width of the anchor extent (y_half × ratio)
        y_half        — half-height of y_range (handy for callers)
        star_x/y      — fixed star positions (data-space)
        star_sz       — per-star sizes
        star_colors   — per-star rgba strings
    """
    global _FIXED_RANGES
    if _FIXED_RANGES is not None:
        return _FIXED_RANGES

    con = get_con()
    a = np.radians(VIEW_ROTATION_DEG)

    orion = con.execute("SELECT x_km, y_km FROM orion_trajectory").df()
    tx, ty = rotate_2d(orion["x_km"].values, orion["y_km"].values, a)

    moon = con.execute("SELECT m_x_km, m_y_km FROM v_earth_moon").df()
    mx_all, my_all = rotate_2d(moon["m_x_km"].values, moon["m_y_km"].values, a)

    all_x = np.concatenate([tx, mx_all, [0.0]])
    all_y = np.concatenate([ty, my_all, [0.0]])

    xc     = (all_x.max() + all_x.min()) / 2 + VIEW_X_OFFSET_KM
    yc     = (all_y.max() + all_y.min()) / 2 + VIEW_Y_OFFSET_KM
    x_half = (all_x.max() - all_x.min()) / 2 * VIEW_ZOOM
    y_half = (all_y.max() - all_y.min()) / 2 * VIEW_ZOOM

    y_range = [yc - y_half, yc + y_half]

    # Anchor x bounds — stars fill this same span
    anchor_half = y_half * _X_ANCHOR_RATIO

    rng    = np.random.default_rng(STAR_SEED)
    star_x = rng.uniform(xc - anchor_half, xc + anchor_half, STAR_COUNT)
    star_y = rng.uniform(y_range[0], y_range[1], STAR_COUNT)

    n_dim = int(STAR_COUNT * 0.79)
    n_fg  = STAR_COUNT - n_dim
    sz = np.concatenate([rng.uniform(0.5, 1.2, n_dim), rng.uniform(1.2, 2.0, n_fg)])
    sa = np.concatenate([rng.uniform(0.12, 0.35, n_dim), rng.uniform(0.45, 0.75, n_fg)])

    _FIXED_RANGES = dict(
        y_range=y_range,
        y_half=y_half,
        x_center=xc,
        x_half=anchor_half,
        star_x=star_x,
        star_y=star_y,
        star_sz=sz,
        star_colors=[f"rgba(255,255,255,{v:.2f})" for v in sa],
    )
    return _FIXED_RANGES


# ═════════════════════════════════════════════════════════════════════════
#  Main builder
# ═════════════════════════════════════════════════════════════════════════

def build_trajectory_fig(phase_idx: int) -> go.Figure:
    """
    2D Earth–Moon trajectory figure for the given phase index (0–4).
    Viewport is fixed across all phases; Moon appears only when in-frame.
    """
    con    = get_con()
    phases = get_phases()
    phase  = phases[phase_idx]
    pt     = phase["datetime_utc"]
    a      = np.radians(VIEW_ROTATION_DEG)
    R      = _get_body_radii()
    fr     = _get_fixed_ranges()

    ER, EG2, EG3, EG4, EG5 = R["ER"], R["EG2"], R["EG3"], R["EG4"], R["EG5"]
    MR, MG2, MG3, MG4      = R["MR"], R["MG2"], R["MG3"], R["MG4"]
    y0, y1                  = fr["y_range"]
    xc, xh                  = fr["x_center"], fr["x_half"]

    # ── Trajectory ────────────────────────────────────────────────────────
    full = con.execute(
        "SELECT x_km, y_km, datetime_utc FROM orion_trajectory ORDER BY datetime_utc"
    ).df()
    tx, ty = rotate_2d(full["x_km"].values, full["y_km"].values, a)

    pm = (full["datetime_utc"] <= pt).values
    fm = (full["datetime_utc"] >= pt).values
    px_, py_ = tx[pm], ty[pm]
    fx_, fy_ = tx[fm], ty[fm]

    # ── Moon ──────────────────────────────────────────────────────────────
    mr = con.execute(
        "SELECT m_x_km, m_y_km FROM v_earth_moon "
        "WHERE datetime_utc <= ? ORDER BY datetime_utc DESC LIMIT 1", [pt]
    ).fetchone()
    fmx, fmy = rotate_2d(
        np.float64(mr[0] if mr else 384_400.0),
        np.float64(mr[1] if mr else 0.0), a,
    )
    fmx, fmy     = float(fmx), float(fmy)
    moon_visible = in_range(fmy, y0, y1, margin=MG4)

    # ── Spacecraft ────────────────────────────────────────────────────────
    sr = con.execute(
        "SELECT x_km, y_km, speed_kms FROM v_kinematics "
        "WHERE datetime_utc <= ? ORDER BY datetime_utc DESC LIMIT 1", [pt]
    ).fetchone()
    fsx, fsy = rotate_2d(
        np.float64(sr[0] if sr else 0.0),
        np.float64(sr[1] if sr else 0.0), a,
    )
    fsx, fsy = float(fsx), float(fsy)
    spd      = float(sr[2]) if sr else 0.0
    callout  = f"ORION<br>{spd:.3f} km/s"

    # ── Traces ────────────────────────────────────────────────────────────
    T = []

    # ── Invisible x anchor — MUST be first trace ──────────────────────────
    # Two transparent points at the fixed x extremes. Forces Plotly to center
    # the scaleanchor-derived x range on xc at every phase, regardless of
    # which Moon / trajectory traces are present.
    yc = (y0 + y1) / 2
    T.append(go.Scatter(
        x=[xc - xh, xc + xh],
        y=[yc, yc],
        mode="markers",
        marker=dict(size=0.1, color="rgba(0,0,0,0)", line=dict(width=0)),
        hoverinfo="skip", showlegend=False,
    ))

    # Starfield (fixed — scattered across anchor x bounds)
    T.append(go.Scatter(
        x=fr["star_x"], y=fr["star_y"], mode="markers",
        marker=dict(size=fr["star_sz"], color=fr["star_colors"],
                    symbol="circle", line=dict(width=0)),
        hoverinfo="skip", showlegend=False,
    ))

    # Earth: glow layers + fill + specular highlight
    T.append(_filled(0, 0, EG5, "rgba(20,80,200,0.025)"))
    T.append(_filled(0, 0, EG4, "rgba(25,100,220,0.05)"))
    T.append(_filled(0, 0, EG3, "rgba(28,120,240,0.09)"))
    T.append(_filled(0, 0, EG2, "rgba(30,144,255,0.16)"))
    T.append(_filled(0, 0, ER,  "rgba(22,100,210,0.96)"))
    hx, hy = circle_xy(ER * 0.25, ER * 0.25, ER * 0.45, n=80)
    T.append(go.Scatter(
        x=hx, y=hy, mode="lines",
        fill="toself", fillcolor="rgba(80,170,255,0.18)",
        line=dict(color="rgba(0,0,0,0)", width=0),
        hoverinfo="skip", showlegend=False,
    ))

    # Moon: only when inside viewport
    if moon_visible:
        T.append(_filled(fmx, fmy, MG4, "rgba(160,160,160,0.03)"))
        T.append(_filled(fmx, fmy, MG3, "rgba(170,170,170,0.06)"))
        T.append(_filled(fmx, fmy, MG2, "rgba(185,185,185,0.12)"))
        T.append(_filled(fmx, fmy, MR,  "rgba(155,155,165,0.92)"))

    # Full trajectory dim context
    T.append(_line(tx, ty, "rgba(80,130,180,0.08)", 6))
    T.append(_line(tx, ty, "rgba(80,130,180,0.12)", 2))
    T.append(_line(tx, ty, COLOR_TRAJECTORY_DIM,    1, dash="dot"))

    # Past arc: glow passes + solid core
    if len(px_) > 1:
        T.append(_line(px_, py_, "rgba(255,255,255,0.06)", 8))
        T.append(_line(px_, py_, "rgba(255,255,255,0.12)", 4))
        T.append(_line(px_, py_, COLOR_TRAJECTORY,         1.5))

    # Future arc
    if len(fx_) > 1:
        T.append(_line(fx_, fy_, "rgba(90,140,190,0.50)", 1, dash="dash"))

    # Spacecraft marker
    T.append(go.Scatter(
        x=[fsx], y=[fsy], mode="markers",
        marker=dict(size=8, color="#ffffff", symbol="circle",
                    line=dict(color="rgba(200,232,255,0.35)", width=1.5)),
        hoverinfo="skip", showlegend=False,
    ))

    # Body labels
    label_x = [0.0]
    label_y = [-ER * 3.5]
    label_t = ["EARTH"]
    if moon_visible:
        label_x.append(fmx)
        label_y.append(fmy - MR * 7.0)
        label_t.append("MOON")

    T.append(go.Scatter(
        x=label_x, y=label_y, mode="text", text=label_t,
        textfont=dict(color=THEME_DARK["text_dim"], size=FONT_SIZE_LABEL,
                      family=THEME_DARK["font_family"]),
        hoverinfo="skip", showlegend=False,
    ))

    # ── Figure ────────────────────────────────────────────────────────────
    fig = go.Figure(data=T)

    fig.add_annotation(
        x=fsx, y=fsy, text=callout,
        showarrow=True, arrowhead=0,
        arrowcolor=THEME_DARK["text_dim"], arrowwidth=1,
        ax=72, ay=-44,
        font=dict(color=THEME_DARK["text"], size=FONT_SIZE_LABEL,
                  family=THEME_DARK["font_family"]),
        align="left",
        bgcolor="rgba(5,10,20,0.85)",
        bordercolor=THEME_DARK["panel_border"],
        borderwidth=1, borderpad=6,
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#000000",
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(
            visible=False,
            scaleanchor="y",
            scaleratio=1,
            # No explicit range — derived from y_range × container pixel ratio.
            # The anchor trace above fixes the x center so it never drifts.
        ),
        yaxis=dict(
            visible=False,
            range=fr["y_range"],
            autorange=False,
            fixedrange=True,
        ),
        hovermode=False,
        dragmode=False,
    )

    return fig