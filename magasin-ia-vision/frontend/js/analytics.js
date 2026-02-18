/**
 * Analytics Dashboard JavaScript Module
 * Real-time analytics visualization with Chart.js
 */

class AnalyticsManager {
    constructor() {
        this.charts = {};
        this.refreshInterval = 30000; // 30 seconds
        this.autoRefresh = true;

        this.init();
    }

    async init() {
        console.log('Initializing Analytics Manager...');

        // Load Chart.js if not already loaded
        if (typeof Chart === 'undefined') {
            await this.loadChartJS();
        }

        await this.loadAnalyticsData();
        this.createCharts();
        this.setupEventListeners();

        // Auto-refresh
        if (this.autoRefresh) {
            setInterval(() => this.refreshData(), this.refreshInterval);
        }
    }

    async loadChartJS() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    setupEventListeners() {
        // Export buttons
        const exportExcelBtn = document.getElementById('export-excel-btn');
        if (exportExcelBtn) {
            exportExcelBtn.addEventListener('click', () => this.exportExcel());
        }

        const exportCsvBtn = document.getElementById('export-csv-btn');
        if (exportCsvBtn) {
            exportCsvBtn.addEventListener('click', () => this.exportCSV());
        }

        // Refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshData());
        }
    }

    async loadAnalyticsData() {
        try {
            const response = await fetch('/api/analytics/stats');
            const result = await response.json();

            if (result.success) {
                this.data = result.data;
                this.updateKPIs();
                console.log('Analytics data loaded successfully');
            } else {
                console.error('Failed to load analytics data');
                this.loadMockData();
            }
        } catch (error) {
            console.error('Error loading analytics:', error);
            this.loadMockData();
        }
    }

    loadMockData() {
        this.data = {
            total_stock: 1385,
            total_value: 2450000,
            movements_today: 23,
            withdrawals_pending: 5,
            ai_accuracy: 0.91,
            stock_by_category: [
                { name: "RAM", value: 450 },
                { name: "Computers", value: 535 },
                { name: "HVAC", value: 180 },
                { name: "Printers", value: 120 },
                { name: "Network", value: 100 }
            ],
            movements_trend: [
                { date: "2026-02-07", entries: 12, exits: 18 },
                { date: "2026-02-08", entries: 15, exits: 20 },
                { date: "2026-02-09", entries: 10, exits: 15 },
                { date: "2026-02-10", entries: 18, exits: 22 },
                { date: "2026-02-11", entries: 20, exits: 25 },
                { date: "2026-02-12", entries: 16, exits: 19 },
                { date: "2026-02-13", entries: 14, exits: 17 }
            ],
            withdrawals_by_country: [
                { country: "Côte d'Ivoire", count: 8 },
                { country: "Mali", count: 5 },
                { country: "Burkina Faso", count: 4 },
                { country: "Sénégal", count: 3 },
                { country: "Gabon", count: 2 },
                { country: "Other", count: 1 }
            ]
        };
        this.updateKPIs();
    }

    updateKPIs() {
        // Update KPI values
        const stockEl = document.getElementById('kpi-stock');
        if (stockEl) stockEl.textContent = this.data.total_stock.toLocaleString();

        const valueEl = document.getElementById('kpi-value');
        if (valueEl) valueEl.textContent = `${(this.data.total_value / 1000000).toFixed(1)}M FCFA`;

        const movementsEl = document.getElementById('kpi-movements');
        if (movementsEl) movementsEl.textContent = this.data.movements_today;

        const accuracyEl = document.getElementById('kpi-accuracy');
        if (accuracyEl) accuracyEl.textContent = `${(this.data.ai_accuracy * 100).toFixed(0)}%`;
    }

    createCharts() {
        this.createStockDistributionChart();
        this.createMovementsTrendChart();
        this.createWithdrawalsChart();
    }

    createStockDistributionChart() {
        const ctx = document.getElementById('stockDistributionChart');
        if (!ctx) return;

        const labels = this.data.stock_by_category.map(item => item.name);
        const values = this.data.stock_by_category.map(item => item.value);

        if (this.charts.stockDistribution) {
            this.charts.stockDistribution.destroy();
        }

        this.charts.stockDistribution = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: [
                        '#137fec',
                        '#10b981',
                        '#f59e0b',
                        '#ef4444',
                        '#8b5cf6'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#cbd5e1',
                            font: { size: 12 }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        titleColor: '#fff',
                        bodyColor: '#cbd5e1',
                        borderColor: '#334155',
                        borderWidth: 1
                    }
                }
            }
        });
    }

    createMovementsTrendChart() {
        const ctx = document.getElementById('movementsTrendChart');
        if (!ctx) return;

        const labels = this.data.movements_trend.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });
        const entries = this.data.movements_trend.map(item => item.entries);
        const exits = this.data.movements_trend.map(item => item.exits);

        if (this.charts.movementsTrend) {
            this.charts.movementsTrend.destroy();
        }

        this.charts.movementsTrend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Entries',
                        data: entries,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Exits',
                        data: exits,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#cbd5e1',
                            font: { size: 12 }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        titleColor: '#fff',
                        bodyColor: '#cbd5e1',
                        borderColor: '#334155',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: '#334155'
                        },
                        ticks: {
                            color: '#94a3b8'
                        }
                    },
                    y: {
                        grid: {
                            color: '#334155'
                        },
                        ticks: {
                            color: '#94a3b8'
                        }
                    }
                }
            }
        });
    }

    createWithdrawalsChart() {
        const ctx = document.getElementById('withdrawalsChart');
        if (!ctx) return;

        const labels = this.data.withdrawals_by_country.map(item => item.country);
        const values = this.data.withdrawals_by_country.map(item => item.count);

        if (this.charts.withdrawals) {
            this.charts.withdrawals.destroy();
        }

        this.charts.withdrawals = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Withdrawal Requests',
                    data: values,
                    backgroundColor: '#137fec',
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        titleColor: '#fff',
                        bodyColor: '#cbd5e1',
                        borderColor: '#334155',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#94a3b8'
                        }
                    },
                    y: {
                        grid: {
                            color: '#334155'
                        },
                        ticks: {
                            color: '#94a3b8',
                            stepSize: 2
                        }
                    }
                }
            }
        });
    }

    async refreshData() {
        console.log('Refreshing analytics data...');
        await this.loadAnalyticsData();
        this.createCharts();
        this.showNotification('Dashboard refreshed', 'info');
    }

    async exportExcel() {
        try {
            const response = await fetch('/api/reports/export/excel');
            const blob = await response.blob();

            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ASECNA_Weekly_Report_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.showNotification('Excel report downloaded successfully', 'success');
        } catch (error) {
            console.error('Error exporting Excel:', error);
            this.showNotification('Failed to export Excel report', 'error');
        }
    }

    async exportCSV(sheet = 'summary') {
        try {
            const response = await fetch(`/api/reports/export/csv?sheet=${sheet}`);
            const blob = await response.blob();

            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ASECNA_${sheet}_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.showNotification('CSV report downloaded successfully', 'success');
        } catch (error) {
            console.error('Error exporting CSV:', error);
            this.showNotification('Failed to export CSV report', 'error');
        }
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
let analyticsManager;
document.addEventListener('DOMContentLoaded', () => {
    analyticsManager = new AnalyticsManager();
});
