# pages/playback.py
#
# Mission control dashboard — registers at /playback/.
# All layout assembly, preload computation, and callbacks live here.
# App object imported from app.dash_instance (already initialised by main.py).

from pathlib import Path
from datetime import datetime as _datetime

import dash
import numpy as np
from dash import html, dcc, Input, Output, State, ctx, no_update
from dash.dependencies import ALL
from dash.exceptions import PreventUpdate

from app.dash_instance import app
from app.config import (
    PANEL_GROUPS,
    VIEW_ROTATION_DEG,
    ARC_MARKER_CATEGORY,
    PLAYBACK_FRAME_INTERVAL_MIN, PLAYBACK_INTERVAL_MS,
    PLAYBACK_FRAMES_PER_TICK,
    PLAYBACK_ANNOTATION_LEAD_FRAMES, PLAYBACK_ANNOTATION_TRAIL_FRAMES,
    LAUNCH_TIME,
    TELEMETRY_METRICS,
    DIAL_VAL_MIN, DIAL_VAL_MAX,
    BIDIR_NEGATIVE_COLOR,
)
from app.db import get_con
from app.phases import get_scrubber_phases, get_phases, get_arc_marker_phases
from app.utils import rotate_2d, fmt_met
from app.telemetry import get_telemetry_preload, get_telemetry_at, get_frame_pct
from components.header import build_header
from components.scrubber import build_scrubber
from components.telemetry_panel import build_telemetry_panel, build_telemetry_grid
from components.trajectory_panel import build_trajectory_content
from viz.trajectory import build_trajectory_fig, get_moon_preload_data
from viz.builders import build_sparkline_points



_PROJECT_ROOT = Path(__file__).parent.parent
_PROJECT_MD   = (_PROJECT_ROOT / "PROJECT.md").read_text(encoding="utf-8")



# ═══════════════════════════════════════════════════════════════════════════
#  SERVER-STARTUP PRELOAD
#
#  Computed once when the Python process starts. Baked into the Store's
#  initial data value so the browser has it the instant the page loads —
#  no callback round-trip, no timing race with the play button.
# ═══════════════════════════════════════════════════════════════════════════

def _build_preload_data() -> dict:
    """
    Rotate the full 12,836-point trajectory into the display frame and build
    everything the clientside playback callback needs.

    Keys
    ----
    rx / ry                  : rotated x/y for all frames (display-frame coords)
    speed                    : scalar speed [km/s] for all frames
    timestamps               : ISO strings for all frames (used by pause rebuild)
    arc_markers              : list of {key, short, label, rx, ry, frame_idx, category, met, rg_km}
    scrubber_frame_indices   : flat list of frame indices, one per scrubber dot in
                               dot order; clientside uses this to highlight the
                               active dot during playback
    annotation_window_frames : from config — frames either side of a marker where
                               the event badge is shown
    total_frames             : total row count
    frames_per_tick          : from config
    sun_angles               : Sun direction angle [degrees] in display-frame coords,
                               one value per frame; used for shadow half-disc geometry
    sun_nz                   : Normalized Z component of the 3D sun unit vector,
                               one value per frame; drives terminator curvature

    """
    con = get_con()
    a   = np.radians(VIEW_ROTATION_DEG)

    df = con.execute("""
        SELECT datetime_utc, x_km, y_km, speed_kms
        FROM   v_kinematics
        ORDER  BY datetime_utc
    """).df()

    rx, ry     = rotate_2d(df["x_km"].values, df["y_km"].values, a)
    timestamps = df["datetime_utc"].dt.strftime("%Y-%m-%dT%H:%M:%S").tolist()
    ts_index   = {ts: i for i, ts in enumerate(timestamps)}

    # Moon rotated coords — same rotation angle as Orion.
    # v_earth_moon joins orion_trajectory 1:1 on datetime_utc; row count matches.
    moon_df = con.execute("""
        SELECT m_x_km, m_y_km FROM v_earth_moon ORDER BY datetime_utc
    """).df()
    moon_rx, moon_ry = rotate_2d(
        moon_df["m_x_km"].values, moon_df["m_y_km"].values, a
    )

    sun_df = con.execute("""
        SELECT x_km, y_km, z_km FROM sun_trajectory ORDER BY datetime_utc
    """).df()
    sun_rx_, sun_ry_ = rotate_2d(sun_df["x_km"].values, sun_df["y_km"].values, a)
    sun_angles = np.degrees(np.arctan2(sun_ry_, sun_rx_)).tolist()
    sun_mag = np.sqrt(sun_df["x_km"] ** 2 + sun_df["y_km"] ** 2 + sun_df["z_km"] ** 2).values
    sun_nz = (sun_df["z_km"].values / np.where(sun_mag == 0, 1.0, sun_mag)).tolist()


    _launch_dt = _datetime.fromisoformat(LAUNCH_TIME)
    arc_phase_list = get_arc_marker_phases()

    # Bulk-fetch rg_km for all arc marker timestamps in one query.
    arc_rg_map: dict = {}
    if arc_phase_list:
        arc_ts = [p["datetime_utc"] for p in arc_phase_list]
        placeholders = ", ".join(["?" for _ in arc_ts])
        rg_rows = con.execute(
            f"SELECT datetime_utc, rg_km FROM orion_trajectory "
            f"WHERE datetime_utc IN ({placeholders})",
            arc_ts,
        ).fetchall()
        arc_rg_map = {row[0]: float(row[1]) for row in rg_rows}

    arc_markers = []
    for phase in arc_phase_list:
        dt_str = phase["datetime_utc"].strftime("%Y-%m-%dT%H:%M:%S")
        fidx = ts_index.get(dt_str)
        if fidx is None:
            continue
        met_sec = int((phase["datetime_utc"] - _launch_dt).total_seconds())
        arc_markers.append({
            "key":        phase["key"],
            "short":      phase["short"],
            "label":      phase["label"],
            "rx":         float(rx[fidx]),
            "ry":         float(ry[fidx]),
            "frame_idx":  fidx,
            "category":   ARC_MARKER_CATEGORY.get(phase["key"], "other"),
            "met":        fmt_met(met_sec),
            "rg_km":      arc_rg_map.get(phase["datetime_utc"], 0.0),
            "badge_side": phase.get("badge_side", "top"),   # ← new
        })

    # One frame index per scrubber dot, in dot order.
    # Clientside walks forward, keeping the last one we've passed.
    scrubber_frame_indices = []
    for sp in get_scrubber_phases():
        dt_str = sp["datetime_utc"].strftime("%Y-%m-%dT%H:%M:%S")
        scrubber_frame_indices.append(ts_index.get(dt_str, 0))

    # Status bar phases — events that define phase-label transitions.
    # Clientside walks forward and keeps the last one whose frame_idx ≤ fi.
    status_phases = []
    for phase in get_phases():
        if not phase.get("status_bar"):
            continue
        dt_str = phase["datetime_utc"].strftime("%Y-%m-%dT%H:%M:%S")
        fidx   = ts_index.get(dt_str)
        if fidx is None:
            continue
        status_phases.append({
            "frame_idx":    fidx,
            "status_label": phase.get("status_label", phase["label"].upper()),
        })

    # ── Telemetry series + sparkline paths ───────────────────────────────
    telem = get_telemetry_preload()

    sparkline_cols = {
        m["column"]
        for metrics in TELEMETRY_METRICS.values()
        for m in metrics
        if m["viz_type"] == "sparkline"
    }

    sparklines = {
        col: build_sparkline_points(series)
        for col, series in telem.items()
        if col in sparkline_cols
    }

    # Min/max per column — sent to JS so bar/bidir widths can be computed
    # relative to full-mission range without a separate query.
    series_stats = {
        col: {"min": float(min(series)), "max": float(max(series))}
        for col, series in telem.items()
    }

    # viz_type added so JS update loop can branch per metric without
    # hardcoding column names in playback.js
    telemetry_meta = [
        {
            "column":       m["column"],
            "decimals":     m["decimals"],
            "locale":       m["locale"],
            "viz_type":     m["viz_type"],
            "log_scale":    m.get("log_scale", False),
            # Dial range — JS uses these to map raw value → arc sweep fraction.
            # Must match DIAL_VAL_MIN/MAX in config.py or server and client
            # will render different arc positions on pause vs. playback.
            "dial_val_min": DIAL_VAL_MIN if m["viz_type"] == "dial" else None,
            "dial_val_max": DIAL_VAL_MAX if m["viz_type"] == "dial" else None,
            # Bidir negative color — the computed hue-rotated hex from config.
            # Passed here so JS gets the actual resolved value, not a CSS var.
            "pos_color":    m.get("bidir_pos_color") if m["viz_type"] == "bidir_bar" else None,
            "neg_color":    m.get("bidir_neg_color", BIDIR_NEGATIVE_COLOR) if m["viz_type"] == "bidir_bar" else None,
            "bidir_center": m.get("bidir_center", 0.0) if m["viz_type"] == "bidir_bar" else None,
            "bidir_mid":    m.get("bidir_mid", 0.5) if m["viz_type"] == "bidir_bar" else None,
        }
        for metrics in TELEMETRY_METRICS.values()
        for m in metrics
    ]

    return {
        "rx":                       rx.tolist(),
        "ry":                       ry.tolist(),
        "speed":                    df["speed_kms"].tolist(),
        "timestamps":               timestamps,
        "arc_markers":              arc_markers,
        "scrubber_frame_indices":   scrubber_frame_indices,
        "annotation_lead_frames":   PLAYBACK_ANNOTATION_LEAD_FRAMES,
        "annotation_trail_frames":  PLAYBACK_ANNOTATION_TRAIL_FRAMES,
        "total_frames":             len(df),
        "frames_per_tick":          PLAYBACK_FRAMES_PER_TICK,
        "target_ms_per_frame":      PLAYBACK_INTERVAL_MS / PLAYBACK_FRAMES_PER_TICK,
        "moon_rx":                  moon_rx.tolist(),
        "moon_ry":                  moon_ry.tolist(),
        "sun_angles":               sun_angles,
        "sun_nz":                   sun_nz,
        "status_phases":            status_phases,
        "launch_iso":               LAUNCH_TIME.replace(" ", "T"),
        "telemetry":                telem,
        "telemetry_sparklines":     sparklines,
        "telemetry_meta":           telemetry_meta,
        "series_stats":             series_stats,
        **get_moon_preload_data(),
    }

_PRELOAD_DATA = _build_preload_data()

# Only build polyline strings for sparkline-typed metrics — bars/dials don't use them
_SPARKLINE_COLS: set[str] = {
    m["column"]
    for metrics in TELEMETRY_METRICS.values()
    for m in metrics
    if m["viz_type"] == "sparkline"
}

_SPARKLINE_POINTS: dict[str, str] = {
    col: build_sparkline_points(series)
    for col, series in get_telemetry_preload().items()
    if col in _SPARKLINE_COLS
}

# Min/max per column — used by bar and bidir builders on server-side tile rebuilds.
# Computed here so _build_telemetry_panel doesn't re-derive it on every callback.
_SERIES_STATS: dict[str, dict] = {
    col: {"min": float(min(series)), "max": float(max(series))}
    for col, series in get_telemetry_preload().items()
}


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE LAYOUT
# ═══════════════════════════════════════════════════════════════════════════

layout = html.Div([   # <-- was app.layout = html.Div([

    dcc.Store(id="phase-store",            data=0),
    dcc.Store(id="playback-running-store", data={"running": False}),
    dcc.Store(id="playback-frame-store",   data={"frame_idx": 0}),
    dcc.Store(id="resize-store",           data=0),
    dcc.Store(id="panel-mode",             data=None),
    dcc.Store(id="last-panel-mode",        data="project"),
    dcc.Store(id="traj-preload-store",     data=_PRELOAD_DATA),
    dcc.Store(id="pause-rebuild-store"),
    dcc.Store(id="scrubber-seek-store"),
    html.Button(id="seek-trigger-btn", style={"display": "none"}),

    # ── Main dashboard ───────────────────────────────────────────────────
    html.Div([

        # ── Dummy outputs for clientside callbacks ───────────────────────────
        html.Div(id="artemis-init-dummy", style={"display": "none"}),

        # ── Header ───────────────────────────────────────────────────────────
        build_header(),
        html.Div(className="dashboard-spacer"),  # ← top spacer

        # ── Trajectory panel ─────────────────────────────────────────────────
        html.Div([
            html.Div(
                "FDO · TRAJECTORY · ORION / UPPER STAGE · EARTH-MOON",
                className="panel-trajectory-header",
            ),
            html.Div([
                html.Div(
                    id="trajectory-content",
                    style={"position": "absolute", "inset": "0"},
                ),
                build_scrubber(),
            ], className="panel-trajectory-viz"),
        ], className="panel panel-trajectory"),

        # ── Telemetry panels ─────────────────────────────────────────────────
        build_telemetry_grid(),
        html.Div(className="dashboard-spacer"),  # ← bottom spacer

    ], className="dashboard"),

    # ── Side panel controls strip ────────────────────────────────────────
    html.Div([
        html.Div("READ ME →", className="side-panel-hint"),
        html.Button(
            "‹",
            id="side-panel-toggle-btn",
            className="side-panel-btn",
            n_clicks=0,
            title="Project info",
        ),
    ], className="side-panel-controls"),

    # ── Side panel ───────────────────────────────────────────────────────
    html.Div(
        id="side-panel",
        className="side-panel",
        children=[
            html.Div(
                id="side-panel-inner",
                className="side-panel-inner",
                children=[html.Div(id="side-panel-content")],
            )
        ],
    ),

], className="page-root")

dash.register_page(__name__, path="/playback/", layout=layout)


# ═══════════════════════════════════════════════════════════════════════════
#  CLIENTSIDE CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════

# ── Initialize window._artemisState on page load ─────────────────────────────
# Fires once with the baked-in preload data. After this the rAF loop in
# playback.js has everything it needs — it just waits for running = true.
app.clientside_callback(
    """function(preloaded) {
        if (!preloaded) return window.dash_clientside.no_update;
        window._artemisState = {
            running:     false,
            frame_idx:   0,
            preloaded:   preloaded,
            needsRender: false,
        };
        window._artemisFrame = 0;
        return null;
    }""",
    Output("artemis-init-dummy", "children"),
    Input("traj-preload-store", "data"),
)

# ── Toggle play/pause ────────────────────────────────────────────────────────
# Writes window._artemisState.running so the rAF loop sees it immediately.
# Button DOM update is a side effect here — render-btn-state callback removed.
# Still writes playback-running-store so on_playback_pause fires on pause.
app.clientside_callback(
    """function(n_clicks, state) {
        if (!n_clicks || !state) return window.dash_clientside.no_update;
        var currentRunning = (window._artemisState && window._artemisState.preloaded)
                             ? window._artemisState.running
                             : state.running;
        var nowRunning = !currentRunning;

        if (!window._artemisState) window._artemisState = {};

        // If resuming from the end of mission, restart from frame 0.
        if (nowRunning) {
            var total = window._artemisState.preloaded
                        && window._artemisState.preloaded.total_frames;
            if (total && window._artemisState.frame_idx >= total - 1) {
                window._artemisState.frame_idx  = 0;
                window._artemisState.resetTiming = true;
            }
        }

        window._artemisState.running = nowRunning;

        var btn = document.getElementById('playback-btn');
        if (btn) {
            btn.textContent = nowRunning ? '\u23f8' : '\u25b6';
            btn.className   = nowRunning ? 'playback-btn playing' : 'playback-btn';
        }

        return {running: nowRunning};
    }""",
    Output("playback-running-store", "data"),
    Input("playback-btn", "n_clicks"),
    State("playback-running-store", "data"),
    prevent_initial_call=True,
)

# ── Reset frame when scrubber dot is clicked ────────────────────────────────
# Writes window._artemisState so the rAF loop advances from the new position.
# needsRender forces an immediate draw even when paused.
# Still writes playback-frame-store so on_playback_pause reads the correct
# frame when the user pauses after a scrubber-click.
app.clientside_callback(
    """function(phaseIdx, preloaded) {
        if (phaseIdx === null || phaseIdx === undefined || !preloaded)
            return window.dash_clientside.no_update;
        var frames = preloaded.scrubber_frame_indices || [];
        var fi = (frames[phaseIdx] !== undefined) ? frames[phaseIdx] : 0;

        if (!window._artemisState) window._artemisState = {};
        window._artemisState.frame_idx   = fi;
        window._artemisState.needsRender = true;
        window._artemisState.resetTiming = true;

        // If the mission ended and the button is showing ↺, restore it to ▶.
        // Scrubber navigation after end-of-mission should return to paused/ready state.
        var btn = document.getElementById('playback-btn');
        if (btn && btn.textContent === '\u21ba') {
            btn.textContent = '\u25b6';
            btn.className   = 'playback-btn';
        }

        // Update dot immediately — don't wait for renderFrame round-trip.
        document.querySelectorAll('.scrubber-dot').forEach(function(dot, idx) {
            dot.className = (idx === phaseIdx)
                ? 'scrubber-dot active'
                : 'scrubber-dot';
        });

        return {frame_idx: fi};
    }""",
    Output("playback-frame-store", "data", allow_duplicate=True),
    Input("phase-store", "data"),
    State("traj-preload-store", "data"),
    prevent_initial_call=True,
)

# ── Scrubber seek → scrubber-seek-store ──────────────────────────────────────
# Fired by playback.js clicking #seek-trigger-btn on mouseup.
# Reads _artemisState.frame_idx directly — the live source of truth.
app.clientside_callback(
    """function(n) {
        if (!n) return window.dash_clientside.no_update;
        var state = window._artemisState;
        if (!state || !state.preloaded) return window.dash_clientside.no_update;
        var fi             = state.frame_idx;
        var scrubberFrames = state.preloaded.scrubber_frame_indices || [];
        var phaseIdx       = 0;
        for (var i = 0; i < scrubberFrames.length; i++) {
            if (scrubberFrames[i] <= fi) phaseIdx = i;
        }
        return {
            dt_str:    state.preloaded.timestamps[fi],
            phase_idx: phaseIdx,
        };
    }""",
    Output("scrubber-seek-store", "data"),
    Input("seek-trigger-btn", "n_clicks"),
    prevent_initial_call=True,
)


# ═══════════════════════════════════════════════════════════════════════════
#  SERVER CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("panel-mode", "data"),
    Output("last-panel-mode", "data"),
    Input("side-panel-toggle-btn", "n_clicks"),
    State("panel-mode", "data"),
    State("last-panel-mode", "data"),
    prevent_initial_call=True,
)
def update_panel_mode(n_clicks, current_mode, last_mode):
    if current_mode is not None:
        return None, no_update  # collapse — remember last mode
    return last_mode, no_update  # reopen to last mode


@app.callback(
    Output("side-panel", "className"),
    Output("side-panel-toggle-btn", "children"),
    Output("side-panel-toggle-btn", "className"),
    Input("panel-mode", "data"),
)
def update_panel_state(mode):
    panel_cls = "side-panel open" if mode is not None else "side-panel"
    chevron = "›" if mode is not None else "‹"
    toggle_cls = "side-panel-btn active" if mode == "project" else "side-panel-btn"
    return panel_cls, chevron, toggle_cls


@app.callback(
    Output("side-panel-content", "children"),
    Input("panel-mode", "data"),
)
def render_panel_content(mode):
    if mode == "project":
        return dcc.Markdown(_PROJECT_MD, link_target="_blank")
    return None


@app.callback(
    Output("phase-store", "data"),
    Input({"type": "scrubber-dot", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def update_phase(n_clicks):
    triggered = ctx.triggered_id
    if triggered is None:
        return 0
    return triggered["index"]


# ── Detect pause → write pause-rebuild-store ─────────────────────────────────
# Clientside so it can read window._artemisState.frame_idx directly — the rAF
# loop never writes back to playback-frame-store, so the old server callback
# always saw a stale frame index.
app.clientside_callback(
    """function(runningState, phaseIdx) {
        if (!runningState || runningState.running)
            return window.dash_clientside.no_update;

        var state = window._artemisState;
        if (!state || !state.preloaded || !state.preloaded.timestamps)
            return window.dash_clientside.no_update;

        return {
            dt_str:    state.preloaded.timestamps[state.frame_idx],
            phase_idx: phaseIdx || 0,
        };
    }""",
    Output("pause-rebuild-store", "data"),
    Input("playback-running-store", "data"),
    State("phase-store", "data"),
    prevent_initial_call=True,
)


# ── Full-quality figure rebuild ────────────────────────────────────
@app.callback(
    Output("trajectory-content", "children"),
    Input("phase-store", "data"),  # scrubber dot click
    Input("pause-rebuild-store", "data"),  # playback paused
    Input("scrubber-seek-store", "data"),  # drag/click seek
    Input("resize-store", "data"),
)
def update_trajectory(phase_idx, pause_data, seek_data, _resize):
    trigger = ctx.triggered_id

    scrubber_phases = get_scrubber_phases()
    all_phases = get_phases()

    if trigger in ("pause-rebuild-store", "scrubber-seek-store"):
        payload = pause_data if trigger == "pause-rebuild-store" else seek_data
        if payload and payload.get("dt_str"):
            scrubber_idx = payload.get("phase_idx", 0)
            phase_key = scrubber_phases[scrubber_idx]["key"]
            global_idx = next(i for i, p in enumerate(all_phases) if p["key"] == phase_key)
            override_dt = _datetime.fromisoformat(payload["dt_str"])
            fig = build_trajectory_fig(global_idx, override_dt=override_dt)
            return build_trajectory_content(fig)

    # phase-store, resize, or initial load
    scrubber_idx = phase_idx or 0
    phase_key = scrubber_phases[scrubber_idx]["key"]
    global_idx = next(i for i, p in enumerate(all_phases) if p["key"] == phase_key)
    fig = build_trajectory_fig(global_idx)
    return build_trajectory_content(fig)


@app.callback(
    Output("telemetry-grid", "children"),
    Input("phase-store", "data"),
    Input("pause-rebuild-store", "data"),
    Input("scrubber-seek-store", "data"),
    prevent_initial_call=False,
)
def update_telemetry(phase_idx, pause_data, seek_data):
    trigger = ctx.triggered_id

    if trigger in ("pause-rebuild-store", "scrubber-seek-store"):
        payload = pause_data if trigger == "pause-rebuild-store" else seek_data
        if payload and payload.get("dt_str"):
            dt_utc = _datetime.fromisoformat(payload["dt_str"])
            values = get_telemetry_at(dt_utc)
            current_pct = get_frame_pct(dt_utc)
            return [
                build_telemetry_panel(
                    group_key=key,
                    group=grp,
                    values_dict=values,
                    current_pct=current_pct,
                    series_stats=_SERIES_STATS,
                    sparkline_points_map=_SPARKLINE_POINTS,
                )
                for key, grp in PANEL_GROUPS.items()
            ]

    # phase-store or initial load
    phases = get_scrubber_phases()
    idx = phase_idx if phase_idx is not None else 0
    idx = max(0, min(idx, len(phases) - 1))
    dt_utc = phases[idx]["datetime_utc"]

    values = get_telemetry_at(dt_utc)
    current_pct = get_frame_pct(dt_utc)

    return [
        build_telemetry_panel(
            group_key=key,
            group=grp,
            values_dict=values,
            current_pct=current_pct,
            series_stats=_SERIES_STATS,
            sparkline_points_map=_SPARKLINE_POINTS,
        )
        for key, grp in PANEL_GROUPS.items()
    ]