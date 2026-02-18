/**
 * Main Application JavaScript
 * Handles API calls, UI updates, and model selection
 */

class MagasinApp {
    constructor() {
        this.apiBase = 'http://localhost:8000/api';
        this.currentDetector = 'yolov8n';
        this.currentTracker = null;
        this.currentSegmenter = null;
    }

    async init() {
        console.log('[App] Initializing...');

        // Load available models
        await this.loadAvailableModels();

        // Setup model selectors
        this.setupModelSelectors();

        // Load initial data
        await this.loadEquipment();
        await this.loadAlerts();
        await this.loadStatistics();

        // Setup event listeners
        this.setupEventListeners();

        console.log('[App] Initialized');
    }

    async loadAvailableModels() {
        try {
            const response = await fetch(`${this.apiBase}/models/available`);
            const result = await response.json();

            if (result.success) {
                this.availableModels = result.data;
                console.log('[App] Available models loaded:', this.availableModels);
            }
        } catch (error) {
            console.error('[App] Error loading models:', error);
        }
    }

    setupModelSelectors() {
        // Detector selector
        const detectorSelect = document.getElementById('detector-select');
        if (detectorSelect && this.availableModels) {
            this.availableModels.detectors.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = `${model.name} (${model.size})`;
                detectorSelect.appendChild(option);
            });

            detectorSelect.addEventListener('change', (e) => {
                this.switchDetector(e.target.value);
            });
        }

        // Tracker selector
        const trackerSelect = document.getElementById('tracker-select');
        if (trackerSelect && this.availableModels) {
            // Add "None" option
            const noneOption = document.createElement('option');
            noneOption.value = '';
            noneOption.textContent = 'None (Disabled)';
            trackerSelect.appendChild(noneOption);

            this.availableModels.trackers.forEach(tracker => {
                const option = document.createElement('option');
                option.value = tracker.id;
                option.textContent = tracker.name;
                trackerSelect.appendChild(option);
            });

            trackerSelect.addEventListener('change', (e) => {
                this.switchTracker(e.target.value);
            });
        }

        // Segmenter selector
        const segmenterSelect = document.getElementById('segmenter-select');
        if (segmenterSelect && this.availableModels) {
            // Add "None" option
            const noneOption = document.createElement('option');
            noneOption.value = '';
            noneOption.textContent = 'None (Disabled)';
            segmenterSelect.appendChild(noneOption);

            this.availableModels.segmenters.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = `${model.name} (${model.size})`;
                segmenterSelect.appendChild(option);
            });

            segmenterSelect.addEventListener('change', (e) => {
                this.switchSegmenter(e.target.value);
            });
        }
    }

    async switchDetector(modelId) {
        console.log('[App] Switching detector to:', modelId);
        try {
            const response = await fetch(`${this.apiBase}/models/detector?model_id=${modelId}`, {
                method: 'POST'
            });
            const result = await response.json();

            if (result.success) {
                this.currentDetector = modelId;
                this.showNotification('Detector switched to ' + modelId, 'success');
            }
        } catch (error) {
            console.error('[App] Error switching detector:', error);
            this.showNotification('Error switching detector', 'error');
        }
    }

    async switchTracker(trackerId) {
        console.log('[App] Switching tracker to:', trackerId);
        try {
            const response = await fetch(`${this.apiBase}/models/tracker?tracker_id=${trackerId}`, {
                method: 'POST'
            });
            const result = await response.json();

            if (result.success) {
                this.currentTracker = trackerId || null;
                this.showNotification(trackerId ? `Tracker switched to ${trackerId}` : 'Tracker disabled', 'success');
            }
        } catch (error) {
            console.error('[App] Error switching tracker:', error);
            this.showNotification('Error switching tracker', 'error');
        }
    }

    async switchSegmenter(modelId) {
        console.log('[App] Switching segmenter to:', modelId);
        try {
            const response = await fetch(`${this.apiBase}/models/segmentation?model_id=${modelId}`, {
                method: 'POST'
            });
            const result = await response.json();

            if (result.success) {
                this.currentSegmenter = modelId || null;
                this.showNotification(modelId ? `Segmenter switched to ${modelId}` : 'Segmentation disabled', 'success');
            }
        } catch (error) {
            console.error('[App] Error switching segmenter:', error);
            this.showNotification('Error switching segmenter', 'error');
        }
    }

    async loadEquipment() {
        try {
            const response = await fetch(`${this.apiBase}/equipment`);
            const result = await response.json();

            if (result.success) {
                console.log('[App] Equipment loaded:', result.data.length, 'items');
                // TODO: Update UI with equipment data
            }
        } catch (error) {
            console.error('[App] Error loading equipment:', error);
        }
    }

    async loadAlerts() {
        try {
            const response = await fetch(`${this.apiBase}/alerts`);
            const result = await response.json();

            if (result.success) {
                console.log('[App] Alerts loaded:', result.data.length, 'alerts');
                this.updateAlertsUI(result.data);
            }
        } catch (error) {
            console.error('[App] Error loading alerts:', error);
        }
    }

    async loadStatistics() {
        try {
            const response = await fetch(`${this.apiBase}/stats`);
            const result = await response.json();

            if (result.success) {
                console.log('[App] Statistics loaded:', result.data);
                this.updateStatsUI(result.data);
            }
        } catch (error) {
            console.error('[App] Error loading statistics:', error);
        }
    }

    updateAlertsUI(alerts) {
        // Update alerts panel if it exists
        const alertsContainer = document.getElementById('alerts-container');
        if (alertsContainer) {
            alertsContainer.innerHTML = alerts.slice(0, 10).map(alert => `
                <div class="alert alert-${alert.severity}">
                    <span class="alert-time">${new Date(alert.timestamp).toLocaleTimeString()}</span>
                    <span class="alert-type">${alert.type}</span>
                    <p>${alert.message}</p>
                </div>
            `).join('');
        }
    }

    updateStatsUI(stats) {
        // Update KPI cards
        const kpiMap = {
            'total-equipment': stats.total_equipment,
            'active-equipment': stats.active_equipment,
            'critical-alerts': stats.critical_alerts,
            'low-stock': stats.low_stock_warnings
        };

        Object.entries(kpiMap).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    setupEventListeners() {
        // Listen for video alerts
        window.addEventListener('videoAlert', (event) => {
            console.log('[App] Video alert received:', event.detail);
            // Refresh alerts
            this.loadAlerts();
        });
    }

    showNotification(message, type = 'info') {
        console.log(`[App] Notification (${type}):`, message);
        // TODO: Implement toast notification UI
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new MagasinApp();
    window.app.init();
});
