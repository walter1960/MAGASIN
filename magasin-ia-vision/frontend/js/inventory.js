/**
 * Inventory Management JavaScript Module - ASECNA Version
 * Handles real-time equipment data from Backend and IA counting integration.
 */

class InventoryManager {
    constructor() {
        this.equipmentData = [];
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.filters = {
            search: '',
            category: 'all',
            status: 'all'
        };

        this.init();

        // Auto-refresh stats every 30 seconds
        setInterval(() => this.loadStats(), 30000);
    }

    async init() {
        console.log('Initializing ASECNA Inventory Manager...');
        this.showLoading();
        await Promise.all([
            this.loadEquipment(),
            this.loadStats()
        ]);
        this.setupEventListeners();
        this.populateCategories();
        this.renderTable();
    }

    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filters.search = e.target.value;
                this.currentPage = 1;
                this.renderTable();
            });
        }

        // Category filter
        const categoryFilter = document.getElementById('category-filter');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', (e) => {
                this.filters.category = e.target.value;
                this.currentPage = 1;
                this.renderTable();
            });
        }

        // Status filter
        const statusFilter = document.getElementById('status-filter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.filters.status = e.target.value;
                this.currentPage = 1;
                this.renderTable();
            });
        }

        // Export button
        const exportButton = document.getElementById('export-btn');
        if (exportButton) {
            exportButton.addEventListener('click', () => this.exportData());
        }
    }

    async loadEquipment() {
        try {
            const response = await fetch('/api/equipment');
            const data = await response.json();

            if (data.success) {
                this.equipmentData = data.data || [];
                console.log(`Loaded ${this.equipmentData.length} items from server`);
            }
        } catch (error) {
            console.error('Error loading equipment:', error);
            this.showNotification('Error connecting to backend', 'error');
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();

            if (data.success && data.data) {
                const s = data.data;
                this.updateKPI('stat-total-inventory', s.total_inventory);
                this.updateKPI('stat-active-use', s.active_in_use);
                this.updateKPI('stat-critical-alerts', s.critical_alerts);
                this.updateKPI('stat-low-stock', s.low_stock_warnings);
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    updateKPI(id, value) {
        const el = document.getElementById(id);
        if (el) {
            // Animating number update
            const startStr = el.textContent.replace(',', '');
            const start = isNaN(parseInt(startStr)) ? 0 : parseInt(startStr);
            const end = parseInt(value) || 0;

            if (start === end) {
                el.textContent = end.toLocaleString();
                return;
            }

            let current = start;
            const duration = 1000;
            const step = Math.ceil(Math.abs(end - start) / (duration / 16));

            const animate = () => {
                if (current < end) {
                    current = Math.min(current + step, end);
                    el.textContent = current.toLocaleString();
                    requestAnimationFrame(animate);
                } else if (current > end) {
                    current = Math.max(current - step, end);
                    el.textContent = current.toLocaleString();
                    requestAnimationFrame(animate);
                }
            };
            animate();
        }
    }

    populateCategories() {
        const categories = [...new Set(this.equipmentData.map(item => item.category))];
        const select = document.getElementById('category-filter');
        if (select) {
            // Keep "All Categories"
            select.innerHTML = '<option value="all">All Categories</option>';
            categories.forEach(cat => {
                if (cat) {
                    const option = document.createElement('option');
                    option.value = cat;
                    option.textContent = cat;
                    select.appendChild(option);
                }
            });
        }
    }

    filterEquipment() {
        let filtered = [...this.equipmentData];

        // Search filter
        if (this.filters.search) {
            const search = this.filters.search.toLowerCase();
            filtered = filtered.filter(item =>
                (item.unique_ref && item.unique_ref.toLowerCase().includes(search)) ||
                (item.name && item.name.toLowerCase().includes(search)) ||
                (item.category && item.category.toLowerCase().includes(search))
            );
        }

        // Category filter
        if (this.filters.category !== 'all') {
            filtered = filtered.filter(item =>
                item.category === this.filters.category
            );
        }

        // Status filter
        if (this.filters.status !== 'all') {
            filtered = filtered.filter(item =>
                item.status === this.filters.status
            );
        }

        return filtered;
    }

    renderTable() {
        const tbody = document.getElementById('equipment-tbody');
        if (!tbody) return;

        const filtered = this.filterEquipment();
        const start = (this.currentPage - 1) * this.itemsPerPage;
        const end = start + this.itemsPerPage;
        const pageData = filtered.slice(start, end);

        if (pageData.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="px-6 py-12 text-center text-slate-500">
                        <div class="flex flex-col items-center">
                            <span class="material-icons text-5xl mb-3 opacity-20">inventory_2</span>
                            <p class="text-lg font-medium">Aucun équipement trouvé</p>
                            <p class="text-sm">Essayez de modifier vos filtres ou votre recherche.</p>
                        </div>
                    </td>
                </tr>
            `;
            this.updatePagination(0);
            return;
        }

        tbody.innerHTML = pageData.map(item => this.renderRow(item)).join('');
        this.updatePagination(filtered.length);
    }

    renderRow(item) {
        // Discrepancy logic for ASECNA Stock
        const declared = item.declared_quantity || 0;
        const detected = item.detected_quantity || 0;
        const hasDiscrepancy = Math.abs(declared - detected) > 0;
        const rowClass = hasDiscrepancy ? 'bg-amber-500/5' : '';

        const statusBadges = {
            'in_stock': '<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-success/10 text-success border border-success/20"><span class="h-1.5 w-1.5 rounded-full bg-success"></span>En Stock</span>',
            'in_use': '<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20"><span class="h-1.5 w-1.5 rounded-full bg-blue-400"></span>Utilisé</span>',
            'missing': '<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-danger/10 text-danger border border-danger/20"><span class="h-1.5 w-1.5 rounded-full bg-danger animate-pulse"></span>Manquant</span>',
            'maintenance': '<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-warning/10 text-warning border border-warning/20"><span class="h-1.5 w-1.5 rounded-full bg-warning"></span>Maintenance</span>'
        };

        const statusHtml = statusBadges[item.status] || `<span class="text-slate-500">${item.status}</span>`;

        return `
            <tr class="hover:bg-neutral-800/50 transition-colors group ${rowClass}" data-id="${item.id}">
                <td class="px-6 py-4">
                    <div class="flex items-center gap-3">
                        <div class="h-10 w-10 rounded bg-neutral-700 flex-shrink-0 flex items-center justify-center">
                            <i class="material-icons text-primary-light">inventory</i>
                        </div>
                        <div>
                            <span class="font-medium text-white block">${item.name}</span>
                            <span class="text-[10px] text-slate-500 uppercase font-black tracking-tighter">${item.category}</span>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4 font-mono text-xs text-slate-400">${item.unique_ref}</td>
                <td class="px-6 py-4 text-slate-300">
                    <span class="px-2 py-1 bg-slate-800 rounded text-xs">${item.category.split(' ')[0]}</span>
                </td>
                <td class="px-6 py-4">${statusHtml}</td>
                <td class="px-6 py-4">
                    <div class="flex flex-col">
                        <div class="flex justify-between items-center w-24">
                            <span class="text-[10px] text-slate-500 uppercase font-bold">Théorique</span>
                            <span class="text-sm font-bold text-white">${declared}</span>
                        </div>
                        <div class="flex justify-between items-center w-24 mt-1">
                            <span class="text-[10px] text-slate-500 uppercase font-bold">IA Détecté</span>
                            <span class="text-sm font-bold ${hasDiscrepancy ? 'text-amber-400' : 'text-success'}">${detected}</span>
                        </div>
                        ${item.counting_confidence ? `
                        <div class="w-24 h-1 bg-slate-800 rounded-full mt-2 overflow-hidden">
                            <div class="h-full bg-primary" style="width: ${item.counting_confidence * 100}%"></div>
                        </div>
                        ` : ''}
                    </div>
                </td>
                <td class="px-6 py-4">
                    <button class="flex items-center gap-2 text-primary hover:text-primary-light transition-colors group/cam">
                        <span class="material-icons text-sm group-hover/cam:scale-110 transition-transform">videocam</span>
                        <span class="text-xs font-medium underline underline-offset-4">${item.zone_name}</span>
                    </button>
                </td>
                <td class="px-6 py-4 text-xs text-slate-400">${item.last_seen}</td>
                <td class="px-6 py-4 text-right">
                    <button class="p-2 text-slate-600 hover:text-white transition-colors">
                        <span class="material-icons">more_vert</span>
                    </button>
                </td>
            </tr>
        `;
    }

    updatePagination(totalItems) {
        const totalPages = Math.ceil(totalItems / this.itemsPerPage);
        const info = document.getElementById('pagination-info');
        const buttons = document.getElementById('pagination-buttons');

        if (info) {
            const start = totalItems === 0 ? 0 : (this.currentPage - 1) * this.itemsPerPage + 1;
            const end = Math.min(this.currentPage * this.itemsPerPage, totalItems);
            info.innerHTML = `Affichage <span class="font-bold text-white">${start}-${end}</span> sur <span class="font-bold text-white">${totalItems}</span>`;
        }

        if (buttons) {
            let html = `
                <button onclick="inventoryManager.setPage(${this.currentPage - 1})" 
                        class="px-2 py-1 text-xs border border-neutral-700 rounded text-slate-500 hover:text-white ${this.currentPage === 1 ? 'opacity-50 cursor-not-allowed' : ''}"
                        ${this.currentPage === 1 ? 'disabled' : ''}>Précédent</button>
            `;

            for (let i = 1; i <= totalPages; i++) {
                if (i === 1 || i === totalPages || (i >= this.currentPage - 1 && i <= this.currentPage + 1)) {
                    const activeClass = i === this.currentPage ? 'bg-primary border-primary text-white font-bold' : 'border-neutral-700 text-slate-500 hover:text-white';
                    html += `<button onclick="inventoryManager.setPage(${i})" class="px-3 py-1 text-xs border rounded ${activeClass}">${i}</button>`;
                } else if (i === 2 || i === totalPages - 1) {
                    html += `<span class="text-slate-700">...</span>`;
                }
            }

            html += `
                <button onclick="inventoryManager.setPage(${this.currentPage + 1})" 
                        class="px-2 py-1 text-xs border border-neutral-700 rounded text-slate-500 hover:text-white ${this.currentPage === totalPages ? 'opacity-50 cursor-not-allowed' : ''}"
                        ${this.currentPage === totalPages ? 'disabled' : ''}>Suivant</button>
            `;
            buttons.innerHTML = html;
        }
    }

    setPage(page) {
        const totalPages = Math.ceil(this.filterEquipment().length / this.itemsPerPage);
        if (page >= 1 && page <= totalPages) {
            this.currentPage = page;
            this.renderTable();
        }
    }

    showLoading() {
        const tbody = document.getElementById('equipment-tbody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="px-6 py-20 text-center">
                        <div class="flex flex-col items-center">
                            <div class="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4"></div>
                            <p class="text-slate-400 animate-pulse">Synchronisation avec le dépôt central...</p>
                        </div>
                    </td>
                </tr>
            `;
        }
    }

    showNotification(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-8 right-8 px-6 py-3 rounded-xl shadow-2xl text-white z-50 font-medium transform transition-all duration-300 translate-y-20 opacity-0 ${type === 'success' ? 'bg-emerald-600' :
                type === 'error' ? 'bg-rose-600' :
                    'bg-blue-600'
            }`;
        toast.innerHTML = `<div class="flex items-center gap-3"><i class="material-icons text-sm">${type === 'success' ? 'check_circle' : 'info'}</i>${message}</div>`;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.remove('translate-y-20', 'opacity-0');
        }, 100);

        setTimeout(() => {
            toast.classList.add('translate-y-20', 'opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    exportData() {
        // Simple CSV export
        const data = this.filterEquipment();
        const headers = ["ID", "Reference", "Nom", "Categorie", "Statut", "Theorique", "Detecte", "Zone", "Derniere Vue"];
        const rows = data.map(i => [i.id, i.unique_ref, i.name, i.category, i.status, i.declared_quantity, i.detected_quantity, i.zone_name, i.last_seen]);

        let csvContent = "data:text/csv;charset=utf-8," + headers.join(",") + "\n" + rows.map(r => r.join(",")).join("\n");
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `inventory_asecna_${new Date().toLocaleDateString()}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        this.showNotification("Exportation terminée", "success");
    }
}

let inventoryManager;
document.addEventListener('DOMContentLoaded', () => {
    inventoryManager = new InventoryManager();
});
