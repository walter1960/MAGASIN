/**
 * Monitoring Dashboard JavaScript for ASECNA Stock IA
 */

class MonitoringManager {
    constructor() {
        this.cameras = [];
        this.stats = {
            total_cameras: 0,
            active_trackings: 0,
            stable_objects: 0,
            alerts: 0
        };

        this.init();
        // Global refresh
        setInterval(() => this.updateDashboard(), 5000);
    }

    async init() {
        await this.updateDashboard();
        this.renderCameraGrid();
    }

    async updateDashboard() {
        try {
            // Get camera status
            const camRes = await fetch('/api/cameras/status');
            const camData = await camRes.json();

            // Get temporal status
            const tempRes = await fetch('/api/detection/temporal/status');
            const tempData = await tempRes.json();

            if (camData.success && tempData.success) {
                this.updateStats(camData, tempData.data);
                this.updateActivityFeed(tempData.data);
                this.renderCameraGrid(camData);
            }
        } catch (error) {
            console.error('Monitoring update error:', error);
        }
    }

    updateStats(camData, tempData) {
        document.getElementById('active-cameras').textContent = camData.total_cameras || 0;
        document.getElementById('active-trackings').textContent = tempData.total_trackings || 0;
        document.getElementById('stable-objects').textContent = tempData.by_status?.stable || 0;
        document.getElementById('active-alerts').textContent = tempData.pending_validations || 0;
    }

    renderCameraGrid(camRes) {
        const grid = document.getElementById('camera-supervision-grid');
        grid.innerHTML = '';

        const cameras = (camRes && camRes.cameras) ? Object.entries(camRes.cameras) : [];

        if (cameras.length === 0) {
            grid.innerHTML = '<p class="col-span-full text-slate-500 text-center py-10">Aucune caméra IP configurée.</p>';
            return;
        }

        cameras.forEach(([id, cam]) => {
            const statusColor = cam.running ? 'bg-green-500' : 'bg-red-500';
            const card = document.createElement('div');
            card.className = 'glass-panel p-4 flex flex-col gap-3 group hover:border-blue-500/30 transition-all cursor-pointer';
            card.onclick = () => window.location.href = `surveillance.html?cam=${id}`;

            card.innerHTML = `
                <div class="flex items-center justify-between">
                    <span class="text-[10px] font-black text-slate-500 uppercase tracking-tighter">${id}</span>
                    <div class="w-2 h-2 ${statusColor} rounded-full ${cam.running ? 'status-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]' : ''}"></div>
                </div>
                <div class="h-24 bg-slate-900 rounded-lg flex items-center justify-center relative overflow-hidden group-hover:scale-[1.02] transition-transform">
                    <i class="fas fa-video ${cam.running ? 'text-blue-500/40' : 'text-slate-800'} text-3xl"></i>
                    <div class="absolute inset-0 bg-blue-600/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    <div class="absolute bottom-2 left-2 flex gap-1">
                         <span class="px-1.5 py-0.5 bg-black/60 text-[8px] font-bold text-blue-400 rounded uppercase">YOLOv8</span>
                         <span class="px-1.5 py-0.5 bg-black/60 text-[8px] font-bold text-yellow-500 rounded uppercase">MediaPipe</span>
                    </div>
                </div>
                <div class="flex flex-col gap-1">
                    <p class="text-xs font-bold text-white truncate" title="${cam.zone}">${cam.zone}</p>
                    <div class="flex justify-between items-center text-[10px] font-bold">
                        <span class="text-slate-500 uppercase tracking-tighter">Status</span>
                        <span class="${cam.running ? 'text-green-400' : 'text-red-400'}">${cam.running ? 'ONLINE' : 'OFFLINE'}</span>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
    }

    updateActivityFeed(tempData) {
        const feed = document.getElementById('activity-feed');
        // keep some history but prepend new events
        // logic to be implemented with real-time stream
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new MonitoringManager();
});
