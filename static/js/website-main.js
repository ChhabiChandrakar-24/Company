/**
 * GFT Website — shared front-end behaviour.
 * Single bootstrap: every binding below is attached exactly once
 * (guarded), so repeated template fragments can never duplicate
 * event listeners or re-initialise components.
 */
(function () {
    'use strict';

    var ready = function (fn) {
        if (document.readyState !== 'loading') { fn(); }
        else { document.addEventListener('DOMContentLoaded', fn); }
    };

    var bindOnce = function (el, type, fn, options) {
        if (!el || el.getAttribute('data-bound-' + type)) { return; }
        el.setAttribute('data-bound-' + type, '1');
        el.addEventListener(type, fn, options);
    };

    ready(function () {
        var root = document.documentElement;

        /* ---------- Mobile nav toggle (single instance) ---------- */
        var toggle = document.querySelector('[data-nav-toggle]');
        var nav = document.querySelector('[data-site-nav]');
        if (toggle && nav) {
            var closeNav = function () {
                toggle.setAttribute('aria-expanded', 'false');
                nav.classList.remove('is-open');
            };
            bindOnce(toggle, 'click', function () {
                var open = toggle.getAttribute('aria-expanded') === 'true';
                toggle.setAttribute('aria-expanded', String(!open));
                nav.classList.toggle('is-open', !open);
            });
            // Close on Escape / outside tap / after navigating
            document.addEventListener('keydown', function (e) {
                if (e.key === 'Escape') { closeNav(); closeAllDropdowns(); }
            });
            document.addEventListener('click', function (e) {
                if (nav.classList.contains('is-open') && !nav.contains(e.target) && !toggle.contains(e.target)) {
                    closeNav();
                }
            });
            nav.addEventListener('click', function (e) {
                if (e.target.closest('a')) { closeNav(); }
            });
        }

        /* ---------- Dropdown menus (single delegated handler, no dupes) ---------- */
        function closeAllDropdowns(except) {
            document.querySelectorAll('.nav-dropdown.is-open').forEach(function (d) {
                if (d !== except) {
                    d.classList.remove('is-open');
                    var t = d.querySelector('.nav-trigger');
                    if (t) { t.setAttribute('aria-expanded', 'false'); }
                }
            });
        }
        document.querySelectorAll('.nav-dropdown > .nav-trigger').forEach(function (btn) {
            bindOnce(btn, 'click', function (e) {
                e.preventDefault();
                var dd = btn.closest('.nav-dropdown');
                var wasOpen = dd.classList.contains('is-open');
                closeAllDropdowns();
                dd.classList.toggle('is-open', !wasOpen);
                btn.setAttribute('aria-expanded', String(!wasOpen));
            });
        });
        document.addEventListener('click', function (e) {
            if (!e.target.closest('.nav-dropdown')) { closeAllDropdowns(); }
        });

        /* ---------- Theme buttons (uses GFTTheme from theme-manager.js) ---------- */
        var themeButtons = document.querySelectorAll('[data-theme-choice]');
        function paintThemeButtons() {
            var current = window.GFTTheme ? GFTTheme.getTheme() : 'system';
            themeButtons.forEach(function (b) {
                b.classList.toggle('active', b.getAttribute('data-theme-choice') === current);
            });
        }
        if (themeButtons.length) {
            document.querySelectorAll('[data-theme-choice]').forEach(function (btn) {
                bindOnce(btn, 'click', function () {
                    if (window.GFTTheme) { GFTTheme.setTheme(btn.getAttribute('data-theme-choice')); }
                    paintThemeButtons();
                });
            });
            if (window.GFTTheme && window.GFTTheme.updateUI) {
                var orig = window.GFTTheme.updateUI;
                window.GFTTheme.updateUI = function (t) { orig.call(this, t); paintThemeButtons(); };
            }
        }
        paintThemeButtons();

        /* ---------- Sticky header shadow ---------- */
        var header = document.querySelector('.site-header');
        if (header && 'IntersectionObserver' in window) {
            var sentinel = document.createElement('div');
            sentinel.style.cssText = 'position:absolute;top:0;left:0;width:1px;height:1px;opacity:0;pointer-events:none';
            document.body.insertBefore(sentinel, document.body.firstChild);
            new IntersectionObserver(function (entries) {
                header.classList.toggle('is-scrolled', !entries[0].isIntersecting);
            }, { rootMargin: '0px 0px -100% 0px' }).observe(sentinel);
        }

        /* ---------- Carousel (guarded init — never initialised twice) ---------- */
        document.querySelectorAll('[data-carousel]').forEach(function (el) {
            if (el.getAttribute('data-carousel-inited')) { return; }
            el.setAttribute('data-carousel-inited', '1');

            var slides = Array.prototype.slice.call(el.querySelectorAll('[data-slide]'));
            var prev = el.querySelector('[data-carousel-prev]');
            var next = el.querySelector('[data-carousel-next]');
            var status = el.querySelector('[data-carousel-status]');
            var dotsWrap = el.querySelector('.carousel-dots');
            if (slides.length < 2) { return; }

            var index = 0;
            var timer = null;
            var autoplay = el.getAttribute('data-autoplay') === 'true';
            var interval = parseInt(el.getAttribute('data-interval') || '6000', 10);

            function show(n, animate) {
                index = (n + slides.length) % slides.length;
                slides.forEach(function (s, j) {
                    s.hidden = j !== index;
                    s.classList.toggle('is-active', j === index);
                    if (animate) {
                        s.classList.remove('is-animating');
                        // Force reflow then add animation class only to the visible slide
                        if (j === index) {
                            void s.offsetWidth;
                            s.classList.add('is-animating');
                        }
                    }
                });
                if (status) { status.textContent = (index + 1) + ' / ' + slides.length; }
                if (dotsWrap) {
                    dotsWrap.querySelectorAll('button').forEach(function (d, j) {
                        d.classList.toggle('is-active', j === index);
                    });
                }
            }

            function stopAuto() {
                if (timer) { clearInterval(timer); timer = null; }
            }
            function startAuto() {
                if (!autoplay) { return; }
                stopAuto();
                timer = setInterval(function () { show(index + 1, true); }, interval);
            }

            if (prev) { bindOnce(prev, 'click', function () { show(index - 1, true); startAuto(); }); }
            if (next) { bindOnce(next, 'click', function () { show(index + 1, true); startAuto(); }); }

            // Dots
            if (dotsWrap) {
                slides.forEach(function (_, j) {
                    var dot = document.createElement('button');
                    dot.type = 'button';
                    dot.setAttribute('aria-label', 'Go to slide ' + (j + 1));
                    if (j === 0) { dot.classList.add('is-active'); }
                    bindOnce(dot, 'click', function () { show(j, true); startAuto(); });
                    dotsWrap.appendChild(dot);
                });
            }

            // Keyboard
            el.setAttribute('tabindex', '0');
            bindOnce(el, 'keydown', function (e) {
                if (e.key === 'ArrowLeft') { show(index - 1, true); startAuto(); }
                if (e.key === 'ArrowRight') { show(index + 1, true); startAuto(); }
            });

            // Touch swipe
            var startX = null;
            bindOnce(el, 'touchstart', function (e) { startX = e.touches[0].clientX; }, { passive: true });
            bindOnce(el, 'touchend', function (e) {
                if (startX === null) { return; }
                var dx = e.changedTouches[0].clientX - startX;
                if (Math.abs(dx) > 44) { show(index + (dx < 0 ? 1 : -1), true); startAuto(); }
                startX = null;
            }, { passive: true });

            // Pause autoplay while focused / hovered (accessibility)
            if (autoplay) {
                el.addEventListener('mouseenter', stopAuto);
                el.addEventListener('mouseleave', startAuto);
                el.addEventListener('focusin', stopAuto);
                el.addEventListener('focusout', startAuto);
            }

            show(0, false);
            startAuto();
        });

        /* ---------- Scroll reveal (respects reduced motion via CSS) ---------- */
        var reveals = document.querySelectorAll('.reveal');
        if (reveals.length && 'IntersectionObserver' in window) {
            var io = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('is-visible');
                        io.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
            reveals.forEach(function (el) { io.observe(el); });
        } else {
            reveals.forEach(function (el) { el.classList.add('is-visible'); });
        }

        /* ---------- Card cursor glow ---------- */
        document.querySelectorAll('.cms-card').forEach(function (card) {
            bindOnce(card, 'pointermove', function (e) {
                var r = card.getBoundingClientRect();
                card.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100) + '%');
            });
        });
    });
})();
