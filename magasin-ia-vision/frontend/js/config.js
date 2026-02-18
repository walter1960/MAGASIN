/**
 * Config Manager JavaScript for ASECNA Stock IA
 * Handles interaction with Configuration API
 */

class ConfigManager {
    constructor() {
        this.countries = [];
        this.aiSettings = {
            stability_duration_minutes: 60,
            confidence_threshold: 0.60,
            alert_delay_hours: 3
        };

        this.initEventListeners();
        this.loadConfig();
        this.loadEquipmentTypes();
        this.loadActiveCameras();
    }

    initEventListeners() {
        // Range Sliders
        const stabilityRange = document.getElementById('stability-range');
        const confidenceRange = document.getElementById('confidence-range');
        const alertRange = document.getElementById('alert-range');

        stabilityRange.addEventListener('input', (e) => {
            const val = e.target.value;
            document.getElementById('stability-val').textContent = `${val} min`;
        });

        confidenceRange.addEventListener('input', (e) => {
            const val = e.target.value;
            document.getElementById('confidence-val').textContent = `${val}%`;
        });

        alertRange.addEventListener('input', (e) => {
            const val = e.target.value;
            document.getElementById('alert-val').textContent = `${val} ${val > 1 ? 'heures' : 'heure'}`;
        });

        // Action Buttons
        document.getElementById('save-ai-settings').addEventListener('click', () => this.saveAiSettings());
        document.getElementById('add-country').addEventListener('click', () => this.addCountry());
        document.getElementById('save-countries').addEventListener('click', () => this.saveCountries());

        // IP Camera Buttons
        document.getElementById('add-camera-btn').addEventListener('click', () => this.addIpCamera());

        // Enter key for country
        document.getElementById('new-country').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addCountry();
        });
    }

    async loadEquipmentTypes() {
        try {
            const response = await fetch('/api/equipment-types');
            const result = await response.json();
            if (result.success) {
                const select = document.getElementById('cam-equipment-type');
                select.innerHTML = '<option value="">-- Sélectionner un type --</option>';
                result.data.forEach(type => {
                    const opt = document.createElement('option');
                    opt.value = type.id;
                    opt.textContent = type.name;
                    select.appendChild(opt);
                });
            }
        } catch (error) {
            console.error('Error loading equipment types:', error);
        }
    }

    async addIpCamera() {
        const zoneName = document.getElementById('cam-zone-name').value.trim();
        const ipAddress = document.getElementById('cam-ip-address').value.trim();
        const equipmentTypeId = document.getElementById('cam-equipment-type').value;

        if (!zoneName || !ipAddress) {
            this.showNotification('Erreur', 'Veuillez remplir le nom de zone et l\'adresse IP.', 'error');
            return;
        }

        const btn = document.getElementById('add-camera-btn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Ajout en cours...';

        try {
            const response = await fetch('/api/cameras/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    zone_name: zoneName,
                    ip_address: ipAddress,
                    equipment_type_id: parseInt(equipmentTypeId) || null
                })
            });

            const result = await response.json();
            if (result.success) {
                this.showNotification('Succès', 'Caméra IP ajoutée et activée.');
                document.getElementById('cam-zone-name').value = '';
                document.getElementById('cam-ip-address').value = '';
                this.loadActiveCameras();
            } else {
                this.showNotification('Erreur', result.message, 'error');
            }
        } catch (error) {
            console.error('Error adding camera:', error);
            this.showNotification('Erreur', 'Échec de la connexion au serveur.', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-plus-circle text-lg"></i> Ajouter le Flux Caméra';
        }
    }

    async loadActiveCameras() {
        try {
            const response = await fetch('/api/cameras/status');
            const result = await response.json();
            if (result.success) {
                this.renderActiveCameras(result.cameras || {});
            }
        } catch (error) {
            console.error('Error loading active cameras:', error);
        }
    }

    renderActiveCameras(cameras) {
        const list = document.getElementById('active-cameras-list');
        list.innerHTML = '';

        // Always show the system webcam if it's there or simulated
        const entries = Object.entries(cameras);

        if (entries.length === 0) {
            list.innerHTML = `
                <div class="p-4 bg-slate-800/50 border border-slate-700 rounded-xl flex items-center gap-4">
                    <div class="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div>
                    <div class="flex-1">
                        <p class="text-xs font-bold text-white">Webcam Locale (Défaut)</p>
                        <p class="text-[10px] text-slate-500">Source: 0 (Pour tests IA)</p>
                    </div>
                </div>
            `;
            return;
        }

        entries.forEach(([id, cam]) => {
            const card = document.createElement('div');
            card.className = 'p-4 bg-slate-800/50 border border-slate-700 rounded-xl flex items-center gap-4 group';
            card.innerHTML = `
                <div class="w-2 h-2 rounded-full ${cam.running ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500'}"></div>
                <div class="flex-1">
                    <p class="text-xs font-bold text-white truncate" title="${cam.zone}">${cam.zone}</p>
                    <p class="text-[10px] text-slate-500 truncate" title="${cam.source}">${cam.source}</p>
                </div>
                ${cam.source === '0' ?
                    '<i class="fas fa-lock text-slate-600 text-xs"></i>' :
                    `<button class="text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity" onclick="configManager.removeCamera('${id}')">
                        <i class="fas fa-trash"></i>
                    </button>`
                }
            `;
            list.appendChild(card);
        });
    }

    async removeCamera(id) {
        if (!confirm('Voulez-vous vraiment supprimer ce flux caméra ?')) return;

        try {
            const response = await fetch(`/api/cameras/${id}`, { method: 'DELETE' });
            const result = await response.json();
            if (result.success) {
                this.showNotification('Supprimé', 'Flux caméra retiré du système.');
                this.loadActiveCameras();
            }
        } catch (error) {
            this.showNotification('Erreur', 'Échec de la suppression.', 'error');
        }
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/config/detection');
            const result = await response.json();

            if (result.success) {
                const data = result.data;
                this.updateUiWithConfig(data);

                // Parse countries
                try {
                    this.countries = typeof data.asecna_countries === 'string'
                        ? JSON.parse(data.asecna_countries)
                        : data.asecna_countries || [];
                    this.renderCountries();
                } catch (e) {
                    console.error("Failed to parse countries:", e);
                    this.countries = [];
                }
            }
        } catch (error) {
            console.error('Error loading config:', error);
            this.showNotification('Erreur', 'Impossible de charger la configuration.', 'error');
        }
    }

    updateUiWithConfig(data) {
        // Stability
        const stability = data.stability_duration_minutes || 60;
        document.getElementById('stability-range').value = stability;
        document.getElementById('stability-val').textContent = `${stability} min`;

        // Confidence
        const confidence = (data.confidence_threshold * 100) || 60;
        document.getElementById('confidence-range').value = confidence;
        document.getElementById('confidence-val').textContent = `${Math.round(confidence)}%`;

        // Alert Delay
        const alertDelay = data.alert_delay_hours || 3;
        document.getElementById('alert-range').value = alertDelay;
        document.getElementById('alert-val').textContent = `${alertDelay} ${alertDelay > 1 ? 'heures' : 'heure'}`;
    }

    async saveAiSettings() {
        const stability = parseInt(document.getElementById('stability-range').value);
        const confidence = parseFloat(document.getElementById('confidence-range').value) / 100;
        const alertDelay = parseInt(document.getElementById('alert-range').value);

        const payload = {
            stability_duration_minutes: stability,
            confidence_threshold: confidence,
            alert_delay_hours: alertDelay
        };

        try {
            const response = await fetch('/api/config/detection/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (result.success) {
                this.showNotification('Succès', 'Paramètres IA mis à jour avec succès.');
            } else {
                this.showNotification('Erreur', result.message, 'error');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showNotification('Erreur', 'Échec de la sauvegarde.', 'error');
        }
    }

    addCountry() {
        const input = document.getElementById('new-country');
        const country = input.value.trim();

        if (country && !this.countries.includes(country)) {
            this.countries.push(country);
            input.value = '';
            this.renderCountries();
        }
    }

    removeCountry(country) {
        this.countries = this.countries.filter(c => c !== country);
        this.renderCountries();
    }

    renderCountries() {
        const list = document.getElementById('countries-list');
        list.innerHTML = '';

        this.countries.sort().forEach(country => {
            const pill = document.createElement('div');
            pill.className = 'flex items-center gap-2 px-4 py-2 bg-slate-800 border border-slate-700 rounded-full text-xs font-medium text-slate-300 hover:border-yellow-500/50 transition-colors group';
            pill.innerHTML = `
                <span>${country}</span>
                <button class="text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity" onclick="configManager.removeCountry('${country}')">
                    <i class="fas fa-times"></i>
                </button>
            `;
            list.appendChild(pill);
        });
    }

    async saveCountries() {
        const payload = {
            asecna_countries: JSON.stringify(this.countries)
        };

        try {
            const response = await fetch('/api/config/detection/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                this.showNotification('Succès', 'Liste des pays synchronisée.');
            }
        } catch (error) {
            this.showNotification('Erreur', 'Échec de la synchronisation.', 'error');
        }
    }

    showNotification(title, message, type = 'success') {
        const notif = document.getElementById('notification');
        const titleEl = document.getElementById('notif-title');
        const messageEl = document.getElementById('notif-message');

        titleEl.textContent = title;
        messageEl.textContent = message;

        notif.style.borderLeftColor = type === 'success' ? '#22c55e' : '#ef4444';

        notif.style.transform = 'translateY(0)';
        setTimeout(() => {
            notif.style.transform = 'translateY(200%)';
        }, 4000);
    }
}

// Global instance for onclick handlers
let configManager;
document.addEventListener('DOMContentLoaded', () => {
    configManager = new ConfigManager();
});
