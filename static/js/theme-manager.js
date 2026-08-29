/**
 * GFT Global Theme Manager
 * Handles Dark/Light Mode switching and system defaults.
 */
(function() {
    function applyTheme(theme) {
        if (theme === 'system') {
            const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            document.documentElement.setAttribute('data-theme', systemPrefersDark ? 'dark' : 'light');
        } else {
            document.documentElement.setAttribute('data-theme', theme);
        }
    }

    function initTheme() {
        const savedTheme = localStorage.getItem('gft_theme') || 'system';
        applyTheme(savedTheme);
        
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (localStorage.getItem('gft_theme') === 'system') {
                applyTheme('system');
            }
        });
    }

    initTheme();

    window.GFTTheme = {
        setTheme: function(theme) {
            localStorage.setItem('gft_theme', theme);
            applyTheme(theme);
            this.updateUI(theme);
        },
        getTheme: function() {
            return localStorage.getItem('gft_theme') || 'system';
        },
        updateUI: function(theme) {
            document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
                if (btn.dataset.theme === theme) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        window.GFTTheme.updateUI(window.GFTTheme.getTheme());
    });
})();