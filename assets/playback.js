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
    var SVG_VH           = _cfg.KPI_SVG_HEIGHT;
    var DIAL_R           = _cfg.DIAL_RADIUS;
    var DIAL_CX          = SVG_VW / 2;
    var DIAL_ANG_MIN     = _cfg.DIAL_ANGLE_MIN;
    var DIAL_ANG_MAX     = _cfg.DIAL_ANGLE_MAX;
    var DIAL_ANG_MIN_RAD = DIAL_ANG_MIN * Math.PI / 180;
    var DIAL_ANG_MAX_RAD = DIAL_ANG_MAX * Math.PI / 180;
    var DIAL_ANG_RANGE   = DIAL_ANG_MIN - DIAL_ANG_MAX;
    var DIAL_CY          = (_cfg.KPI_SVG_HEIGHT + DIAL_R + DIAL_R * Math.sin(DIAL_ANG_MAX_RAD)) / 2 + _cfg.DIAL_CY_OFFSET;

    // ── rAF timing state ─────────────────────────────────────────────────
    var _lastTs  = null;
    var _elapsed = 0;

    // ── Shadow geometry cache ─────────────────────────────────────────────
    // Built once from preload data during idle (paused) time before playback.
    // Per-frame hot path becomes pure array lookups — no trig, no allocation.
    var _futureIndices = null;
    var _shadowCache = null;

    function _buildShadowCache(preloaded) {
        if (_shadowCache !== null) return;
        var n  = preloaded.total_frames;
        var ER = preloaded.earth_radius;
        var MR = preloaded.moon_radii[3];
        var ex = new Array(n);
        var ey = new Array(n);
        var mx = new Array(n);
        var my = new Array(n);
        for (var i = 0; i < n; i++) {
            var esd = _shadowHalfDisc(0, 0, ER,
                preloaded.sun_angles[i], preloaded.sun_nz[i]);
            ex[i] = esd[0];
            ey[i] = esd[1];
            var msd = _shadowHalfDisc(
                preloaded.moon_rx[i], preloaded.moon_ry[i], MR,
                preloaded.sun_angles[i], preloaded.sun_nz[i]);
            mx[i] = msd[0];
            my[i] = msd[1];
        }
        _shadowCache = { ex: ex, ey: ey, mx: mx, my: my };
    }

    function _shadowHalfDisc(cx, cy, r, sunAngleDeg, sunNz) {
        var n     = 60;
        var theta = sunAngleDeg * Math.PI / 180;
        var sz    = sunNz;

        var termX = [];
        var termY = [];
        for (var i = 0; i <= n; i++) {
            var t = (i / n) * Math.PI;
            termX.push(cx + r * (-Math.sin(theta) * Math.cos(t) - sz * Math.cos(theta) * Math.sin(t)));
            termY.push(cy + r * ( Math.cos(theta) * Math.cos(t) - sz * Math.sin(theta) * Math.sin(t)));
        }

        var discX = [];
        var discY = [];
        for (var i = 0; i <= n; i++) {
            var ang = (theta - Math.PI / 2) - (i / n) * Math.PI;
            discX.push(cx + r * Math.cos(ang));
            discY.push(cy + r * Math.sin(ang));
        }

        return [termX.concat(discX), termY.concat(discY)];
    }

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
    function renderFrame(fi, preloaded, running, framesToAdv) {

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

        // ── Past arc — extendData on sequential ticks, restyle on reset ──
        //
        // window._artemisArcFrame tracks what frame the arc is drawn through.
        // If fi lands exactly where a sequential advance from that frame would
        // put us, append only the new points (O(framesToAdv)).
        // Any other case — seek, phase jump, pause render, mission restart —
        // falls back to a full restyle (O(fi)), which is correct and rare.
        var _prevArc = window._artemisArcFrame;
        var _sequential = (
            framesToAdv !== undefined &&
            _prevArc    !== undefined &&
            fi === _prevArc + framesToAdv &&
            fi > 0
        );

        if (_sequential) {
            var newX = rx.slice(_prevArc + 1, fi + 1);
            var newY = ry.slice(_prevArc + 1, fi + 1);
            Plotly.extendTraces(graphDiv,
                { x: [newX, newX], y: [newY, newY] },
                [pgIdx, pcIdx]
            );
        } else {
            var arcX = rx.slice(0, fi + 1);
            var arcY = ry.slice(0, fi + 1);
            Plotly.restyle(graphDiv,
                { x: [arcX, arcX], y: [arcY, arcY] },
                [pgIdx, pcIdx]
            );
        }
        window._artemisArcFrame = fi;

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

        // ── Future arc — hidden every running frame (survives server rebuilds) ──
        // Indices cached once to avoid per-frame array allocation.
        var futureStart = meta.trace_idx.future_start;
        var futureEnd   = meta.trace_idx.future_end;
        if (running && futureEnd > futureStart) {
            if (_futureIndices === null) {
                _futureIndices = [];
                for (var k = futureStart; k < futureEnd; k++) {
                    _futureIndices.push(k);
                }
            }
            Plotly.restyle(graphDiv, {opacity: 0}, _futureIndices);
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
            var MR  = moonRadii[3];
            var mlx = inView ? moonX : NaN;
            var mly = inView ? moonY - MR * preloaded.moon_label_y_mult : NaN;

            Plotly.restyle(graphDiv,
                {
                    x:       moonXs.concat([[0.0, mlx]]),
                    y:       moonYs.concat([[preloaded.earth_label_y, mly]]),
                    opacity: moonOps.concat([1])
                },
                moonIdxs.concat([labelIdx])
            );
        }

// ── Spacecraft + shadows — Earth + Moon (one restyle) ────────────
        // Spacecraft batched here since all three update x/y on Plotly traces.
        var earthShadowIdx = meta.trace_idx.earth_shadow;
        var moonShadowIdx  = meta.trace_idx.moon_shadow;

        if (earthShadowIdx !== undefined && _shadowCache) {
            if (moonShadowIdx !== undefined) {
                Plotly.restyle(graphDiv,
                    {x: [[rx[fi]], _shadowCache.ex[fi], _shadowCache.mx[fi]],
                     y: [[ry[fi]], _shadowCache.ey[fi], _shadowCache.my[fi]],
                     opacity: [1, 1, moonOp]},
                    [spIdx, earthShadowIdx, moonShadowIdx]
                );
            } else {
                Plotly.restyle(graphDiv,
                    {x: [[rx[fi]], _shadowCache.ex[fi]],
                     y: [[ry[fi]], _shadowCache.ey[fi]],
                     opacity: [1, 1]},
                    [spIdx, earthShadowIdx]
                );
            }
        }

        // ── Arc marker dots — filter to past events per frame ─────────────
        var arcStart = meta.trace_idx.arc_markers_start;
        if (arcStart !== undefined) {
            var burnX  = [], burnY  = [], burnCD  = [];
            var coastX = [], coastY = [], coastCD = [];
            var otherX = [], otherY = [], otherCD = [];

            for (var i = 0; i < markers.length; i++) {
                var mk = markers[i];
                if (mk.frame_idx > fi) { continue; }
                var cd = [mk.short, mk.label, mk.met || '', mk.rg_km || 0];
                if      (mk.category === 'burn')  { burnX.push(mk.rx);  burnY.push(mk.ry);  burnCD.push(cd);  }
                else if (mk.category === 'coast') { coastX.push(mk.rx); coastY.push(mk.ry); coastCD.push(cd); }
                else                              { otherX.push(mk.rx); otherY.push(mk.ry); otherCD.push(cd); }
            }

            Plotly.restyle(graphDiv,
                {x: [burnX, coastX, otherX], y: [burnY, coastY, otherY], customdata: [burnCD, coastCD, otherCD]},
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
                    var pastEl = document.getElementById('tile-sparkline-past--' + col);
                    var starEl = document.getElementById('tile-star--' + col);
                    if (pastEl && starEl) {

                        // ── One-time init ─────────────────────────────────
                        // Skipped if _totalLen already set — re-runs automatically
                        // after a Dash rebuild since new elements carry no _totalLen.
                        if (!pastEl._totalLen) {
                            var tl = pastEl.getTotalLength();
                            if (tl > 0) {
                                pastEl._totalLen = tl;
                                pastEl.setAttribute('stroke-dasharray', tl.toFixed(2));

                                // Parse points string — avoids SVGPointList API.
                                // Produces same cumulative lengths as Python's
                                // _approx_path_length / _star_and_offset.
                                var tokens  = (pastEl.getAttribute('points') || '').trim().split(/\s+/);
                                var cum     = [0.0];
                                var prevX   = null, prevY = null;
                                for (var k = 0; k < tokens.length; k++) {
                                    var xy = tokens[k].split(',');
                                    var bx = parseFloat(xy[0]);
                                    var by = parseFloat(xy[1]);
                                    if (prevX !== null) {
                                        var ddx = bx - prevX, ddy = by - prevY;
                                        cum.push(cum[cum.length - 1] + Math.sqrt(ddx * ddx + ddy * ddy));
                                    }
                                    prevX = bx; prevY = by;
                                }
                                pastEl._cumLengths = cum;

                                // Correct ry: preserveAspectRatio="none" scales x and y
                                // independently. Height is a fixed CSS px value == SVG_VH
                                // so y-scale is 1.0 — only x-scale varies with tile width.
                                var svgRect = pastEl.ownerSVGElement.getBoundingClientRect();
                                if (svgRect.width > 0 && svgRect.height > 0) {
                                    var rx = parseFloat(starEl.getAttribute('rx'));
                                    starEl.setAttribute('ry',
                                        (rx * svgRect.width * SVG_VH / (svgRect.height * SVG_VW)).toFixed(3));
                                }
                            }
                        }

                        // ── Per-tick ──────────────────────────────────────
                        if (pastEl._totalLen && pastEl._cumLengths) {
                            var cum2      = pastEl._cumLengths;
                            var pct2      = parseFloat(needleX) / SVG_VW;
                            var idx2      = Math.min(Math.round(pct2 * (cum2.length - 1)), cum2.length - 1);
                            var revealLen = cum2[idx2];

                            pastEl.setAttribute('stroke-dashoffset',
                                (pastEl._totalLen - revealLen).toFixed(2));

                            var pt = pastEl.getPointAtLength(revealLen);
                            starEl.setAttribute('cx', pt.x.toFixed(2));
                            starEl.setAttribute('cy', pt.y.toFixed(2));
                        }
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
                        var mid       = SVG_VW * (meta.bidir_mid != null ? meta.bidir_mid : 0.5);
                        var rightW    = SVG_VW - mid;
                        var center    = meta.bidir_center != null ? meta.bidir_center : 0;
                        var deviation = raw - center;
                        var devPos    = Math.max((stats.max || 0) - center, 1e-9);
                        var devNeg    = Math.max(center - (stats.min || 0), 1e-9);
                        var bFillW, bFillX, bFillColor;

                        if (deviation >= 0) {
                            bFillW     = Math.min((deviation / devPos) * rightW, rightW);
                            bFillX     = mid;
                            bFillColor = meta.pos_color || 'var(--panel-accent)';
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

        // ── Seek indicator — tracks current frame position on scrubber track ──
        var indicator = document.getElementById('scrubber-seek-indicator');
        if (indicator) {
            var pct = fi / (preloaded.total_frames - 1) * 100;
            indicator.style.left = pct.toFixed(2) + '%';
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


        // Paused — if Dash rebuilt any sparkline tile, re-init on the next
        // tick by forcing needsRender. Detects stale refs via missing _totalLen.
        // Then drain any forced render request and bail.
        if (!state.running) {
            // Build shadow cache during idle time — one-shot, uses paused ticks.
            if (_shadowCache === null && state.preloaded) {
                _buildShadowCache(state.preloaded);
            }
            if (!state.needsRender && state.preloaded && state.preloaded.telemetry_meta) {
                var tmeta = state.preloaded.telemetry_meta;
                for (var si = 0; si < tmeta.length; si++) {
                    if (tmeta[si].viz_type === 'sparkline') {
                        var sEl = document.getElementById(
                            'tile-sparkline-past--' + tmeta[si].column);
                        if (sEl && !sEl._totalLen) {
                            state.needsRender = true;
                            break;
                        }
                    }
                }
            }
            if (state.needsRender) {
                state.needsRender = false;
                // ── Paused branch call site ───────────────────────────────────────
                renderFrame(state.frame_idx, state.preloaded, false);
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
            fi                = total - 1;
            state.running     = false;        // auto-stop at end of mission
            state.needsRender = true;         // drain into paused-branch render

            var endBtn = document.getElementById('playback-btn');
            if (endBtn) {
                endBtn.textContent = '\u21ba'; // ↺
                endBtn.className   = 'playback-btn ended';
            }
        }

        state.frame_idx      = fi;
        window._artemisFrame = fi;

        // ── Running branch call site ──────────────────────────────────────
        renderFrame(fi, state.preloaded, true, framesToAdv);
    }

    // Kick the loop immediately. No-ops until _artemisState.running = true.
    window._artemisRafId = requestAnimationFrame(loop);


        // ── Scrubber drag/click seek ──────────────────────────────────────────
    //
    // mousedown on .scrubber-track starts a seek. mousemove/mouseup are
    // registered on document so the drag doesn't break if the cursor leaves
    // the track bounds. renderFrame runs live during drag (rAF only — no
    // server round-trip). set_props fires once on mouseup to trigger the
    // full-quality server rebuild.

    var _isDragging = false;

    function _pctFromEvent(e, track) {
        var rect = track.getBoundingClientRect();
        return Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    }

    function _frameIdxFromPct(pct, totalFrames) {
        return Math.round(pct * (totalFrames - 1));
    }

    function _activeDotFromFrame(fi, scrubberFrameIndices) {
        // Walk forward, keep the last index whose frame is <= fi.
        var active = 0;
        for (var i = 0; i < scrubberFrameIndices.length; i++) {
            if (scrubberFrameIndices[i] <= fi) active = i;
        }
        return active;
    }

    function _applySeek(fi) {
        var state = window._artemisState;
        if (!state || !state.preloaded) return;

        state.frame_idx   = fi;
        state.resetTiming = true;   // prevents frame-jump when drag ends + play resumes

        // Restore play button if mission had ended.
        var btn = document.getElementById('playback-btn');
        if (btn && btn.textContent === '\u21ba') {
            btn.textContent = '\u25b6';
            btn.className   = 'playback-btn';
        }

        // Update dot highlight.
        var dotActive = _activeDotFromFrame(
            fi, state.preloaded.scrubber_frame_indices || []
        );
        document.querySelectorAll('.scrubber-dot').forEach(function(dot, idx) {
            dot.className = idx === dotActive ? 'scrubber-dot active' : 'scrubber-dot';
        });

        renderFrame(fi, state.preloaded, false);
    }

    function _fireSeekStore() {
        var btn = document.getElementById('seek-trigger-btn');
        if (btn) btn.click();
    }

    document.addEventListener('mousedown', function(e) {
        var track = e.target.closest('.scrubber-track');
        if (!track) return;

        var state = window._artemisState;
        if (!state || !state.preloaded) return;

        _isDragging = true;
        var pct = _pctFromEvent(e, track);
        var fi  = _frameIdxFromPct(pct, state.preloaded.total_frames);
        _applySeek(fi);
    });

    document.addEventListener('mousemove', function(e) {
        if (!_isDragging) return;

        var track = document.querySelector('.scrubber-track');
        if (!track) return;

        var state = window._artemisState;
        if (!state || !state.preloaded) return;

        var pct = _pctFromEvent(e, track);
        var fi  = _frameIdxFromPct(pct, state.preloaded.total_frames);
        _applySeek(fi);
    });

    document.addEventListener('mouseup', function(e) {
        if (!_isDragging) return;
        _isDragging = false;

        var state = window._artemisState;
        if (!state || !state.preloaded) return;

        _fireSeekStore();
    });

}());