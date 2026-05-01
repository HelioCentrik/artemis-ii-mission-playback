# app.py
#
# Dash application entry point. Layout structure and callback wiring only.
# Business logic lives in dedicated modules under app/.
#
# ── Playback architecture ─────────────────────────────────────────────────
#
#   Stores (all client-side JSON blobs):
#     phase-store            int          scrubber dot index; written by dot clicks
#     playback-running-store {running}    bool; toggled exclusively by play/pause btn
#     playback-frame-store   {frame_idx}  int; advanced exclusively by interval tick
#     traj-preload-store     {rx,ry,…}    full rotated trajectory + arc marker data;
#                                         computed ONCE at server startup, baked into
#                                         Store initial data — available immediately
#                                         on page load with zero callback latency
#     pause-rebuild-store    {dt_str,…}   written when playback stops; triggers
#                                         server-side full-quality figure rebuild
#
#   Clientside callbacks (zero round-trips):
#     init-artemis-state : traj-preload-store load → window._artemisState init
#     toggle-running     : playback-btn click  → window._artemisState.running
#                          + playback-running-store (triggers on-pause server cb)
#     reset-frame        : phase-store change  → window._artemisState.frame_idx
#                          + playback-frame-store (keeps on-pause state accurate)
#
#   Hot path (React-free):
#     playback.js rAF loop reads window._artemisState each frame, advances
#     frame_idx on wall-clock elapsed time, calls Plotly directly.
#     Writes window._artemisFrame each tick for telemetry hooks (Phase 5).
#
#   Server callbacks:
#     update-phase       : scrubber dot click  → phase-store
#     update-scrubber    : phase-store → scrubber-dot classNames
#     on-pause           : playback-running-store → pause-rebuild-store
#     update-trajectory  : phase-store | pause-rebuild-store → trajectory-content
#                          (Full-quality rebuild on phase click or pause)

import dash
from dash import html, dcc, Input, Output, State, ctx
from dash.dependencies import ALL
from dash.exceptions import PreventUpdate
from datetime import datetime as _datetime

import numpy as np

from app.config import (
    PANEL_GROUPS,
    VIEW_ROTATION_DEG,
    ARC_MARKER_CATEGORY,
    PLAYBACK_FRAME_INTERVAL_MIN, PLAYBACK_INTERVAL_MS, PLAYBACK_FRAMES_PER_TICK, PLAYBACK_ANNOTATION_WINDOW_FRAMES,
    PLAYBACK_SPEED_LABEL,
    LAUNCH_TIME,
    TELEMETRY_METRICS,
    DIAL_VAL_MIN, DIAL_VAL_MAX,
    BIDIR_NEGATIVE_COLOR,
)
from app.db import get_con
from app.phases import get_scrubber_phases, get_phases, get_arc_marker_phases
from app.utils import rotate_2d
from app.index_string import INDEX_STRING
from app.trajectory import build_trajectory_fig, build_starfield_svg, get_moon_preload_data
from app.telemetry import get_telemetry_preload, get_telemetry_at, get_frame_pct
from app.viz_builders import build_sparkline_points
from app.kpi import build_kpi_tile

# Register the artemis2 Plotly template as a side effect of import
import app.plotly_template  # noqa: F401



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
    arc_markers              : list of {key, short, label, rx, ry, frame_idx, category}
    scrubber_frame_indices   : flat list of frame indices, one per scrubber dot in
                               dot order; clientside uses this to highlight the
                               active dot during playback
    annotation_window_frames : from config — frames either side of a marker where
                               the event badge is shown
    total_frames             : total row count
    frames_per_tick          : from config
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

    arc_markers = []
    for phase in get_arc_marker_phases():
        dt_str = phase["datetime_utc"].strftime("%Y-%m-%dT%H:%M:%S")
        fidx   = ts_index.get(dt_str)
        if fidx is None:
            continue
        arc_markers.append({
            "key":       phase["key"],
            "short":     phase["short"],
            "label":     phase["label"],
            "rx":        float(rx[fidx]),
            "ry":        float(ry[fidx]),
            "frame_idx": fidx,
            "category":  ARC_MARKER_CATEGORY.get(phase["key"], "other"),
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
        "annotation_window_frames": PLAYBACK_ANNOTATION_WINDOW_FRAMES,
        "total_frames":             len(df),
        "frames_per_tick":          PLAYBACK_FRAMES_PER_TICK,
        "target_ms_per_frame":      PLAYBACK_INTERVAL_MS / PLAYBACK_FRAMES_PER_TICK,
        "moon_rx":                  moon_rx.tolist(),
        "moon_ry":                  moon_ry.tolist(),
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
#  APP INIT
# ═══════════════════════════════════════════════════════════════════════════

app = dash.Dash(
    __name__,
    title="Artemis II · Mission Playback",
    update_title=None,
    index_string=INDEX_STRING,
)

server = app.server



# ═══════════════════════════════════════════════════════════════════════════
#  LAYOUT HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _build_header():
    """Branding bar only — status info moved to trajectory HUD overlay."""
    return html.Div([
        html.Div([
            html.Div([
                html.Div("ARTEMIS II : MISSION PLAYBACK", className="header-title"),
            ], className="header-brand-left"),
        ], className="header-brand"),
    ])


def _build_scrubber():
    scrubber_phases = get_scrubber_phases()
    dots = []
    for i, phase in enumerate(scrubber_phases):
        dots.append(
            html.Div(
                className=f"scrubber-dot{' active' if i == 0 else ''}",
                style={"left": f"{phase['scrubber_pct']:.2f}%"},
                id={"type": "scrubber-dot", "index": i},
                title=phase["label"],
            )
        )
    return html.Div([
        html.Div("▶", id="playback-btn", className="playback-btn"),
        html.Div(dots, className="scrubber-track"),
    ], className="scrubber")


def _build_telemetry_panel(
    group_key:    str,
    group:        dict,
    values_dict:  dict | None = None,
    current_pct:  float       = 0.0,
    series_stats: dict        = {},
) -> html.Div:
    """
    Build one telemetry panel with 3 KPI tiles.

    values_dict  : {column: float} from get_telemetry_at(); None → stub tiles
    current_pct  : SVG x-coord for sparkline needle (0–KPI_SVG_VIEWBOX_WIDTH)
    series_stats : {column: {min, max}} for bar/bidir range scaling
    """
    if values_dict is None:
        stub_tile = html.Div([
            html.Div([
                html.Span("---", className="tile-label"),
                html.Span("---", className="tile-unit"),
            ], className="tile-header"),
            html.Span("--", className="tile-value"),
            html.Div(className="tile-sparkline"),
        ], className="tile")

        tiles = [stub_tile, stub_tile, stub_tile]

    else:
        tiles = [
            build_kpi_tile(
                metric_cfg       = m,
                value            = values_dict.get(m["column"], 0.0),
                series_stats     = series_stats,
                sparkline_points = _SPARKLINE_POINTS.get(m["column"], ""),
                current_pct      = current_pct,
            )
            for m in TELEMETRY_METRICS[group_key]
        ]

    return html.Div([
        html.Div([
            html.Div([
                html.Span(className="accent-dot"),
                html.Span(group["label"]),
            ], className="telemetry-panel-label"),
            html.Span(group["code"], className="telemetry-panel-code"),
        ], className="telemetry-panel-header"),
        html.Div(tiles, className="tile-grid"),
    ], className=f"panel telemetry-panel telemetry-panel--{group_key}")


def _build_telemetry_grid() -> html.Div:
    return html.Div(
        id="telemetry-grid",
        className="telemetry-grid",
        children=[
            _build_telemetry_panel(key, grp)
            for key, grp in PANEL_GROUPS.items()
        ],
    )


def _trajectory_content(fig) -> html.Div:
    """
    Starfield SVG (z=0) + Plotly graph (z=1) + HUD overlay (z=2)
    inside a relative container.

    dcc.Graph gets id="trajectory-graph" so the clientside frame-update
    callback can locate it via document.getElementById. React reconciles
    the graph in-place when the figure prop changes (same id = no teardown).
    Pointer-events disabled — the scrubber overlay handles all clicks.
    """
    return html.Div([
        dcc.Markdown(
            build_starfield_svg(),
            dangerously_allow_html=True,
            style={
                "position": "absolute",
                "inset": "0",
                "zIndex": "0",
                "lineHeight": "0",
            },
        ),
        dcc.Graph(
            id="trajectory-graph",
            figure=fig,
            config=dict(displayModeBar=False),
            style={
                "position": "absolute",
                "inset": "0",
                "height": "100%",
                "zIndex": "1",
                "pointerEvents": "none",
            },
        ),
        # ── HUD overlay — GMT · MET · Phase · Playback rate ──────────────
        html.Div([
            html.Div([
                html.Span(className="status-dot"),
                html.Span(
                    "GMT ---:--:--:-- · MET --T --:--:-- · ----:---",
                    id="status-text",
                ),
            ], className="traj-hud-left"),
            html.Span(PLAYBACK_SPEED_LABEL, className="traj-hud-right"),
        ], className="traj-hud-overlay"),
    ], style={"position": "relative", "height": "100%"})



# ═══════════════════════════════════════════════════════════════════════════
#  PAGE LAYOUT
# ═══════════════════════════════════════════════════════════════════════════

app.layout = html.Div([

    # ── Stores ──────────────────────────────────────────────────────────
    dcc.Store(id="phase-store",            data=0),
    dcc.Store(id="playback-running-store", data={"running": False}),
    dcc.Store(id="playback-frame-store",   data={"frame_idx": 0}),
    dcc.Store(id="resize-store",           data=0),

    # Preload baked in at startup — immediately available, no callback needed.
    dcc.Store(id="traj-preload-store",     data=_PRELOAD_DATA),

    # Written on pause → triggers full-quality figure rebuild.
    dcc.Store(id="pause-rebuild-store"),

    # ── Dummy outputs for clientside callbacks ───────────────────────────
    html.Div(id="artemis-init-dummy",  style={"display": "none"}),

    # ── Header ───────────────────────────────────────────────────────────
    _build_header(),

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
            _build_scrubber(),
        ], className="panel-trajectory-viz"),
    ], className="panel panel-trajectory"),

    # ── Telemetry panels ─────────────────────────────────────────────────
    _build_telemetry_grid(),

], className="dashboard")



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

        // Update dot immediately — don't wait for renderFrame round-trip.
        // React may reset the class during reconciliation; renderFrame will
        // re-correct it, but this ensures the highlight lands on click.
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



# ═══════════════════════════════════════════════════════════════════════════
#  SERVER CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════

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
def on_playback_pause(running_state, frame_state, phase_idx):
    """
    On PLAY  (running=True)  → no-op.
    On PAUSE (running=False) → write paused frame timestamp + scrubber context.
    """
    if not running_state or running_state.get("running"):
        raise PreventUpdate

    frame_idx  = (frame_state or {}).get("frame_idx", 0)
    timestamps = _PRELOAD_DATA.get("timestamps", [])

    if not timestamps:
        raise PreventUpdate

    return {
        "dt_str":    timestamps[frame_idx],
        "phase_idx": phase_idx or 0,
    }


# ── Full-quality figure rebuild ────────────────────────────────────
@app.callback(
    Output("trajectory-content", "children"),
    Input("phase-store",         "data"),   # scrubber dot click
    Input("pause-rebuild-store", "data"),   # playback paused
    Input("resize-store",        "data"),
)
def update_trajectory(phase_idx, pause_data, _resize):
    """
    Rebuilds the full-quality trajectory figure on phase click or pause.

    phase-store         → rebuild at the phase's canonical timestamp
    pause-rebuild-store → rebuild at the exact frame where playback stopped
    Initial load (trigger=None) → treated as phase-store, phase 0
    """
    trigger = ctx.triggered_id

    scrubber_phases = get_scrubber_phases()
    all_phases      = get_phases()

    if trigger == "pause-rebuild-store" and pause_data:
        scrubber_idx = pause_data.get("phase_idx", 0)
        phase_key    = scrubber_phases[scrubber_idx]["key"]
        global_idx   = next(i for i, p in enumerate(all_phases) if p["key"] == phase_key)
        override_dt  = _datetime.fromisoformat(pause_data["dt_str"])
        fig = build_trajectory_fig(global_idx, override_dt=override_dt)
    else:
        scrubber_idx = phase_idx or 0
        phase_key    = scrubber_phases[scrubber_idx]["key"]
        global_idx   = next(i for i, p in enumerate(all_phases) if p["key"] == phase_key)
        fig = build_trajectory_fig(global_idx)

    return _trajectory_content(fig)


@app.callback(
    Output("telemetry-grid", "children"),
    Input("phase-store",         "data"),
    Input("pause-rebuild-store", "data"),
    prevent_initial_call=False,
)
def update_telemetry(phase_idx, pause_data):
    """
    Rebuild all four telemetry panels on phase-click or playback pause.

    Trigger priority:
      pause-rebuild-store — uses exact paused dt_str for frame accuracy
      phase-store         — uses canonical phase timestamp
      initial load        — falls through to phase 0
    """
    triggered = ctx.triggered_id

    if triggered == "pause-rebuild-store" and pause_data and pause_data.get("dt_str"):
        dt_utc = _datetime.fromisoformat(pause_data["dt_str"])
    else:
        phases = get_scrubber_phases()
        idx = phase_idx if phase_idx is not None else 0
        idx = max(0, min(idx, len(phases) - 1))
        dt_utc = phases[idx]["datetime_utc"]

    values      = get_telemetry_at(dt_utc)
    current_pct = get_frame_pct(dt_utc)

    return [
        _build_telemetry_panel(
            group_key    = key,
            group        = grp,
            values_dict  = values,
            current_pct  = current_pct,
            series_stats = _SERIES_STATS,
        )
        for key, grp in PANEL_GROUPS.items()
    ]



# ═══════════════════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, port=8050, threaded=False)