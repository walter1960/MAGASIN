/**
 * Global Notification Service for ASECNA Stock IA
 * Connects to common system-wide notifications via WebSocket.
 */

class NotificationService {
    constructor(host = window.location.host) {
        this.host = host;
        this.wsUrl = `ws://${host}/ws/notifications`;
        this.ws = null;
        this.reconnectInterval = 5000;
        this.notifBar = null;
        this.notifIcon = null;
        this.notifTitle = null;
        this.notifMsg = null;

        this.init();
    }

    init() {
        // Find or create notification UI components
        document.addEventListener('DOMContentLoaded', () => {
            this.prepareUI();
            this.connect();
        });
    }

    prepareUI() {
        this.notifBar = document.getElementById('notif-bar');
        this.notifIcon = document.getElementById('notif-icon');
        this.notifTitle = document.getElementById('notif-title');
        this.notifMsg = document.getElementById('notif-msg');

        // If not found, we could inject a global notification bar here or fail silently
        if (!this.notifBar) {
            console.warn("Notification bar UI not found on this page. Creating dynamic overlay.");
            this.createDynamicUI();
        }
    }

    createDynamicUI() {
        const container = document.createElement('div');
        container.id = 'notif-bar';
        container.className = 'fixed bottom-8 right-8 bg-slate-800/90 backdrop-blur-md p-4 px-6 translate-y-[200%] transition-all duration-500 z-[100] flex items-center gap-4 rounded-2xl border border-slate-700 shadow-2xl';
        container.innerHTML = `
            <div id="notif-icon" class="w-10 h-10 rounded-full flex items-center justify-center bg-blue-500/20 text-blue-500">
                <i class="fas fa-info"></i>
            </div>
            <div class="cursor-pointer" id="notif-content">
                <p id="notif-title" class="font-bold text-white text-sm">IA System</p>
                <p id="notif-msg" class="text-[12px] text-slate-400">Initialisation...</p>
            </div>
        `;
        document.body.appendChild(container);

        this.notifBar = container;
        this.notifIcon = container.querySelector('#notif-icon');
        this.notifTitle = container.querySelector('#notif-title');
        this.notifMsg = container.querySelector('#notif-msg');

        // Add click listener to navigate to relevant page if info provided
        container.addEventListener('click', () => {
            if (this.currentData && this.currentData.data) {
                const data = this.currentData.data;
                if (data.id) {
                    window.location.href = `validation.html`;
                }
            }
        });
    }

    connect() {
        console.log(`Connecting to notification system at ${this.wsUrl}`);
        this.ws = new WebSocket(this.wsUrl);

        this.ws.onopen = () => {
            console.log("Notification system connected.");
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleNotification(data);
        };

        this.ws.onclose = () => {
            console.log("Notification system disconnected. Retrying...");
            setTimeout(() => this.connect(), this.reconnectInterval);
        };
    }

    handleNotification(data) {
        this.currentData = data;

        let type = 'info';
        if (data.type === 'VALIDATION_CREATED') type = 'warning';
        if (data.type === 'VALIDATION_APPROVED') type = 'success';
        if (data.type === 'VALIDATION_REJECTED') type = 'error';

        this.show(data.message, type);

        // Custom sound if needed
        // this.playAlert();
    }

    show(message, type = 'info') {
        if (!this.notifBar) return;

        this.notifMsg.textContent = message;

        // Style based on type
        this.notifIcon.className = 'w-10 h-10 rounded-full flex items-center justify-center ';
        if (type === 'success') {
            this.notifIcon.classList.add('bg-green-500/20', 'text-green-500');
            this.notifIcon.innerHTML = '<i class="fas fa-check"></i>';
            this.notifTitle.textContent = 'Action Validée';
        } else if (type === 'warning') {
            this.notifIcon.classList.add('bg-yellow-500/20', 'text-yellow-500');
            this.notifIcon.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
            this.notifTitle.textContent = 'Alerte Stock IA';
        } else if (type === 'error') {
            this.notifIcon.classList.add('bg-red-500/20', 'text-red-500');
            this.notifIcon.innerHTML = '<i class="fas fa-times"></i>';
            this.notifTitle.textContent = 'Action Rejetée';
        } else {
            this.notifIcon.classList.add('bg-blue-500/20', 'text-blue-500');
            this.notifIcon.innerHTML = '<i class="fas fa-info"></i>';
            this.notifTitle.textContent = 'Information Système';
        }

        this.notifBar.style.transform = 'translateY(0)';
        setTimeout(() => {
            this.notifBar.style.transform = 'translateY(200%)';
        }, 8000);
    }
}

// Global instance
const notificationService = new NotificationService();
