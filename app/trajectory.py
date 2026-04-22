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
from datetime import timedelta

import plotly.graph_objects as go

from app.config import (
    FONT_SIZE_LABEL,
    FONT_FAMILY, FONT_PRIMARY, FONT_DIM, PANEL_BORDER,
    VIEW_ROTATION_DEG, VIEW_ZOOM, VIEW_X_OFFSET_KM, VIEW_Y_OFFSET_KM,
    STAR_SEED, STAR_COUNT,
    STAR_DIM_FRACTION,
    STAR_SIZE_DIM_MIN, STAR_SIZE_DIM_MAX,
    STAR_SIZE_FG_MIN, STAR_SIZE_FG_MAX,
    STAR_ALPHA_DIM_MIN, STAR_ALPHA_DIM_MAX,
    STAR_ALPHA_FG_MIN, STAR_ALPHA_FG_MAX,
    SPACE_BG_COLOR,
    EARTH_LABEL_Y_MULT, MOON_LABEL_Y_MULT,
    ORION_LABEL_SHOW, ORION_LABEL_BG_ALPHA, ORION_LABEL_XSHIFT, ORION_LABEL_YSHIFT, ORION_MARKER_SIZE,
    TRAJ_DIM_GLOW_RGB, TRAJ_DIM_GLOW_WIDE, TRAJ_DIM_GLOW_WIDE_ALPHA,
    TRAJ_DIM_CORE_RGB, TRAJ_DIM_CORE_WIDTH, TRAJ_DIM_CORE_ALPHA, TRAJ_DIM_CORE_DASH,
    PAST_ARC_RGB, PAST_ARC_GLOW_WIDTH, PAST_ARC_GLOW_ALPHA,
    PAST_ARC_CORE_WIDTH, PAST_ARC_CORE_ALPHA,
    FUTURE_ARC_HOURS, FUTURE_FADE_HOURS, FUTURE_FADE_SEGMENTS,
    FUTURE_GLOW_RGB, FUTURE_GLOW_WIDE, FUTURE_GLOW_WIDE_ALPHA, FUTURE_GLOW_NARROW, FUTURE_GLOW_NARROW_ALPHA,
    FUTURE_CORE_RGB, FUTURE_CORE_WIDTH, FUTURE_CORE_ALPHA, FUTURE_CORE_DASH,
    ARC_DOT_BURN, ARC_DOT_COAST, ARC_DOT_OTHER,
    ARC_MARKER_CATEGORY,
    ARC_DOT_SIZE, ARC_LABEL_SIZE,
)
from app.utils import rotate_2d, circle_xy, fmt_met, in_range
from app.db import get_con
from app.phases import get_phases, get_arc_marker_phases


# ── Module-level caches ───────────────────────────────────────────────────
_BODY_RADII:   dict | None = None
_FIXED_RANGES: dict | None = None

_STARFIELD_SVG: str | None = None


def build_starfield_svg() -> str:
    """
    Build a static SVG string of the starfield background. Cached after
    first call — seed is fixed so output is always identical.

    SVG uses a 0–100 viewBox with preserveAspectRatio="none" so it always
    fills its container exactly, regardless of panel aspect ratio.
    A black rect is the first element, replacing plot_bgcolor on the figure.
    """
    global _STARFIELD_SVG
    if _STARFIELD_SVG is not None:
        return _STARFIELD_SVG

    rng   = np.random.default_rng(STAR_SEED)
    n_dim = int(STAR_COUNT * STAR_DIM_FRACTION)
    n_fg  = STAR_COUNT - n_dim

    cx = rng.uniform(0, 100, STAR_COUNT)
    cy = rng.uniform(0, 100, STAR_COUNT)

    radii = np.concatenate([
        rng.uniform(STAR_SIZE_DIM_MIN, STAR_SIZE_DIM_MAX, n_dim),
        rng.uniform(STAR_SIZE_FG_MIN,  STAR_SIZE_FG_MAX,  n_fg),
    ])
    alphas = np.concatenate([
        rng.uniform(STAR_ALPHA_DIM_MIN, STAR_ALPHA_DIM_MAX, n_dim),
        rng.uniform(STAR_ALPHA_FG_MIN,  STAR_ALPHA_FG_MAX,  n_fg),
    ])

    circles = "\n  ".join(
        f'<circle cx="{cx[i]:.2f}" cy="{cy[i]:.2f}" r="{radii[i]:.3f}" '
        f'fill="rgba(255,255,255,{alphas[i]:.2f})"/>'
        for i in range(STAR_COUNT)
    )

    _STARFIELD_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="100%" height="100%" '
        'viewBox="0 0 100 100" '
        'preserveAspectRatio="xMidYMid slice" '
        'style="display:block;position:absolute;inset:0;width:100%;height:100%">'
        f'\n  <rect width="100" height="100" fill="{SPACE_BG_COLOR}"/>'
        f'\n  {circles}\n</svg>'
    )
    return _STARFIELD_SVG

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

    _FIXED_RANGES = dict(
        y_range=y_range,
        y_half=y_half,
        x_center=xc,
        x_half=anchor_half,
        # star_colors=[f"rgba(255,255,255,{v:.2f})" for v in sa],
    )
    return _FIXED_RANGES


# ═════════════════════════════════════════════════════════════════════════
#  Trajectory Arc Points of Interest
# ═════════════════════════════════════════════════════════════════════════

def _build_arc_marker_traces(
    arc_phases: list[dict],
    rotation_rad: float,
    current_dt,
) -> list:
    """
    Dot markers for arc_marker phases that have already been passed
    (datetime_utc <= current_dt). No permanent labels — short code and
    full label surface on hover only.
    """
    # Filter to past events only
    past_phases = [p for p in arc_phases if p["datetime_utc"] <= current_dt]
    if not past_phases:
        return []

    con = get_con()

    timestamps   = [p["datetime_utc"] for p in past_phases]
    placeholders = ", ".join(["?" for _ in timestamps])
    rows = con.execute(
        f"SELECT datetime_utc, x_km, y_km FROM orion_trajectory "
        f"WHERE datetime_utc IN ({placeholders})",
        timestamps,
    ).fetchall()

    coord_map: dict = {}
    for dt, x, y in rows:
        rx, ry = rotate_2d(float(x), float(y), rotation_rad)
        coord_map[dt] = (float(rx), float(ry))

    _PALETTE = {
        "burn":  ARC_DOT_BURN,
        "coast": ARC_DOT_COAST,
        "other": ARC_DOT_OTHER,
    }

    groups: dict[str, list[dict]] = {"burn": [], "coast": [], "other": []}
    for phase in past_phases:
        coords = coord_map.get(phase["datetime_utc"])
        if coords is None:
            continue
        cat = ARC_MARKER_CATEGORY.get(phase["key"], "other")
        groups[cat].append({"phase": phase, "x": coords[0], "y": coords[1]})

    traces = []

    for cat, items in groups.items():
        if not items:
            continue
        color = _PALETTE[cat]
        traces.append(go.Scatter(
            x=[it["x"] for it in items],
            y=[it["y"] for it in items],
            mode="markers",
            marker=dict(
                size=ARC_DOT_SIZE,
                color=color,
                line=dict(color="rgba(0,0,0,0)", width=0),
            ),
            customdata=[
                [it["phase"]["short"], it["phase"]["label"]]
                for it in items
            ],
            hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}<extra></extra>",
            hoverlabel=dict(
                bgcolor="#0a1628",
                bordercolor="#1a2f4a",
                font=dict(family=FONT_FAMILY, color="#c8e8ff", size=FONT_SIZE_LABEL),
            ),
            showlegend=False,
        ))

    return traces


# ═════════════════════════════════════════════════════════════════════════
#  Main builder
# ═════════════════════════════════════════════════════════════════════════

def build_trajectory_fig(phase_idx: int, override_dt=None) -> go.Figure:
    """
    2D Earth–Moon trajectory figure for the given phase index (0–4).
    Viewport is fixed across all phases; Moon appears only when in-frame.
    """
    con    = get_con()
    phases = get_phases()
    phase  = phases[phase_idx]
    pt     = override_dt if override_dt is not None else phase["datetime_utc"]
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

    future_end = pt + timedelta(hours=FUTURE_ARC_HOURS)
    fade_start = pt + timedelta(hours=FUTURE_ARC_HOURS - FUTURE_FADE_HOURS)

    pm  = (full["datetime_utc"] <= pt).values
    sfm = ((full["datetime_utc"] >= pt) & (full["datetime_utc"] <= fade_start)).values
    ffm = ((full["datetime_utc"] >= fade_start) & (full["datetime_utc"] <= future_end)).values

    px_, py_ = tx[pm],  ty[pm]
    sfx, sfy = tx[sfm], ty[sfm]   # solid future portion (0 → 18h)
    ffx, ffy = tx[ffm], ty[ffm]   # fading future portion (18h → 24h)

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

    # Past arc — always emitted so trace indices are stable across all phases.
    # Empty lists render nothing; playback will restyle x/y each tick.
    _past_x = list(px_) if len(px_) > 1 else []
    _past_y = list(py_) if len(py_) > 1 else []

    IDX_PAST_GLOW = len(T)
    T.append(_line(_past_x, _past_y, f"rgba({PAST_ARC_RGB}, {PAST_ARC_GLOW_ALPHA})", PAST_ARC_GLOW_WIDTH))

    IDX_PAST_CORE = len(T)
    T.append(_line(_past_x, _past_y, f"rgba({PAST_ARC_RGB}, {PAST_ARC_CORE_ALPHA})", PAST_ARC_CORE_WIDTH))

    # Full mission dim context arc (ghost path — always visible)
    if False:
        T.append(_line(tx, ty, f"rgba({TRAJ_DIM_GLOW_RGB},{TRAJ_DIM_GLOW_WIDE_ALPHA:.3f})", TRAJ_DIM_GLOW_WIDE))
        T.append(_line(tx, ty, f"rgba({TRAJ_DIM_GLOW_RGB},{TRAJ_DIM_GLOW_NARROW_ALPHA:.3f})", TRAJ_DIM_GLOW_NARROW))
        T.append(_line(tx, ty, f"rgba({TRAJ_DIM_CORE_RGB},{TRAJ_DIM_CORE_ALPHA:.3f})", TRAJ_DIM_CORE_WIDTH, dash=TRAJ_DIM_CORE_DASH))

    # Future arc — solid portion (three layers: wide glow + narrow glow + core)
    if len(sfx) > 1:
        T.append(_line(sfx, sfy, f"rgba({FUTURE_GLOW_RGB},{FUTURE_GLOW_WIDE_ALPHA:.3f})",   FUTURE_GLOW_WIDE))
        T.append(_line(sfx, sfy, f"rgba({FUTURE_GLOW_RGB},{FUTURE_GLOW_NARROW_ALPHA:.3f})", FUTURE_GLOW_NARROW))
        T.append(_line(sfx, sfy, f"rgba({FUTURE_CORE_RGB},{FUTURE_CORE_ALPHA:.3f})",         FUTURE_CORE_WIDTH, dash=FUTURE_CORE_DASH))

    # Future arc — fading tail (same three layers, all alpha stepping to 0 together)
    if len(ffx) > 1:
        pts = len(ffx)
        for i in range(FUTURE_FADE_SEGMENTS):
            i0 = int(i / FUTURE_FADE_SEGMENTS * pts)
            i1 = min(int((i + 1) / FUTURE_FADE_SEGMENTS * pts) + 1, pts)
            if i1 <= i0 + 1:
                continue
            fade = 1.0 - i / max(1, FUTURE_FADE_SEGMENTS - 1)
            T.append(_line(ffx[i0:i1], ffy[i0:i1], f"rgba({FUTURE_GLOW_RGB},{FUTURE_GLOW_WIDE_ALPHA * fade:.3f})",
                           FUTURE_GLOW_WIDE))
            T.append(_line(ffx[i0:i1], ffy[i0:i1], f"rgba({FUTURE_GLOW_RGB},{FUTURE_GLOW_NARROW_ALPHA * fade:.3f})",
                           FUTURE_GLOW_NARROW))
            T.append(_line(ffx[i0:i1], ffy[i0:i1], f"rgba({FUTURE_CORE_RGB},{FUTURE_CORE_ALPHA * fade:.3f})",
                           FUTURE_CORE_WIDTH, dash=FUTURE_CORE_DASH))

    # Arc marker dots — past events only, hover labels
    T.extend(_build_arc_marker_traces(get_arc_marker_phases(), a, pt))

    # Spacecraft marker — index recorded for playback restyle
    IDX_MARKER = len(T)
    T.append(go.Scatter(
        x=[fsx], y=[fsy], mode="markers",
        marker=dict(size=ORION_MARKER_SIZE, color="#ffffff", symbol="circle",
                    line=dict(color="rgba(200,232,255,0.35)", width=1.5)),
        hoverinfo="skip", showlegend=False,
    ))

    # Body labels
    label_x = [0.0]
    label_y = [-ER * EARTH_LABEL_Y_MULT]
    label_t = ["EARTH"]
    if moon_visible:
        label_x.append(fmx)
        label_y.append(fmy - MR * MOON_LABEL_Y_MULT)
        label_t.append("MOON")

    T.append(go.Scatter(
        x=label_x, y=label_y, mode="text", text=label_t,
        textfont=dict(color=FONT_DIM, size=FONT_SIZE_LABEL, family=FONT_FAMILY),
        hoverinfo="skip", showlegend=False,
    ))

    # ── Figure ────────────────────────────────────────────────────────────
    fig = go.Figure(data=T)

    if ORION_LABEL_SHOW:
        fig.add_annotation(
            x=0, y=0, text="",
            visible=False,
            showarrow=False,
            xanchor="center",
            yshift=-28,
            font=dict(color=FONT_PRIMARY, size=FONT_SIZE_LABEL, family=FONT_FAMILY),
            bgcolor="rgba(5,10,20,0.82)",
            bordercolor=PANEL_BORDER,
            borderwidth=1, borderpad=5,
        )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
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

    fig.update_layout(meta={
        "trace_idx": {
            "past_glow": IDX_PAST_GLOW,
            "past_core": IDX_PAST_CORE,
            "marker": IDX_MARKER,
        }
    })

    return fig