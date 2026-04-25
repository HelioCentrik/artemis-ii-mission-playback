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
        requestAnimationFrame(loop);

        var state = window._artemisState;

        // No-op until initialized and running. Reset timing so the first
        // tick after resume doesn't try to "catch up" elapsed idle time.
        if (!state || !state.running || !state.preloaded) {
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
    requestAnimationFrame(loop);

}());