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


/* ── Crew card expand / collapse ─────────────────────────────────────────── */

(function () {
    "use strict";

    var EXPANDED_HEIGHT = 580;   // px — target expanded card height
    var _activeCard     = null;
    var _scrim          = null;
    var _initTimeout    = null;

    function _getOrCreateScrim() {
        var s = document.querySelector('.home-crew-scrim');
        if (s) return s;
        s = document.createElement('div');
        s.className = 'home-crew-scrim';
        document.body.appendChild(s);
        s.addEventListener('click', _collapse);
        return s;
    }

    function _removeGhost(card) {
        if (card._crewGhost && card._crewGhost.parentNode) {
            card._crewGhost.parentNode.removeChild(card._crewGhost);
        }
        card._crewGhost = null;
    }

    function _collapseImmediate(card) {
        card.classList.remove('expanded', 'is-lifting');
        card.style.cssText = '';
        _removeGhost(card);
        if (_scrim) _scrim.classList.remove('visible');
        _activeCard = null;
    }

    function _expand(card) {
        if (_activeCard === card) { _collapse(); return; }
        if (_activeCard)          { _collapseImmediate(_activeCard); }

        var rect        = card.getBoundingClientRect();
        var cardIndex   = parseInt(card.dataset.cardIndex, 10);
        var heightDelta = EXPANDED_HEIGHT - rect.height;
        var widthDelta  = Math.round(heightDelta / 2);

        // Hold the grid slot while card is fixed
        var ghost             = document.createElement('div');
        ghost.className       = 'home-crew-card-ghost';
        ghost.style.width     = rect.width  + 'px';
        ghost.style.height    = rect.height + 'px';
        card.parentNode.insertBefore(ghost, card);
        card._crewGhost = ghost;

        // Store original geometry for collapse animation
        card.dataset.origTop    = rect.top;
        card.dataset.origLeft   = rect.left;
        card.dataset.origWidth  = rect.width;
        card.dataset.origHeight = rect.height;

        // Pin card at its current viewport position — no visual change yet
        card.style.position = 'fixed';
        card.style.left     = rect.left   + 'px';
        card.style.top      = rect.top    + 'px';
        card.style.width    = rect.width  + 'px';
        card.style.height   = rect.height + 'px';
        card.style.margin   = '0';

        // Force reflow so transition starts from pinned position
        void card.offsetHeight;

        card.classList.add('is-lifting');
        _scrim.classList.add('visible');

        // Directional expansion per card position:
        //   0 — left corner  : anchor left,  grow right
        //   1 — inner left   : anchor right, grow left  (outward)
        //   2 — inner right  : anchor left,  grow right (outward)
        //   3 — right corner : anchor right, grow left
        var newTop   = Math.max(8, rect.top - heightDelta);
        var newWidth = rect.width + widthDelta;
        var newLeft;

        if      (cardIndex === 0) { newLeft = rect.left;                }
        else if (cardIndex === 1) { newLeft = rect.left - widthDelta;   }
        else if (cardIndex === 2) { newLeft = rect.left;                }
        else                      { newLeft = rect.left - widthDelta;   }

        card.style.top    = newTop    + 'px';
        card.style.left   = newLeft   + 'px';
        card.style.width  = newWidth  + 'px';
        card.style.height = EXPANDED_HEIGHT + 'px';

        _activeCard = card;

        // Fade in detail after geometry settles — transitionend on height
        var fallback = setTimeout(function () {
            card.classList.add('expanded');
        }, 380);

        function onEnd(e) {
            if (e.propertyName !== 'height') return;
            clearTimeout(fallback);
            card.removeEventListener('transitionend', onEnd);
            card.classList.add('expanded');
        }
        card.addEventListener('transitionend', onEnd);
    }

    function _collapse() {
        if (!_activeCard) return;
        var card    = _activeCard;
        _activeCard = null;

        card.classList.remove('expanded');
        _scrim.classList.remove('visible');

        // Animate back to original geometry
        card.style.top    = parseFloat(card.dataset.origTop)    + 'px';
        card.style.left   = parseFloat(card.dataset.origLeft)   + 'px';
        card.style.width  = parseFloat(card.dataset.origWidth)  + 'px';
        card.style.height = parseFloat(card.dataset.origHeight) + 'px';

        var fallback = setTimeout(function () {
            card.classList.remove('is-lifting');
            card.style.cssText = '';
            _removeGhost(card);
        }, 380);

        function onEnd(e) {
            if (e.propertyName !== 'height') return;
            clearTimeout(fallback);
            card.removeEventListener('transitionend', onEnd);
            card.classList.remove('is-lifting');
            card.style.cssText = '';
            _removeGhost(card);
        }
        card.addEventListener('transitionend', onEnd);
    }

    function _init() {
        var row = document.querySelector('.home-crew-row');
        if (!row || row.dataset.crewInit) return;
        var cards = row.querySelectorAll('.home-crew-card');
        if (!cards.length) return;

        row.dataset.crewInit = '1';
        _scrim = _getOrCreateScrim();

        cards.forEach(function (card) {
            card.addEventListener('click', function () { _expand(card); });
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') _collapse();
        });
    }

    var _observer = new MutationObserver(function () {
        if (!document.querySelector('.home-crew-card')) return;
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