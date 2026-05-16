// assets/home.js

(function () {
    "use strict";

    var _timer       = null;
    var _current     = 0;
    var _initTimeout = null;
    var INTERVAL     = 5000;

    function _labelFromSrc(src) {
        var filename = src.split('/').pop().replace(/\.\w+$/, '');
        var slug     = filename.replace(/^\d+[-_]/, '');
        return slug.replace(/[-_]+/g, ' · ').toUpperCase();
    }

    function _showImage(imgs, label, index) {
        imgs.forEach(function (img, i) {
            img.classList.toggle('active', i === index);
        });
        if (label) {
            label.textContent = 'ARTEMIS II  ✦  ' + _labelFromSrc(imgs[index].src);
        }
        _current = index;
    }

    function _showVideo(video, imgsWrap, label) {
        clearInterval(_timer);
        _timer                 = null;
        video.style.display    = 'block';
        video.currentTime      = 0;
        imgsWrap.style.display = 'none';
        if (label) label.textContent = 'ARTEMIS II  ✦  SPLASHDOWN & RECOVERY';
        video.play().catch(function () {});
    }

    function _isVideoVisible(video) {
        return video.style.display !== 'none';
    }

    function _startTimer(imgs, label, video, imgsWrap) {
        _timer = setInterval(function () {
            var next = _current + 1;
            if (next >= imgs.length) {
                _showVideo(video, imgsWrap, label);
            } else {
                _showImage(imgs, label, next);
            }
        }, INTERVAL);
    }

    function _resetTimer(imgs, label, video, imgsWrap) {
        clearInterval(_timer);
        _startTimer(imgs, label, video, imgsWrap);
    }

    function _init() {
        var video    = document.getElementById('carousel-video');
        var imgsWrap = document.getElementById('carousel-imgs');
        var controls = document.getElementById('carousel-controls');
        var label    = document.getElementById('carousel-panel-label');
        var prevBtn  = document.getElementById('carousel-prev');
        var nextBtn  = document.getElementById('carousel-next');

        if (!video || !imgsWrap) return;

        if (video.dataset.carouselInit) return;
        video.dataset.carouselInit = '1';

        var imgs = Array.from(imgsWrap.querySelectorAll('.home-carousel-img'));
        if (!imgs.length) return;

        clearInterval(_timer);
        _timer   = null;
        _current = 0;

        // Video visible first, images hidden — controls always visible
        video.style.display    = 'block';
        video.currentTime      = 0;
        imgsWrap.style.display = 'none';

        imgs.forEach(function (img, i) {
            img.classList.toggle('active', i === 0);
        });

        video.play().catch(function () {});

        video.addEventListener('ended', function () {
            video.style.display    = 'none';
            imgsWrap.style.display = 'block';
            _showImage(imgs, label, 0);
            _startTimer(imgs, label, video, imgsWrap);
        });

        if (prevBtn) {
            prevBtn.addEventListener('click', function () {
                if (_isVideoVisible(video)) {
                    return; // video is first — nothing before it
                } else if (_current === 0) {
                    _showVideo(video, imgsWrap, label);
                } else {
                    _showImage(imgs, label, _current - 1);
                    _resetTimer(imgs, label, video, imgsWrap);
                }
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', function () {
                if (_isVideoVisible(video)) {
                    video.style.display    = 'none';
                    imgsWrap.style.display = 'block';
                    video.pause();
                    _showImage(imgs, label, 0);
                    _startTimer(imgs, label, video, imgsWrap);
                } else {
                    var next = _current + 1;
                    if (next >= imgs.length) {
                        _showVideo(video, imgsWrap, label);
                    } else {
                        _showImage(imgs, label, next);
                        _resetTimer(imgs, label, video, imgsWrap);
                    }
                }
            });
        }
    }

    var _observer = new MutationObserver(function () {
        if (!document.getElementById('carousel-video')) return;
        clearTimeout(_initTimeout);
        _initTimeout = setTimeout(_init, 50);
    });

    _observer.observe(document.body, { childList: true, subtree: true });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }

}());