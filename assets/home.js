// assets/home.js
//
// Home page carousel — recovery video → image slideshow.
// IIFE guards against running on /playback/. MutationObserver handles
// Dash SPA navigation back to / without a full page reload.

(function () {
    "use strict";

    var _timer   = null;
    var _current = 0;
    var INTERVAL = 5000;

    // Derive a display label from the image filename slug.
    // "/assets/carousel/01-recovery-victor-glover.jpg" → "RECOVERY · VICTOR GLOVER"
    function _labelFromSrc(src) {
        var filename = src.split('/').pop().replace(/\.\w+$/, '');
        var slug     = filename.replace(/^\d+[-_]/, '');
        return slug.replace(/[-_]+/g, ' · ').toUpperCase();
    }

    function _showImage(imgs, dots, label, index) {
        imgs.forEach(function (img, i) {
            img.classList.toggle('active', i === index);
        });
        dots.forEach(function (dot, i) {
            dot.classList.toggle('active', i === index);
        });
        if (label) {
            label.textContent = 'ARTEMIS II  ✦  ' + _labelFromSrc(imgs[index].src);
        }
        _current = index;
    }

    function _startTimer(imgs, dots, label) {
        _timer = setInterval(function () {
            _showImage(imgs, dots, label, (_current + 1) % imgs.length);
        }, INTERVAL);
    }

    function _resetTimer(imgs, dots, label) {
        clearInterval(_timer);
        _startTimer(imgs, dots, label);
    }

    function _init() {
        var video    = document.getElementById('carousel-video');
        var imgsWrap = document.getElementById('carousel-imgs');
        var controls = document.getElementById('carousel-controls');
        var label    = document.getElementById('carousel-panel-label');
        var prevBtn  = document.getElementById('carousel-prev');
        var nextBtn  = document.getElementById('carousel-next');

        if (!video || !imgsWrap) return;

        var imgs = Array.from(imgsWrap.querySelectorAll('.home-carousel-img'));
        var dots = Array.from(document.querySelectorAll('.home-carousel-dot'));

        if (!imgs.length) return;

        // Hide carousel until video ends
        imgsWrap.style.display = 'none';
        controls.style.display = 'none';

        video.addEventListener('ended', function () {
            video.style.display    = 'none';
            imgsWrap.style.display = 'block';
            controls.style.display = 'flex';
            _showImage(imgs, dots, label, 0);
            _startTimer(imgs, dots, label);
        });

        prevBtn && prevBtn.addEventListener('click', function () {
            _showImage(imgs, dots, label, (_current - 1 + imgs.length) % imgs.length);
            _resetTimer(imgs, dots, label);
        });

        nextBtn && nextBtn.addEventListener('click', function () {
            _showImage(imgs, dots, label, (_current + 1) % imgs.length);
            _resetTimer(imgs, dots, label);
        });

        dots.forEach(function (dot, i) {
            dot.addEventListener('click', function () {
                _showImage(imgs, dots, label, i);
                _resetTimer(imgs, dots, label);
            });
        });
    }

    // MutationObserver — handles initial load AND Dash SPA navigation back to /
    var _observer = new MutationObserver(function () {
        if (document.getElementById('carousel-video')) {
            _observer.disconnect();
            _init();
        }
    });

    if (document.getElementById('carousel-video')) {
        _init();
    } else {
        _observer.observe(document.body, { childList: true, subtree: true });
    }

}());