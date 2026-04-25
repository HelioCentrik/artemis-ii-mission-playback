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
#     toggle-running     : playback-btn click  → playback-running-store
#     advance-frame      : interval tick        → playback-frame-store (no-ops if paused)
#     render-btn-state   : playback-running-store → btn icon + className
#     update-frame-viz   : playback-frame-store → Plotly.restyle/relayout via DOM id
#                          (Spacecraft, arc, annotations, scrubber dot highlight)
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
)
from app.db import get_con
from app.phases import get_scrubber_phases, get_phases, get_arc_marker_phases
from app.utils import rotate_2d
from app.index_string import INDEX_STRING
from app.trajectory import build_trajectory_fig, build_starfield_svg, get_moon_preload_data

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
        "moon_rx":                  moon_rx.tolist(),
        "moon_ry":                  moon_ry.tolist(),
        "status_phases":            status_phases,                        # ← add
        "launch_iso":               LAUNCH_TIME.replace(" ", "T"),        # ← add
        **get_moon_preload_data(),
    }


# Runs at import time — before any callback or layout is evaluated.
_PRELOAD_DATA = _build_preload_data()


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


def _build_telemetry_panel(group_key, group):
    return html.Div([
        html.Div([
            html.Div([
                html.Span(className="accent-dot"),
                html.Span(group["label"]),
            ], className="telemetry-panel-label"),
            html.Span(group["code"], className="telemetry-panel-code"),
        ], className="telemetry-panel-header"),
        html.Div([
            html.Div([
                html.Div([
                    html.Span("---", className="tile-label"),
                    html.Span("---", className="tile-unit"),
                ], className="tile-header"),
                html.Div("--", className="tile-value"),
                html.Div(className="tile-sparkline"),
            ], className="tile"),
            html.Div([
                html.Div([
                    html.Span("---", className="tile-label"),
                    html.Span("---", className="tile-unit"),
                ], className="tile-header"),
                html.Div("--", className="tile-value"),
                html.Div(className="tile-sparkline"),
            ], className="tile"),
        ], className="tile-grid"),
    ], className=f"panel telemetry-panel telemetry-panel--{group_key}")


def _build_telemetry_grid():
    return html.Div(
        [_build_telemetry_panel(key, grp) for key, grp in PANEL_GROUPS.items()],
        className="telemetry-grid",
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

    # Preload baked in at startup — immediately available, no callback needed.
    dcc.Store(id="traj-preload-store",     data=_PRELOAD_DATA),

    # Written on pause → triggers full-quality figure rebuild.
    dcc.Store(id="pause-rebuild-store"),

    # ── Interval ────────────────────────────────────────────────────────
    dcc.Interval(
        id="playback-interval",
        interval=PLAYBACK_INTERVAL_MS,
        disabled=False,         # always ticking; advance-frame no-ops when paused
    ),

    # ── Dummy output for clientside frame-viz callback ───────────────────
    html.Div(id="playback-viz-dummy", style={"display": "none"}),

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

# ── Toggle running on button click ──────────────────────────────────────────
app.clientside_callback(
    """function(n_clicks, state) {
        if (!n_clicks || !state) return window.dash_clientside.no_update;
        return {running: !state.running};
    }""",
    Output("playback-running-store", "data"),
    Input("playback-btn", "n_clicks"),
    State("playback-running-store", "data"),
    prevent_initial_call=True,
)

# ── Advance frame on each interval tick ─────────────────────────────────────
app.clientside_callback(
    """function(n_intervals, runState, frameState, preloaded) {
        if (!runState || !runState.running || !preloaded || !frameState) {
            return window.dash_clientside.no_update;
        }
        var next = frameState.frame_idx + preloaded.frames_per_tick;
        if (next >= preloaded.total_frames) {
            return {frame_idx: preloaded.total_frames - 1};
        }
        return {frame_idx: next};
    }""",
    Output("playback-frame-store", "data"),
    Input("playback-interval", "n_intervals"),
    State("playback-running-store", "data"),
    State("playback-frame-store", "data"),
    State("traj-preload-store", "data"),
    prevent_initial_call=True,
)

# ── Reset frame when scrubber dot is clicked ────────────────────────────────
app.clientside_callback(
    """function(phaseIdx, preloaded) {
        if (phaseIdx === null || phaseIdx === undefined || !preloaded)
            return window.dash_clientside.no_update;
        var frames = preloaded.scrubber_frame_indices || [];
        var fi = (frames[phaseIdx] !== undefined) ? frames[phaseIdx] : 0;
        return {frame_idx: fi};
    }""",
    Output("playback-frame-store", "data", allow_duplicate=True),
    Input("phase-store", "data"),
    State("traj-preload-store", "data"),
    prevent_initial_call=True,
)

# ── Sync button icon + className ─────────────────────────────────────────────
app.clientside_callback(
    """function(state) {
        if (!state) return ["▶", "playback-btn"];
        return [
            state.running ? "⏸" : "▶",
            state.running ? "playback-btn playing" : "playback-btn"
        ];
    }""",
    Output("playback-btn", "children"),
    Output("playback-btn", "className"),
    Input("playback-running-store", "data"),
)

# ── Per-frame figure update (clientside, zero round-trips) ──
#
#   Fires on every playback-frame-store change. Directly manipulates the live
#   Plotly graph via Plotly.restyle / Plotly.relayout using trace indices from
#   fig.layout.meta (embedded by build_trajectory_fig).
#
#   What it updates each tick:
#     Past arc glow + core x/y sliced to current frame
#     Spacecraft marker position + Orion speed callout annotation
#     Arc event badge annotation (visible, text, x, y)
#      Scrubber dot highlight (direct DOM className swap)
#
#   Graph div resolution:
#     dcc.Graph(id="trajectory-graph") — Plotly attaches ._fullData to the
#     element it manages. Try the outer container first; fall back to the
#     inner .js-plotly-plot child if Plotly mounted on a child div instead.
#
#   Plotly call budget per tick:
#     1× Plotly.restyle  — spacecraft marker + 2 arc traces batched
#     1× Plotly.relayout — both annotations batched
app.clientside_callback(
    """
    function(frameState, preloaded) {

        // ── Moon circle helper ────────────────────────────────────────────────
        // Parametric circle: 120 segments, closed (first == last point).
        function circleXY(cx, cy, r) {
            var n = 120, x = new Array(n + 1), y = new Array(n + 1);
            var step = (2 * Math.PI) / n;
            for (var i = 0; i <= n; i++) {
                var t = i * step;
                x[i] = cx + r * Math.cos(t);
                y[i] = cy + r * Math.sin(t);
            }
            return [x, y];
        }

        // ── Guards ───────────────────────────────────────────────────────
        if (!frameState || !preloaded) {
            return window.dash_clientside.no_update;
        }
        var fi = frameState.frame_idx;
        if (fi === undefined || fi === null) {
            return window.dash_clientside.no_update;
        }

        // ── Resolve the live Plotly graph element ─────────────────────────
        var graphDiv = document.querySelector('.js-plotly-plot');
        if (!graphDiv || !graphDiv.layout || !graphDiv.layout.meta) {
            return window.dash_clientside.no_update;
        }

        var meta  = graphDiv.layout.meta;
        var spIdx = meta.trace_idx.marker;
        var pgIdx = meta.trace_idx.past_glow;
        var pcIdx = meta.trace_idx.past_core;

        if (spIdx === undefined || pgIdx === undefined || pcIdx === undefined) {
            return window.dash_clientside.no_update;
        }

        var rx  = preloaded.rx;
        var ry  = preloaded.ry;
        var spd = (preloaded.speed[fi] || 0).toFixed(3);

        // ── Past arc + spacecraft (single restyle) ──────
        var arcX = rx.slice(0, fi + 1);
        var arcY = ry.slice(0, fi + 1);

        Plotly.restyle(graphDiv, {
            x: [[rx[fi]], arcX, arcX],
            y: [[ry[fi]], arcY, arcY]
        }, [spIdx, pgIdx, pcIdx]);

        // ── Arc event badge ───────────────────────────────
        var windowFrames = preloaded.annotation_window_frames || 180;
        var markers      = preloaded.arc_markers || [];

        var eventVisible = false;
        var eventText    = '';
        var eventX       = 0;
        var eventY       = 0;
        var bestDist     = Infinity;

        for (var i = 0; i < markers.length; i++) {
            var m       = markers[i];
            var absDist = Math.abs(fi - m.frame_idx);
            if (absDist <= windowFrames && absDist < bestDist) {
                bestDist     = absDist;
                eventText    = m.short + ' · ' + m.label;
                eventX       = m.rx;
                eventY       = m.ry;
                eventVisible = true;
            }
        }

        // ── Orion callout + event badge (single relayout) ────────
        Plotly.relayout(graphDiv, {
            'annotations[0].x':       rx[fi],
            'annotations[0].y':       ry[fi],
            'annotations[0].text':    'ORION<br>' + spd + ' km/s',
            'annotations[1].visible': eventVisible,
            'annotations[1].text':    eventText,
            'annotations[1].x':       eventX,
            'annotations[1].y':       eventY
        });
        
        // ── hide future arc during playback ───────────────────────
        var futureStart = meta.trace_idx.future_start;
        var futureEnd   = meta.trace_idx.future_end;
        if (futureEnd > futureStart) {
            var futureIndices = [];
            for (var k = futureStart; k < futureEnd; k++) {
                futureIndices.push(k);
            }
            Plotly.restyle(graphDiv, {opacity: 0}, futureIndices);
        }
        
        // ── Moon position + visibility ───────────────────────────────
        var moonStart  = meta.trace_idx.moon_start;
        var labelIdx   = meta.trace_idx.label;

        if (moonStart !== undefined && labelIdx !== undefined) {
            var moonX      = preloaded.moon_rx[fi];
            var moonY      = preloaded.moon_ry[fi];
            var moonRadii  = preloaded.moon_radii;          // [MG4, MG3, MG2, MR]
            var yRange     = preloaded.moon_y_range;        // [y_lo, y_hi]
            var inView     = moonY >= (yRange[0] - moonRadii[0])
                          && moonY <= (yRange[1] + moonRadii[0]);
            var moonOp     = inView ? 1 : 0;

            // Build x/y/opacity arrays for the 4 Moon body traces.
            var moonXs = [], moonYs = [], moonOps = [], moonIdxs = [];
            for (var k = 0; k < moonRadii.length; k++) {
                var circ = circleXY(moonX, moonY, moonRadii[k]);
                moonXs.push(circ[0]);
                moonYs.push(circ[1]);
                moonOps.push(moonOp);
                moonIdxs.push(moonStart + k);
            }
            Plotly.restyle(graphDiv,
                {x: moonXs, y: moonYs, opacity: moonOps},
                moonIdxs
            );

            // Moon + Earth body labels.
            // Earth label is fixed (Earth never moves); Moon label follows Moon.
            // NaN position = Plotly skips that text point entirely.
            var MR         = moonRadii[3];
            var mlx        = inView ? moonX : NaN;
            var mly        = inView ? moonY - MR * preloaded.moon_label_y_mult : NaN;
            Plotly.restyle(graphDiv,
                {x: [[0.0, mlx]], y: [[preloaded.earth_label_y, mly]]},
                [labelIdx]
            );
        }
        
        // ── Arc marker dots — filter to past events per frame ─────
        var arcStart = meta.trace_idx.arc_markers_start;
        if (arcStart !== undefined) {
            var burnX = [],  burnY  = [];
            var coastX = [], coastY = [];
            var otherX = [], otherY = [];

            for (var i = 0; i < markers.length; i++) {
                var m = markers[i];
                if (m.frame_idx > fi) { continue; }
                if      (m.category === 'burn')  { burnX.push(m.rx);  burnY.push(m.ry);  }
                else if (m.category === 'coast') { coastX.push(m.rx); coastY.push(m.ry); }
                else                             { otherX.push(m.rx); otherY.push(m.ry); }
            }

            Plotly.restyle(graphDiv,
                {x: [burnX, coastX, otherX], y: [burnY, coastY, otherY]},
                [arcStart, arcStart + 1, arcStart + 2]
            );
        }

        // ── Scrubber dot highlight (direct DOM) ───────────
        var scrubberFrames = preloaded.scrubber_frame_indices || [];
        var activeDot      = 0;
        for (var j = 0; j < scrubberFrames.length; j++) {
            if (fi >= scrubberFrames[j]) { activeDot = j; }
        }
        document.querySelectorAll('.scrubber-dot').forEach(function(dot, idx) {
            dot.className = (idx === activeDot) ? 'scrubber-dot active' : 'scrubber-dot';
        });

                // ── Status bar — GMT · MET · Phase ───────────────────────────
        var ts         = preloaded.timestamps[fi];
        var frameDate  = new Date(ts + 'Z');
        var launchDate = new Date(preloaded.launch_iso + 'Z');

        function pad2(n) { return String(n).padStart(2, '0'); }
        function pad3(n) { return String(n).padStart(3, '0'); }

        // GMT: YYYY:DDD:HH:MM:SS (mission-control day-of-year format)
        var year   = frameDate.getUTCFullYear();
        var doy    = Math.floor((frameDate - new Date(Date.UTC(year, 0, 1))) / 86400000) + 1;
        var gmtStr = year + ':' + pad3(doy) + ':' +
                     pad2(frameDate.getUTCHours())   + ':' +
                     pad2(frameDate.getUTCMinutes()) + ':' +
                     pad2(frameDate.getUTCSeconds());

        // MET: DDT HH:MM:SS (elapsed since SLS liftoff)
        var metSec = Math.floor((frameDate - launchDate) / 1000);
        var metD   = Math.floor(metSec / 86400);
        var metH   = Math.floor((metSec % 86400) / 3600);
        var metM   = Math.floor((metSec % 3600) / 60);
        var metS   = metSec % 60;
        var metStr = pad2(metD) + 'T ' + pad2(metH) + ':' + pad2(metM) + ':' + pad2(metS);

        // Phase label: last status_phase whose frame_idx ≤ fi
        var statusPhases = preloaded.status_phases || [];
        var phaseLabel   = '';
        for (var p = 0; p < statusPhases.length; p++) {
            if (fi >= statusPhases[p].frame_idx) { phaseLabel = statusPhases[p].status_label; }
        }

        var statusEl = document.getElementById('status-text');
        if (statusEl) {
            statusEl.textContent = 'GMT ' + gmtStr + ' · MET ' + metStr + ' · ' + phaseLabel;
        }

        return window.dash_clientside.no_update;
    }
    """,
    Output("playback-viz-dummy", "children"),
    Input("playback-frame-store", "data"),
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


# ── Detect pause, write pause-rebuild-store ────────────────────────
@app.callback(
    Output("pause-rebuild-store", "data"),
    Input("playback-running-store", "data"),
    State("playback-frame-store", "data"),
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
)
def update_trajectory(phase_idx, pause_data):
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


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, port=8050)