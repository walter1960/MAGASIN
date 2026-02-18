/**
 * Video Stream Manager
 * Handles WebSocket connection for real-time video streaming
 */

class VideoStreamManager {
    constructor(canvasId, cameraId = '0', host = 'localhost:8000') {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
        this.cameraId = cameraId;
        this.wsUrl = `ws://${host}/ws/video/${cameraId}`;
        this.ws = null;
        this.reconnectInterval = 3000;
        this.isConnected = false;

        // Performance tracking
        this.lastFrameTime = 0;
        this.latency = 0;

        // Find container for loading state
        this.container = this.canvas ? this.canvas.parentElement : null;
    }

    connect() {
        console.log('[VideoStream] Connecting to:', this.wsUrl);

        this.ws = new WebSocket(this.wsUrl);

        this.ws.onopen = () => {
            console.log('[VideoStream] Connected');
            this.isConnected = true;
            this.updateStatus('connected');
            this.showLoading('Waiting for frames...');
        };

        this.ws.onmessage = async (event) => {
            try {
                let metadata, imageData;

                if (event.data instanceof Blob) {
                    // Binary protocol: [4 bytes JSON len] [JSON metadata] [Raw JPEG]
                    const arrayBuffer = await event.data.arrayBuffer();
                    const view = new DataView(arrayBuffer);
                    const metadataLen = view.getUint32(0, false);

                    const metadataText = new TextDecoder().decode(arrayBuffer.slice(4, 4 + metadataLen));
                    metadata = JSON.parse(metadataText);

                    imageData = arrayBuffer.slice(4 + metadataLen);

                    const now = Date.now();
                    if (this.lastFrameTime) this.latency = now - this.lastFrameTime;
                    this.lastFrameTime = now;

                    this.hideLoading();
                    this.renderBinaryFrame(imageData, metadata.detections, metadata.alerts);
                } else {
                    // Fallback to JSON (for legacy support if needed)
                    const data = JSON.parse(event.data);
                    if (data.type === 'frame') {
                        this.renderFrame(data.data, data.detections, data.alerts);
                    }
                }
            } catch (error) {
                console.error('[VideoStream] Error parsing message:', error);
            }
        };

        this.ws.onerror = (error) => {
            console.error('[VideoStream] WebSocket error:', error);
            this.updateStatus('error');
        };

        this.ws.onclose = () => {
            console.log('[VideoStream] Disconnected');
            this.isConnected = false;
            this.updateStatus('disconnected');

            // Auto-reconnect
            setTimeout(() => this.connect(), this.reconnectInterval);
        };
    }

    renderBinaryFrame(arrayBuffer, detections, alerts) {
        if (!this.canvas || !this.ctx) return;

        const blob = new Blob([arrayBuffer], { type: 'image/jpeg' });
        const url = URL.createObjectURL(blob);
        const img = new Image();

        img.onload = () => {
            if (this.canvas.width !== img.width || this.canvas.height !== img.height) {
                this.canvas.width = img.width;
                this.canvas.height = img.height;
            }
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.drawImage(img, 0, 0);
            if (detections && detections.length > 0) this.drawClientOverlays(detections);
            if (alerts && alerts.length > 0) this.handleAlerts(alerts);

            // Cleanup memory
            URL.revokeObjectURL(url);
        };
        img.src = url;
    }

    renderFrame(base64Data, detections, alerts) {
        // ... (legacy kept for compatibility)
        const img = new Image();
        img.onload = () => {
            if (this.canvas.width !== img.width || this.canvas.height !== img.height) {
                this.canvas.width = img.width;
                this.canvas.height = img.height;
            }
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.drawImage(img, 0, 0);
            if (detections && detections.length > 0) this.drawClientOverlays(detections);
            if (alerts && alerts.length > 0) this.handleAlerts(alerts);
        };
        img.src = 'data:image/jpeg;base64,' + base64Data;
    }

    drawClientOverlays(detections) {
        // We only draw extra info that might not be in the server's plot()
        // or to add custom client-side animations
        detections.forEach(det => {
            if (det.interaction) {
                const [x1, y1, x2, y2] = det.bbox;
                // Highlight handling objects with a glow
                this.ctx.strokeStyle = '#ef4444';
                this.ctx.lineWidth = 4;
                this.ctx.setLineDash([5, 5]); // Dashed line for interaction
                this.ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
                this.ctx.setLineDash([]); // Reset
            }
        });
    }

    handleAlerts(alerts) {
        // Dispatch custom event for alerts
        const event = new CustomEvent('videoAlert', { detail: alerts });
        window.dispatchEvent(event);
    }

    updateStatus(status) {
        // Individual camera status is handled by individual dots in grid
        // but we can log for debugging
        if (status === 'disconnected') {
            this.showLoading('Reconnecting...');
        }
    }

    showLoading(message = 'Loading...') {
        if (!this.container) return;
        let loader = this.container.querySelector('.v-loader');
        if (!loader) {
            loader = document.createElement('div');
            loader.className = 'v-loader absolute inset-0 bg-slate-900/80 flex flex-col items-center justify-center gap-3 z-20';
            loader.innerHTML = `
                <div class="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent shadow-lg text-primary"></div>
                <span class="text-[10px] font-mono text-slate-400 uppercase tracking-widest">${message}</span>
            `;
            this.container.appendChild(loader);
        } else {
            loader.querySelector('span').textContent = message;
            loader.classList.remove('hidden');
        }
    }

    hideLoading() {
        if (!this.container) return;
        const loader = this.container.querySelector('.v-loader');
        if (loader) loader.classList.add('hidden');
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Export for use in other scripts
window.VideoStreamManager = VideoStreamManager;
