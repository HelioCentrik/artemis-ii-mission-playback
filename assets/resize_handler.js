(function () {
    var _timer = null;

    function schedule() {
        clearTimeout(_timer);
        _timer = setTimeout(function () {
            if (window._artemisState && window._artemisState.running) return;
            if (!document.getElementById('resize-store')) return;
            if (window.dash_clientside && window.dash_clientside.set_props) {
                window.dash_clientside.set_props("resize-store", { data: Date.now() });
            }
        }, 200);
    }

    window.addEventListener("resize", schedule);
    document.addEventListener("fullscreenchange", schedule);
    document.addEventListener("webkitfullscreenchange", schedule);
})();