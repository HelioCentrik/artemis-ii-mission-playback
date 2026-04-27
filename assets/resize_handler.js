(function () {
    var _rebuildTimer = null;
    var _relayoutFrame = null;

    function scheduleRebuild() {
        clearTimeout(_rebuildTimer);
        _rebuildTimer = setTimeout(function () {
            if (window._artemisState && window._artemisState.running) return;
            if (window.dash_clientside && window.dash_clientside.set_props) {
                window.dash_clientside.set_props("resize-store", { data: Date.now() });
            }
        }, 200);
    }

    // Immediately correct the Plotly SVG to the current container dimensions.
    // Called synchronously on fullscreenchange (before browser paints) so there
    // is no wrong-scale intermediate frame; called via rAF on window resize to
    // coalesce rapid events without spamming Plotly.
    function relayoutNow() {
        var graphDiv = document.getElementById("trajectory-graph");
        if (!graphDiv || !graphDiv._fullLayout || !window.Plotly) return;

        var w = graphDiv.offsetWidth;
        var h = graphDiv.offsetHeight;
        if (!w || !h) return;

        var yRange = graphDiv._fullLayout.yaxis.range;
        var xRange = graphDiv._fullLayout.xaxis.range;
        if (!yRange || !xRange) return;

        // scaleanchor="y", scaleratio=1, margin=0 → x_span = y_span × W/H
        var ySpan   = yRange[1] - yRange[0];
        var xMid    = (xRange[0] + xRange[1]) / 2;
        var xHalf   = (ySpan / 2) * (w / h);

        Plotly.relayout(graphDiv, {
            width: w,
            height: h,
            "xaxis.range": [xMid - xHalf, xMid + xHalf],
        });
    }

    function onFullscreenChange() {
        relayoutNow();   // synchronous — corrects SVG before first fullscreen paint
        scheduleRebuild();
    }

    function onWindowResize() {
        if (_relayoutFrame) cancelAnimationFrame(_relayoutFrame);
        _relayoutFrame = requestAnimationFrame(relayoutNow);
        scheduleRebuild();
    }

    window.addEventListener("resize", onWindowResize);
    document.addEventListener("fullscreenchange", onFullscreenChange);
    document.addEventListener("webkitfullscreenchange", onFullscreenChange);
})();
