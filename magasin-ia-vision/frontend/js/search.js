/**
 * Object Search JavaScript for ASECNA Stock IA
 */

class ObjectSearch {
    constructor() {
        this.searchBtn = document.getElementById('search-btn');
        this.searchInput = document.getElementById('search-query');
        this.resultsContainer = document.getElementById('search-results');
        this.countContainer = document.getElementById('results-count');
        this.countNum = document.getElementById('count-num');
        this.emptyState = document.getElementById('empty-state');

        this.initEventListeners();
    }

    initEventListeners() {
        this.searchBtn.addEventListener('click', () => this.performSearch());
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
    }

    async performSearch() {
        const query = this.searchInput.value.trim();
        if (!query) return;

        // UI Feedback
        this.searchBtn.disabled = true;
        this.searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        this.resultsContainer.classList.add('opacity-50');

        try {
            const response = await fetch(`/api/search/object?name=${encodeURIComponent(query)}`);
            const result = await response.json();

            if (result.success) {
                this.renderResults(result.data);
            }
        } catch (error) {
            console.error('Search error:', error);
        } finally {
            this.searchBtn.disabled = false;
            this.searchBtn.innerHTML = 'Rechercher';
            this.resultsContainer.classList.remove('opacity-50');
        }
    }

    renderResults(results) {
        this.resultsContainer.innerHTML = '';

        if (results.length === 0) {
            this.countContainer.classList.add('hidden');
            this.emptyState.classList.remove('hidden');
            this.emptyState.innerHTML = `
                <i class="fas fa-search-minus text-7xl mb-6"></i>
                <p class="text-xl font-medium">Aucun objet correspondant trouvé</p>
                <p class="text-slate-500 mt-2">Réessayez avec un autre mot-clé</p>
            `;
            return;
        }

        this.emptyState.classList.add('hidden');
        this.countContainer.classList.remove('hidden');
        this.countNum.textContent = results.length;

        results.forEach(item => {
            const card = document.createElement('div');
            card.className = 'glass-panel p-6 hover:shadow-2xl transition-all hover:scale-[1.02] cursor-pointer group flex flex-col';
            card.onclick = () => this.showTrackingModal(item);

            const confColor = item.avg_confidence > 0.8 ? 'text-green-400' : 'text-yellow-500';
            const statusColor = this.getStatusColor(item.status);

            card.innerHTML = `
                <div class="flex justify-between items-start mb-4">
                    <div class="w-12 h-12 bg-slate-800 rounded-xl flex items-center justify-center border border-slate-700 group-hover:border-blue-500/50 transition-colors">
                        <i class="fas fa-microchip text-blue-400 text-xl"></i>
                    </div>
                    <span class="px-2 py-1 ${statusColor} bg-opacity-10 border border-current border-opacity-20 rounded text-[10px] font-bold uppercase tracking-wider">
                        ${item.status}
                    </span>
                </div>
                
                <h4 class="text-xl font-bold text-white mb-1">${item.object_type}</h4>
                <p class="text-slate-400 text-xs flex items-center gap-2 mb-6">
                    <i class="fas fa-video text-blue-500"></i>
                    ${item.camera_id}
                </p>

                <div class="mt-auto grid grid-cols-2 gap-4">
                    <div class="bg-slate-800/50 p-3 rounded-xl border border-slate-700/50">
                        <p class="text-[10px] uppercase text-slate-500 font-bold mb-1">Durée</p>
                        <p class="text-sm font-semibold text-white">${item.duration.toFixed(0)} min</p>
                    </div>
                    <div class="bg-slate-800/50 p-3 rounded-xl border border-slate-700/50">
                        <p class="text-[10px] uppercase text-slate-500 font-bold mb-1">Confiance</p>
                        <p class="text-sm font-semibold ${confColor}">${(item.avg_confidence * 100).toFixed(1)}%</p>
                    </div>
                </div>

                <div class="mt-6 pt-4 border-t border-slate-700 flex items-center justify-between group-hover:text-blue-400 transition-colors">
                    <span class="text-xs font-semibold uppercase">Localisation Live</span>
                    <i class="fas fa-arrow-right text-xs"></i>
                </div>
            `;
            this.resultsContainer.appendChild(card);
        });
    }

    getStatusColor(status) {
        switch (status) {
            case 'stable': return 'text-green-400';
            case 'pending_validation': return 'text-yellow-500';
            case 'tracking': return 'text-blue-400';
            case 'validated': return 'text-emerald-500';
            default: return 'text-slate-400';
        }
    }

    showTrackingModal(item) {
        const modal = document.getElementById('tracking-modal');
        document.getElementById('modal-cam').textContent = item.camera_id;
        document.getElementById('modal-type').textContent = item.object_type;
        document.getElementById('modal-duration').textContent = `${item.duration.toFixed(0)} min`;
        document.getElementById('modal-conf').textContent = `${(item.avg_confidence * 100).toFixed(1)}%`;
        document.getElementById('modal-link').href = item.tracking_link;

        modal.classList.remove('hidden');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ObjectSearch();
});
