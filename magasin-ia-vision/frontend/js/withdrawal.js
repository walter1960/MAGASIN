/**
 * Withdrawal Management JavaScript Module
 * Handles material withdrawal requests workflow for 19 African countries
 */

class WithdrawalManager {
    constructor() {
        this.requests = [];
        this.equipmentTypes = [];
        this.countries = [
            'Bénin', 'Burkina Faso', 'Cameroun', 'Centrafrique', 'Congo', 'Côte d\'Ivoire',
            'Gabon', 'Guinée', 'Guinée Bissau', 'Guinée Équatoriale', 'Madagascar',
            'Mali', 'Mauritanie', 'Niger', 'République Démocratique du Congo',
            'Sénégal', 'Tchad', 'Togo', 'Sénégal (Dakar HQ)'
        ];

        this.init();
    }

    async init() {
        console.log('Initializing Withdrawal Manager...');
        await this.loadWithdrawals();
        await this.loadEquipmentTypes();
        this.setupEventListeners();
        this.renderRequestsTable();
    }

    setupEventListeners() {
        // New withdrawal request button
        const newRequestBtn = document.getElementById('new-withdrawal-btn');
        if (newRequestBtn) {
            newRequestBtn.addEventListener('click', () => this.showRequestForm());
        }

        // Filter by status
        const statusFilter = document.getElementById('status-filter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.filterStatus = e.target.value;
                this.renderRequestsTable();
            });
        }

        // Filter by country
        const countryFilter = document.getElementById('country-filter');
        if (countryFilter) {
            countryFilter.addEventListener('change', (e) => {
                this.filterCountry = e.target.value;
                this.renderRequestsTable();
            });
        }
    }

    async loadWithdrawals() {
        try {
            const response = await fetch('/api/withdrawals');
            const data = await response.json();

            if (data.success) {
                this.requests = data.data || [];
                console.log(`Loaded ${this.requests.length} withdrawal requests`);
            }
        } catch (error) {
            console.error('Error loading withdrawals:', error);
            this.loadMockWithdrawals();
        }
    }

    loadMockWithdrawals() {
        this.requests = [
            {
                id: 1,
                requesterName: 'Jean Kouassi',
                requesterCountry: 'Côte d\'Ivoire',
                requesterEmail: 'j.kouassi@asecna.ci',
                equipmentType: 'RAM DDR4 8GB',
                quantityRequested: 50,
                status: 'pending',
                requestedAt: '2026-02-13T10:30:00Z',
                notes: 'Urgent: Mise à niveau serveurs'
            },
            {
                id: 2,
                requesterName: 'Aïcha Diallo',
                requesterCountry: 'Mali',
                requesterEmail: 'a.diallo@asecna.ml',
                equipmentType: 'Desktop Computer Dell',
                quantityRequested: 10,
                status: 'approved',
                requestedAt: '2026-02-12T14:20:00Z',
                approvedBy: 'Admin Dakar',
                approvedAt: '2026-02-13T09:00:00Z',
                notes: 'Nouveau bureau Bamako'
            },
            {
                id: 3,
                requesterName: 'Pierre Nkomo',
                requesterCountry: 'Gabon',
                requesterEmail: 'p.nkomo@asecna.ga',
                equipmentType: 'Air Conditioner Unit',
                quantityRequested: 5,
                status: 'completed',
                requestedAt: '2026-02-10T08:15:00Z',
                approvedBy: 'Admin Dakar',
                approvedAt: '2026-02-10T16:00:00Z',
                completedAt: '2026-02-11T11:30:00Z',
                notes: 'Livré via DHL'
            }
        ];
    }

    async loadEquipmentTypes() {
        try {
            const response = await fetch('/api/equipment/types');
            const data = await response.json();

            if (data.success) {
                this.equipmentTypes = data.data || [];
            }
        } catch (error) {
            console.error('Error loading equipment types:', error);
            this.equipmentTypes = [
                { id: 1, name: 'RAM DDR4 8GB' },
                { id: 2, name: 'Desktop Computer Dell' },
                { id: 3, name: 'Laptop Computer HP' },
                { id: 4, name: 'Air Conditioner Unit' },
                { id: 5, name: 'Printer HP LaserJet' },
                { id: 6, name: 'Network Switch' }
            ];
        }
    }

    renderRequestsTable() {
        const tbody = document.getElementById('withdrawals-tbody');
        if (!tbody) return;

        let filtered = [...this.requests];

        // Apply filters
        if (this.filterStatus && this.filterStatus !== 'all') {
            filtered = filtered.filter(r => r.status === this.filterStatus);
        }
        if (this.filterCountry && this.filterCountry !== 'all') {
            filtered = filtered.filter(r => r.requesterCountry === this.filterCountry);
        }

        if (filtered.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-6 py-8 text-center text-slate-400">
                        <span class="material-icons text-4xl mb-2">assignment</span>
                        <p>No withdrawal requests found</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = filtered.map(request => this.renderRequestRow(request)).join('');
    }

    renderRequestRow(request) {
        const statusBadges = {
            'pending': '<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-warning/10 text-warning border border-warning/20">🟡 Pending</span>',
            'approved': '<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-success/10 text-success border border-success/20">🟢 Approved</span>',
            'rejected': '<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-danger/10 text-danger border border-danger/20">🔴 Rejected</span>',
            'completed': '<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">✅ Completed</span>'
        };

        const requestDate = new Date(request.requestedAt);
        const timeAgo = this.getTimeAgo(requestDate);

        return `
            <tr class="hover:bg-neutral-800/50 transition-colors group" data-id="${request.id}">
                <td class="px-6 py-4 font-mono text-primary">#WD-${String(request.id).padStart(4, '0')}</td>
                <td class="px-6 py-4">
                    <div class="flex flex-col">
                        <span class="font-medium text-white">${request.requesterName}</span>
                        <span class="text-xs text-slate-400">${request.requesterCountry}</span>
                    </div>
                </td>
                <td class="px-6 py-4 text-slate-300">${request.equipmentType}</td>
                <td class="px-6 py-4 text-center">
                    <span class="inline-flex items-center justify-center w-10 h-10 rounded-full bg-primary/10 text-primary font-bold">
                        ${request.quantityRequested}
                    </span>
                </td>
                <td class="px-6 py-4">${statusBadges[request.status] || statusBadges['pending']}</td>
                <td class="px-6 py-4 text-slate-400 text-sm">${timeAgo}</td>
                <td class="px-6 py-4 text-right">
                    <div class="flex items-center justify-end gap-2">
                        ${request.status === 'pending' ? `
                            <button onclick="withdrawalManager.approveRequest(${request.id})" 
                                    class="px-3 py-1 text-xs bg-success hover:bg-success/80 text-white rounded transition-colors">
                                Approve
                            </button>
                            <button onclick="withdrawalManager.rejectRequest(${request.id})" 
                                    class="px-3 py-1 text-xs bg-danger hover:bg-danger/80 text-white rounded transition-colors">
                                Reject
                            </button>
                        ` : ''}
                        <button onclick="withdrawalManager.viewDetails(${request.id})" 
                                class="p-2 text-slate-400 hover:text-primary transition-colors">
                            <span class="material-icons text-sm">visibility</span>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    showRequestForm() {
        // Create modal HTML
        const modalHTML = `
            <div id="withdrawal-modal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div class="bg-surface-dark rounded-xl border border-neutral-700 p-6 w-full max-w-2xl mx-4">
                    <div class="flex items-center justify-between mb-6">
                        <h2 class="text-xl font-bold text-white">New Withdrawal Request</h2>
                        <button onclick="withdrawalManager.closeModal()" class="text-slate-400 hover:text-white">
                            <span class="material-icons">close</span>
                        </button>
                    </div>
                    
                    <form id="withdrawal-form" class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-2">Your Name</label>
                            <input type="text" id="requester-name" required
                                   class="w-full px-4 py-2 bg-background-dark border border-neutral-700 rounded-lg text-white focus:outline-none focus:border-primary">
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-2">Country</label>
                            <select id="requester-country" required
                                    class="w-full px-4 py-2 bg-background-dark border border-neutral-700 rounded-lg text-white focus:outline-none focus:border-primary">
                                <option value="">Select country...</option>
                                ${this.countries.map(c => `<option value="${c}">${c}</option>`).join('')}
                            </select>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-2">Email</label>
                            <input type="email" id="requester-email" required
                                   class="w-full px-4 py-2 bg-background-dark border border-neutral-700 rounded-lg text-white focus:outline-none focus:border-primary">
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-2">Equipment Type</label>
                            <select id="equipment-type" required
                                    class="w-full px-4 py-2 bg-background-dark border border-neutral-700 rounded-lg text-white focus:outline-none focus:border-primary">
                                <option value="">Select equipment...</option>
                                ${this.equipmentTypes.map(e => `<option value="${e.id}">${e.name}</option>`).join('')}
                            </select>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-2">Quantity Required</label>
                            <input type="number" id="quantity" min="1" required
                                   class="w-full px-4 py-2 bg-background-dark border border-neutral-700 rounded-lg text-white focus:outline-none focus:border-primary">
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-2">Notes (optional)</label>
                            <textarea id="notes" rows="3"
                                      class="w-full px-4 py-2 bg-background-dark border border-neutral-700 rounded-lg text-white focus:outline-none focus:border-primary"></textarea>
                        </div>
                        
                        <div class="flex gap-3 pt-4">
                            <button type="submit" class="flex-1 px-6 py-3 bg-primary hover:bg-primary-dark text-white font-medium rounded-lg transition-colors">
                                Submit Request
                            </button>
                            <button type="button" onclick="withdrawalManager.closeModal()" 
                                    class="px-6 py-3 bg-neutral-700 hover:bg-neutral-600 text-white font-medium rounded-lg transition-colors">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Setup form submit
        document.getElementById('withdrawal-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitRequest();
        });
    }

    async submitRequest() {
        const formData = {
            requesterName: document.getElementById('requester-name').value,
            requesterCountry: document.getElementById('requester-country').value,
            requesterEmail: document.getElementById('requester-email').value,
            equipmentTypeId: document.getElementById('equipment-type').value,
            quantityRequested: parseInt(document.getElementById('quantity').value),
            notes: document.getElementById('notes').value
        };

        try {
            // TODO: Implement actual API call
            console.log('Submitting withdrawal request:', formData);

            // Mock submission
            this.requests.unshift({
                id: this.requests.length + 1,
                ...formData,
                equipmentType: this.equipmentTypes.find(e => e.id == formData.equipmentTypeId)?.name,
                status: 'pending',
                requestedAt: new Date().toISOString()
            });

            this.closeModal();
            this.renderRequestsTable();
            this.showNotification('Withdrawal request submitted successfully', 'success');
        } catch (error) {
            console.error('Error submitting request:', error);
            this.showNotification('Failed to submit request', 'error');
        }
    }

    async approveRequest(id) {
        const request = this.requests.find(r => r.id === id);
        if (request && confirm(`Approve withdrawal request from ${request.requesterCountry}?`)) {
            try {
                // TODO: API call
                request.status = 'approved';
                request.approvedBy = 'Admin Dakar';
                request.approvedAt = new Date().toISOString();

                this.renderRequestsTable();
                this.showNotification('Request approved successfully', 'success');
            } catch (error) {
                this.showNotification('Failed to approve request', 'error');
            }
        }
    }

    async rejectRequest(id) {
        const request = this.requests.find(r => r.id === id);
        if (request) {
            const reason = prompt('Rejection reason:');
            if (reason) {
                request.status = 'rejected';
                request.rejectedReason = reason;

                this.renderRequestsTable();
                this.showNotification('Request rejected', 'warning');
            }
        }
    }

    viewDetails(id) {
        const request = this.requests.find(r => r.id === id);
        if (request) {
            console.log('Withdrawal details:', request);
            alert(JSON.stringify(request, null, 2));
        }
    }

    closeModal() {
        const modal = document.getElementById('withdrawal-modal');
        if (modal) {
            modal.remove();
        }
    }

    getTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);

        if (seconds < 60) return `${seconds}s ago`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    }

    showNotification(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed top-20 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${type === 'success' ? 'bg-success' :
                type === 'error' ? 'bg-danger' :
                    type === 'warning' ? 'bg-warning' :
                        'bg-primary'
            }`;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
}

// Initialize when DOM is ready
let withdrawalManager;
document.addEventListener('DOMContentLoaded', () => {
    withdrawalManager = new WithdrawalManager();
});
