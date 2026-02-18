/**
 * UX Utilities for ASECNA Stock IA
 * Handles global loading states and visual feedback.
 */

class UXUtils {
    constructor() {
        this.loadingOverlay = null;
        this.init();
    }

    init() {
        document.addEventListener('DOMContentLoaded', () => {
            this.createLoadingOverlay();
            this.interceptFetch();
        });
    }

    createLoadingOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'global-loader';
        overlay.className = 'fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[200] flex items-center justify-center opacity-0 pointer-events-none transition-all duration-300';
        overlay.innerHTML = `
            <div class="flex flex-col items-center gap-4">
                <div class="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
                <p class="text-white font-medium text-sm tracking-widest uppercase animate-pulse">Traitement IA en cours...</p>
            </div>
        `;
        document.body.appendChild(overlay);
        this.loadingOverlay = overlay;
    }

    showLoading(show = true) {
        if (!this.loadingOverlay) return;
        if (show) {
            this.loadingOverlay.classList.remove('opacity-0', 'pointer-events-none');
            this.loadingOverlay.classList.add('opacity-100');
        } else {
            this.loadingOverlay.classList.add('opacity-0', 'pointer-events-none');
            this.loadingOverlay.classList.remove('opacity-100');
        }
    }

    /**
     * Optional: Intercept all fetch calls to show loader automatically
     * Handle with care to avoid flickering on fast requests
     */
    interceptFetch() {
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            // Only show loader for API calls that take time
            // Or maybe only for POST/PUT/DELETE
            const isApi = args[0].includes('/api/');
            const isMutation = ['POST', 'PUT', 'DELETE'].includes((args[1] || {}).method || 'GET');

            if (isApi && isMutation) {
                this.showLoading(true);
            }

            try {
                const response = await originalFetch(...args);
                return response;
            } finally {
                if (isApi && isMutation) {
                    this.showLoading(false);
                }
            }
        };
    }
}

// Global instance
const uxUtils = new UXUtils();
