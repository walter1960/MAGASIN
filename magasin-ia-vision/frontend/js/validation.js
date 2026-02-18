/**
 * Validation Manager JavaScript for ASECNA Stock IA
 */

class ValidationManager {
    constructor() {
        this.requests = [];
        this.currentRejectId = null;

        this.initEventListeners();
        this.loadRequests();

        // Auto refresh every 30 seconds
        setInterval(() => this.loadRequests(), 30000);
    }

    initEventListeners() {
        document.getElementById('refresh-btn').addEventListener('click', () => this.loadRequests());
        document.getElementById('confirm-reject').addEventListener('click', () => this.confirmReject());
    }

    async loadRequests() {
        const loader = document.getElementById('loading');
        const list = document.getElementById('validation-requests');
        const emptyState = document.getElementById('empty-state');

        try {
            const response = await fetch('/api/validation/requests');
            const result = await response.json();

            loader.classList.add('hidden');

            if (result.success && result.data.length > 0) {
                this.requests = result.data;
                emptyState.classList.add('hidden');
                this.renderRequests();
                this.updateStats();
            } else {
                list.innerHTML = '';
                emptyState.classList.remove('hidden');
                this.updateStats(0);
            }
        } catch (error) {
            console.error('Error loading validation requests:', error);
            this.showNotification('Erreur', 'Impossible de charger les validations.', 'error');
        }
    }

    updateStats(count = null) {
        const finalCount = count !== null ? count : this.requests.length;
        document.getElementById('pending-count').textContent = `${finalCount} en attente`;
        document.getElementById('total-pending').textContent = finalCount;
        document.getElementById('total-detected').textContent = finalCount; // Simplified for MVP
    }

    renderRequests() {
        const container = document.getElementById('validation-requests');
        container.innerHTML = '';

        this.requests.forEach(req => {
            const card = document.createElement('div');
            card.className = 'glass-panel p-6 request-card overflow-hidden relative group';

            const deltaClass = req.quantity_delta > 0 ? 'text-green-400 bg-green-500/10' : 'text-red-400 bg-red-500/10';
            const deltaSign = req.quantity_delta > 0 ? '+' : '';
            const camBadges = req.camera_ids.map(id => `<span class="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-[10px] rounded border border-blue-500/20">${id}</span>`).join(' ');

            card.innerHTML = `
                <div class="flex flex-col md:flex-row gap-8 items-center">
                    <!-- Object Info -->
                    <div class="flex items-center gap-6 flex-1">
                        <div class="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center text-blue-400 border border-slate-700 shadow-inner">
                            <i class="fas fa-microchip text-2xl"></i>
                        </div>
                        <div>
                            <div class="flex items-center gap-3 mb-1">
                                <h4 class="text-xl font-bold text-white">${req.object_type}</h4>
                                <span class="badge badge-pending">Validation Requise</span>
                            </div>
                            <div class="flex flex-wrap gap-2 items-center">
                                ${camBadges}
                                <span class="text-slate-500 text-xs">• Détecté stable pendant ${req.detection_duration_minutes.toFixed(0)} min</span>
                            </div>
                        </div>
                    </div>

                    <!-- Quantity Change -->
                    <div class="flex items-center gap-4 bg-slate-800/40 p-4 rounded-2xl border border-slate-700/50">
                        <div class="text-center">
                            <p class="text-[10px] uppercase text-slate-500 font-bold mb-1">Actuel</p>
                            <p class="text-xl font-outfit font-bold text-white">${req.current_quantity}</p>
                        </div>
                        <div class="flex items-center justify-center px-4">
                            <i class="fas fa-arrow-right text-slate-600"></i>
                        </div>
                        <div class="text-center">
                            <p class="text-[10px] uppercase text-slate-500 font-bold mb-1 tracking-tight">Proposé</p>
                            <div class="flex items-center gap-2">
                                <p class="text-xl font-outfit font-bold text-white">${req.proposed_quantity}</p>
                                <span class="px-1.5 py-0.5 ${deltaClass} rounded text-[10px] font-black">${deltaSign}${req.quantity_delta}</span>
                            </div>
                        </div>
                    </div>

                    <!-- Machine Confidence -->
                    <div class="flex flex-col items-center">
                        <div class="relative w-16 h-16 flex items-center justify-center">
                            <svg class="w-full h-full -rotate-90">
                                <circle cx="32" cy="32" r="28" fill="transparent" stroke="#1e293b" stroke-width="6" />
                                <circle cx="32" cy="32" r="28" fill="transparent" stroke="#F0B429" stroke-width="6" 
                                    stroke-dasharray="175.9" stroke-dashoffset="${175.9 * (1 - req.avg_confidence)}" stroke-linecap="round" />
                            </svg>
                            <span class="absolute text-[11px] font-black text-white">${(req.avg_confidence * 100).toFixed(0)}%</span>
                        </div>
                        <p class="text-[10px] uppercase text-slate-500 font-bold mt-2">IA Confiance</p>
                    </div>

                    <!-- Actions -->
                    <div class="flex gap-3">
                        <button onclick="valManager.openRejectModal('${req.validation_code}')" class="w-12 h-12 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 transition-all flex items-center justify-center group/btn">
                            <i class="fas fa-times group-hover/btn:scale-110 transition-transform"></i>
                        </button>
                        <button onclick="valManager.approveRequest('${req.validation_code}')" class="px-6 h-12 rounded-xl bg-green-600 hover:bg-green-500 text-white font-bold transition-all shadow-lg flex items-center gap-2 active:scale-95">
                            <i class="fas fa-check"></i>
                            Valider Stock
                        </button>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });
    }

    async approveRequest(id) {
        try {
            const response = await fetch(`/api/validation/approve/${id}`, { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                this.showNotification('Succès', 'Stock mis à jour avec succès.', 'success');
                this.loadRequests();
            } else {
                this.showNotification('Erreur', result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Erreur', 'Échec de la validation Api.', 'error');
        }
    }

    openRejectModal(id) {
        this.currentRejectId = id;
        document.getElementById('reject-modal').classList.remove('hidden');
        document.getElementById('reject-reason').value = '';
        setTimeout(() => {
            document.getElementById('reject-modal').firstElementChild.classList.remove('scale-95');
        }, 10);
    }

    closeRejectModal() {
        document.getElementById('reject-modal').classList.add('hidden');
    }

    async confirmReject() {
        const reason = document.getElementById('reject-reason').value.trim();
        if (!reason) {
            alert('Veuillez indiquer une raison pour le rejet.');
            return;
        }

        try {
            const response = await fetch(`/api/validation/reject/${this.currentRejectId}?reason=${encodeURIComponent(reason)}`, {
                method: 'POST'
            });
            const result = await response.json();

            if (result.success) {
                this.showNotification('Rejeté', 'Détection IA écartée.', 'warning');
                this.closeRejectModal();
                this.loadRequests();
            }
        } catch (error) {
            this.showNotification('Erreur', 'Échec du rejet API.', 'error');
        }
    }

    showNotification(title, message, type = 'success') {
        const notif = document.getElementById('notif-bar');
        const icon = document.getElementById('notif-icon');
        const titleEl = document.getElementById('notif-title');
        const msgEl = document.getElementById('notif-msg');

        titleEl.textContent = title;
        msgEl.textContent = message;

        // Reset classes
        icon.className = 'w-10 h-10 rounded-full flex items-center justify-center ';

        if (type === 'success') {
            icon.classList.add('bg-green-500/20', 'text-green-500');
            icon.innerHTML = '<i class="fas fa-check"></i>';
        } else if (type === 'warning') {
            icon.classList.add('bg-yellow-500/20', 'text-yellow-500');
            icon.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
        } else {
            icon.classList.add('bg-red-500/20', 'text-red-500');
            icon.innerHTML = '<i class="fas fa-times"></i>';
        }

        notif.style.transform = 'translateY(0)';
        setTimeout(() => {
            notif.style.transform = 'translateY(200%)';
        }, 5000);
    }
}

// Global instance for onclick
let valManager;
document.addEventListener('DOMContentLoaded', () => {
    valManager = new ValidationManager();
});

// Helper for close button
function closeRejectModal() {
    valManager.closeRejectModal();
}
