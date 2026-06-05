/* =============================================
   Smart AI Assistant — Theme Manager
   ============================================= */

(function() {
    'use strict';

    const THEME_KEY = 'smartai-theme';

    // Apply saved theme on page load (before render)
    function applySavedTheme() {
        const saved = localStorage.getItem(THEME_KEY) || 'dark';
        document.documentElement.setAttribute('data-theme', saved);
        updateThemeIcon(saved);
    }

    function updateThemeIcon(theme) {
        const btn = document.getElementById('theme-toggle');
        if (!btn) return;
        const icon = btn.querySelector('i');
        if (icon) {
            icon.className = theme === 'dark' ? 'bi bi-moon-stars' : 'bi bi-sun';
        }
    }

    // Toggle theme
    window.toggleTheme = function() {
        const html = document.documentElement;
        const current = html.getAttribute('data-theme') || 'dark';
        const next = current === 'dark' ? 'light' : 'dark';

        html.setAttribute('data-theme', next);
        localStorage.setItem(THEME_KEY, next);
        updateThemeIcon(next);

        // Persist to server if logged in
        fetch('/api/settings/theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.getElementById('csrf-token')?.value || '',
            },
            body: JSON.stringify({ theme: next }),
        }).catch(() => {});  // Fail silently
    };

    // Apply on load
    applySavedTheme();

    // Also apply after DOM ready (for dynamic elements)
    document.addEventListener('DOMContentLoaded', () => {
        const saved = localStorage.getItem(THEME_KEY) || 'dark';
        updateThemeIcon(saved);
    });
})();
