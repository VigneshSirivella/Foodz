// =========================================================
// Foodz Centralized API & Cloud Deployment Configuration
// =========================================================
(function() {
    const isLocalhost = window.location.hostname === 'localhost' ||
                        window.location.hostname === '127.0.0.1' ||
                        window.location.hostname === '';

    // Deployed Render backend URL fallback when hosted on Vercel
    // If Vercel rewrites (/api/...) are active, relative requests ('') also proxy directly
    const DEFAULT_CLOUD_BACKEND = 'https://foodz-backend.onrender.com';

    const configuredUrl = window.__FOODZ_API_BASE_URL__ ||
                          localStorage.getItem('FOODZ_API_BASE_URL') ||
                          (isLocalhost ? '' : DEFAULT_CLOUD_BACKEND);

    window.FOODZ_CONFIG = {
        API_BASE_URL: configuredUrl ? configuredUrl.replace(/\/+$/, '') : '',
        apiUrl: function(endpoint) {
            const cleanEndpoint = endpoint.startsWith('/') ? endpoint : '/' + endpoint;
            const base = (window.FOODZ_CONFIG && window.FOODZ_CONFIG.API_BASE_URL)
                         ? window.FOODZ_CONFIG.API_BASE_URL.replace(/\/+$/, '')
                         : '';
            return base + cleanEndpoint;
        }
    };

    window.apiUrl = window.FOODZ_CONFIG.apiUrl;
})();
