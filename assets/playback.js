// assets/playback.js
//
// Hot playback loop — React-free hot path.
//
// Architecture:
//   window._artemisState  { running, frame_idx, preloaded }
//     Written by thin Dash clientside callbacks (init, play/pause toggle,
//     scrubber-dot reset). Read here every rAF tick.
//
//   window._artemisFrame  int
//     Written here every tick. Future telemetry hooks read this without
//     coupling to Dash stores.
//
// Timing:
//   Accumulate wall-clock elapsed ms each rAF tick.
//   Advance floor(elapsed / target_ms_per_frame) data frames.
//   True 1hr/sec independent of monitor fps or React scheduling.

(function () {
    "use strict";

    // Cancel any loop left over from a previous script evaluation.
    // Dash can re-evaluate this IIFE when preload data changes — without
    // this guard a second loop starts alongside the first.
    if (window._artemisRafId) {
        cancelAnimationFrame(window._artemisRafId);
        window._artemisRafId = null;
    }

    // ── Geometry from config bridge (window._artemisConfig) ──────────────
    // Populated by index_string.py before this script loads.
    // Computed once at IIFE init — not per-frame.
    var _cfg             = window._artemisConfig;
    var SVG_VW           = _cfg.KPI_SVG_WIDTH;
    var DIAL_R           = _cfg.DIAL_RADIUS;
    var DIAL_CX          = SVG_VW / 2;
    var DIAL_ANG_MIN     = _cfg.DIAL_ANGLE_MIN;
    var DIAL_ANG_MAX     = _cfg.DIAL_ANGLE_MAX;
    var DIAL_ANG_MIN_RAD = DIAL_ANG_MIN * Math.PI / 180;
    var DIAL_ANG_MAX_RAD = DIAL_ANG_MAX * Math.PI / 180;
    var DIAL_ANG_RANGE   = DIAL_ANG_MIN - DIAL_ANG_MAX;
    var DIAL_CY          = (_cfg.KPI_SVG_HEIGHT + DIAL_R + DIAL_R * Math.sin(DIAL_ANG_MAX_RAD)) / 2;

    // ── rAF timing state ─────────────────────────────────────────────────
    var _lastTs  = null;
    var _elapsed = 0;

    // ── Moon circle helper ────────────────────────────────────────────────
    // Parametric circle: 120 segments, closed (first == last point).
    function circleXY(cx, cy, r) {
        var n    = 120;
        var x    = new Array(n + 1);
        var y    = new Array(n + 1);
        var step = (2 * Math.PI) / n;
        for (var i = 0; i <= n; i++) {
            var t = i * step;
            x[i]  = cx + r * Math.cos(t);
            y[i]  = cy + r * Math.sin(t);
        }
        return [x, y];
    }

    // ── Per-frame Plotly update ───────────────────────────────────────────
    function renderFrame(fi, preloaded) {

        var graphDiv = document.querySelector('.js-plotly-plot');
        if (!graphDiv || !graphDiv.layout || !graphDiv.layout.meta) return;

        var meta  = graphDiv.layout.meta;
        var spIdx = meta.trace_idx.marker;
        var pgIdx = meta.trace_idx.past_glow;
        var pcIdx = meta.trace_idx.past_core;

        if (spIdx === undefined || pgIdx === undefined || pcIdx === undefined) return;

        var rx  = preloaded.rx;
        var ry  = preloaded.ry;
        var spd = (preloaded.speed[fi] || 0).toFixed(3);

        // ── Past arc + spacecraft (single restyle) ───────────────────────
        var arcX = rx.slice(0, fi + 1);
        var arcY = ry.slice(0, fi + 1);

        Plotly.restyle(graphDiv, {
            x: [[rx[fi]], arcX, arcX],
            y: [[ry[fi]], arcY, arcY]
        }, [spIdx, pgIdx, pcIdx]);

        // ── Arc event badge ───────────────────────────────────────────────
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
                eventText    = m.short + ' \u00b7 ' + m.label;
                eventX       = m.rx;
                eventY       = m.ry;
                eventVisible = true;
            }
        }

        // ── Orion callout + event badge (single relayout) ────────────────
        Plotly.relayout(graphDiv, {
            'annotations[0].x':       rx[fi],
            'annotations[0].y':       ry[fi],
            'annotations[0].text':    'ORION<br>' + spd + ' km/s',
            'annotations[1].visible': eventVisible,
            'annotations[1].text':    eventText,
            'annotations[1].x':       eventX,
            'annotations[1].y':       eventY
        });

        // ── Future arc — hidden during playback ──────────────────────────
        var futureStart = meta.trace_idx.future_start;
        var futureEnd   = meta.trace_idx.future_end;
        if (futureEnd > futureStart) {
            var futureIndices = [];
            for (var k = futureStart; k < futureEnd; k++) {
                futureIndices.push(k);
            }
            Plotly.restyle(graphDiv, {opacity: 0}, futureIndices);
        }

        // ── Moon position + visibility ────────────────────────────────────
        var moonStart = meta.trace_idx.moon_start;
        var labelIdx  = meta.trace_idx.label;

        if (moonStart !== undefined && labelIdx !== undefined) {
            var moonX     = preloaded.moon_rx[fi];
            var moonY     = preloaded.moon_ry[fi];
            var moonRadii = preloaded.moon_radii;
            var yRange    = preloaded.moon_y_range;
            var inView    = moonY >= (yRange[0] - moonRadii[0])
                         && moonY <= (yRange[1] + moonRadii[0]);
            var moonOp    = inView ? 1 : 0;

            var moonXs   = [];
            var moonYs   = [];
            var moonOps  = [];
            var moonIdxs = [];
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

            var MR  = moonRadii[3];
            var mlx = inView ? moonX : NaN;
            var mly = inView ? moonY - MR * preloaded.moon_label_y_mult : NaN;
            Plotly.restyle(graphDiv,
                {x: [[0.0, mlx]], y: [[preloaded.earth_label_y, mly]]},
                [labelIdx]
            );
        }

        // ── Arc marker dots — filter to past events per frame ─────────────
        var arcStart = meta.trace_idx.arc_markers_start;
        if (arcStart !== undefined) {
            var burnX  = [], burnY  = [];
            var coastX = [], coastY = [];
            var otherX = [], otherY = [];

            for (var i = 0; i < markers.length; i++) {
                var mk = markers[i];
                if (mk.frame_idx > fi) { continue; }
                if      (mk.category === 'burn')  { burnX.push(mk.rx);  burnY.push(mk.ry);  }
                else if (mk.category === 'coast') { coastX.push(mk.rx); coastY.push(mk.ry); }
                else                              { otherX.push(mk.rx); otherY.push(mk.ry); }
            }

            Plotly.restyle(graphDiv,
                {x: [burnX, coastX, otherX], y: [burnY, coastY, otherY]},
                [arcStart, arcStart + 1, arcStart + 2]
            );
        }

        // ── Scrubber dot highlight (direct DOM) ───────────────────────────
        var scrubberFrames = preloaded.scrubber_frame_indices || [];
        var activeDot      = 0;
        for (var j = 0; j < scrubberFrames.length; j++) {
            if (fi >= scrubberFrames[j]) { activeDot = j; }
        }
        document.querySelectorAll('.scrubber-dot').forEach(function (dot, idx) {
            dot.className = (idx === activeDot)
                ? 'scrubber-dot active'
                : 'scrubber-dot';
        });

        // ── Telemetry tile updates ────────────────────────────────────────
        var telem       = preloaded.telemetry;
        var telemMeta   = preloaded.telemetry_meta;
        var seriesStats = preloaded.series_stats || {};

        if (telem && telemMeta) {
            var totalFrames = preloaded.total_frames || 1;
            var needleX     = ((fi / Math.max(totalFrames - 1, 1)) * SVG_VW).toFixed(1);
            var needleXStr  = String(needleX);

            for (var t = 0; t < telemMeta.length; t++) {
                var meta   = telemMeta[t];
                var col    = meta.column;
                var series = telem[col];

                if (!series) { continue; }

                var raw = series[fi];
                if (raw === undefined || raw === null) { continue; }

                // ── Value span (all viz types) ────────────────────────────
                var valEl = document.getElementById('tile-val--' + col);
                if (valEl) {
                    var formatted;
                    if (meta.locale) {
                        formatted = Number(raw).toLocaleString('en-US', {
                            minimumFractionDigits: meta.decimals,
                            maximumFractionDigits: meta.decimals,
                        });
                    } else {
                        formatted = Number(raw).toFixed(meta.decimals);
                    }
                    valEl.textContent = formatted;
                }

                // ── Sub-viz update — branch by viz_type ──────────────────
                var vt    = meta.viz_type;
                var stats = seriesStats[col] || {};

                if (vt === 'sparkline') {
                    var needleEl = document.getElementById('tile-needle--' + col);
                    if (needleEl) {
                        needleEl.setAttribute('x1', needleXStr);
                        needleEl.setAttribute('x2', needleXStr);
                    }

                } else if (vt === 'bar') {
                    var barEl = document.getElementById('tile-bar--' + col);
                    if (barEl) {
                        var fillW;
                        if (meta.log_scale) {
                            var sMinL    = Math.max(stats.min || 1e-300, 1e-300);
                            var sMaxL    = Math.max(stats.max || 1,      1e-9);
                            var logMin   = Math.log(sMinL) / Math.LN10;
                            var logMax   = Math.log(sMaxL) / Math.LN10;
                            var logVal   = Math.log(Math.max(raw, 1e-300)) / Math.LN10;
                            var logRange = Math.max(logMax - logMin, 1e-9);
                            fillW = Math.max(0, Math.min(SVG_VW, ((logVal - logMin) / logRange) * SVG_VW));
                        } else {
                            var sMaxL = Math.max(Math.abs(stats.max || 1), 1e-9);
                            fillW = Math.max(0, Math.min(SVG_VW, (raw / sMaxL) * SVG_VW));
                        }
                        barEl.setAttribute('width', fillW.toFixed(2));
                    }

                } else if (vt === 'bidir_bar') {
                    var bidirEl = document.getElementById('tile-bidir--' + col);
                    if (bidirEl) {
                        var mid       = SVG_VW / 2;
                        var center    = meta.bidir_center != null ? meta.bidir_center : 0;
                        var deviation = raw - center;
                        var devPos    = Math.max((stats.max || 0) - center, 1e-9);
                        var devNeg    = Math.max(center - (stats.min || 0), 1e-9);
                        var bFillW, bFillX, bFillColor;

                        if (deviation >= 0) {
                            bFillW     = Math.min((deviation / devPos) * mid, mid);
                            bFillX     = mid;
                            bFillColor = 'var(--panel-accent)';
                        } else {
                            bFillW     = Math.min((Math.abs(deviation) / devNeg) * mid, mid);
                            bFillX     = mid - bFillW;
                            bFillColor = meta.neg_color || 'var(--panel-accent)';
                        }

                        bidirEl.setAttribute('x',     bFillX.toFixed(2));
                        bidirEl.setAttribute('width', bFillW.toFixed(2));
                        bidirEl.style.fill = bFillColor;
                    }

                } else if (vt === 'dial') {
                    var dialEl = document.getElementById('tile-dial--' + col);
                    if (dialEl) {
                        var valMin  = meta.dial_val_min != null ? meta.dial_val_min : 0;
                        var valMax  = meta.dial_val_max != null ? meta.dial_val_max : 90;
                        var dRange  = Math.max(valMax - valMin, 1e-9);
                        var frac    = Math.max(0, Math.min(1, (raw - valMin) / dRange));
                        var currDeg = DIAL_ANG_MIN - frac * DIAL_ANG_RANGE;
                        var currRad = currDeg * Math.PI / 180;

                        var x0 = DIAL_CX + DIAL_R * Math.cos(DIAL_ANG_MIN_RAD);
                        var y0 = DIAL_CY - DIAL_R * Math.sin(DIAL_ANG_MIN_RAD);
                        var xc = DIAL_CX + DIAL_R * Math.cos(currRad);
                        var yc = DIAL_CY - DIAL_R * Math.sin(currRad);

                        var d;
                        if (frac < 0.005) {
                            d = 'M ' + x0.toFixed(2) + ',' + y0.toFixed(2) +
                                ' L ' + x0.toFixed(2) + ',' + y0.toFixed(2);
                        } else {
                            d = 'M ' + x0.toFixed(2) + ',' + y0.toFixed(2) +
                                ' A ' + DIAL_R + ' ' + DIAL_R + ' 0 0 1 ' +
                                xc.toFixed(2) + ',' + yc.toFixed(2);
                        }
                        dialEl.setAttribute('d', d);
                    }

                }
                // value_only: no sub-viz element — nothing to update
            }
        }

        // ── Status bar — GMT · MET · Phase ───────────────────────────────
        var ts         = preloaded.timestamps[fi];
        var frameDate  = new Date(ts + 'Z');
        var launchDate = new Date(preloaded.launch_iso + 'Z');

        function pad2(n) { return String(n).padStart(2, '0'); }
        function pad3(n) { return String(n).padStart(3, '0'); }

        var year   = frameDate.getUTCFullYear();
        var doy    = Math.floor(
                         (frameDate - new Date(Date.UTC(year, 0, 1))) / 86400000
                     ) + 1;
        var gmtStr = year + ':' + pad3(doy)                       + ':' +
                     pad2(frameDate.getUTCHours())                 + ':' +
                     pad2(frameDate.getUTCMinutes())               + ':' +
                     pad2(frameDate.getUTCSeconds());

        var metSec = Math.floor((frameDate - launchDate) / 1000);
        var metD   = Math.floor(metSec / 86400);
        var metH   = Math.floor((metSec % 86400) / 3600);
        var metM   = Math.floor((metSec % 3600)  / 60);
        var metS   = metSec % 60;
        var metStr = pad2(metD) + 'T ' +
                     pad2(metH) + ':' + pad2(metM) + ':' + pad2(metS);

        var statusPhases = preloaded.status_phases || [];
        var phaseLabel   = '';
        for (var p = 0; p < statusPhases.length; p++) {
            if (fi >= statusPhases[p].frame_idx) {
                phaseLabel = statusPhases[p].status_label;
            }
        }

        var statusEl = document.getElementById('status-text');
        if (statusEl) {
            statusEl.textContent =
                'GMT ' + gmtStr + ' \u00b7 MET ' + metStr + ' \u00b7 ' + phaseLabel;
        }
    }

    // ── rAF loop ──────────────────────────────────────────────────────────
    function loop(ts) {
        window._artemisRafId = requestAnimationFrame(loop);

        var state = window._artemisState;

        // No-op until initialized. Reset timing so the first tick after
        // resume doesn't try to "catch up" elapsed idle time.
        if (!state || !state.preloaded) {
            _lastTs  = null;
            _elapsed = 0;
            return;
        }

        // Timing reset requested by scrubber dot click — clear accumulated
        // elapsed before the loop resumes so it doesn't jump frames.
        if (state.resetTiming) {
            state.resetTiming = false;
            _lastTs  = null;
            _elapsed = 0;
        }

        // Paused — drain any forced render request (e.g. scrubber click),
        // then bail. Keeps the view responsive without running the full loop.
        if (!state.running) {
            if (state.needsRender) {
                state.needsRender = false;
                renderFrame(state.frame_idx, state.preloaded);
            }
            _lastTs  = null;
            _elapsed = 0;
            return;
        }

        // First tick after resume: anchor timestamp, don't advance yet.
        if (_lastTs === null) {
            _lastTs = ts;
            return;
        }

        _elapsed += ts - _lastTs;
        _lastTs   = ts;

        var targetMs    = state.preloaded.target_ms_per_frame;
        var framesToAdv = Math.floor(_elapsed / targetMs);
        if (framesToAdv === 0) return;

        _elapsed -= framesToAdv * targetMs;

        var fi    = state.frame_idx + framesToAdv;
        var total = state.preloaded.total_frames;

        if (fi >= total) {
            fi            = total - 1;
            state.running = false;     // auto-stop at end of mission
        }

        state.frame_idx      = fi;
        window._artemisFrame = fi;

        renderFrame(fi, state.preloaded);
    }

    // Kick the loop immediately. No-ops until _artemisState.running = true.
    window._artemisRafId = requestAnimationFrame(loop);

}());