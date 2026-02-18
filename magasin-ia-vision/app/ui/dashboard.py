from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QListWidget, QPushButton, QMessageBox
from PyQt6.QtCore import Qt, QTimer
import datetime
import os
from services.statistics_service import StatisticsService

class KPICard(QFrame):
    def __init__(self, title, value, color="#3498db"):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"background-color: {color}; color: white; border-radius: 8px;")
        
        layout = QVBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        
        layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

class DashboardView(QWidget):
    def __init__(self):
        super().__init__()
        self.stats_service = StatisticsService()
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("Tableau de Bord")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(header)
        
        export_btn = QPushButton("Exporter Rapport CSV")
        export_btn.clicked.connect(self.export_report)
        header_layout.addWidget(export_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        layout.addLayout(header_layout)
        layout.addSpacing(20)
        
        # KPI Row
        kpi_layout = QHBoxLayout()
        self.stock_kpi = KPICard("Total Équipements", "124", "#2ecc71")
        self.use_kpi = KPICard("En Utilisation", "12", "#f39c12")
        self.missing_kpi = KPICard("Manquants", "0", "#e74c3c")
        self.alert_kpi = KPICard("Alertes Actives", "0", "#e67e22")
        
        kpi_layout.addWidget(self.stock_kpi)
        kpi_layout.addWidget(self.use_kpi)
        kpi_layout.addWidget(self.missing_kpi)
        kpi_layout.addWidget(self.alert_kpi)
        
        layout.addLayout(kpi_layout)
        
        # Logs / Charts
        logs_label = QLabel("Dernières Alertes")
        logs_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(logs_label)

        self.alert_list = QListWidget()
        layout.addWidget(self.alert_list)
        
        layout.addStretch()
        self.setLayout(layout)

    def add_alert(self, alert_data):
        """
        Add an alert to the list and update KPI.
        """
        # Deduplicate: Don't add if the last alert is identical and recent (< 5s)
        # For simplicity, just add
        item_text = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {alert_data['type']}: {alert_data['message']}"
        self.alert_list.insertItem(0, item_text)
        
        self.refresh_stats()

    def refresh_stats(self):
        # Update Alert KPI
        # In real app, query DB count of unacknowledged alerts
        current_alerts = self.alert_list.count()
        self.alert_kpi.value_label.setText(str(current_alerts))
        
        # Update Movement KPI (Using Stats Service)
        moves = self.stats_service.get_todays_movements_count()
        self.use_kpi.value_label.setText(str(moves)) # Reusing 'En Utilisation' card for 'Mouvements Jour' for demo, or create new card
        self.use_kpi.title_label.setText("Mouvements Jour")
        
    def export_report(self):
        filename = f"rapport_mouvements_{datetime.date.today()}.csv"
        path = os.path.join(os.getcwd(), "exports", filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        if self.stats_service.export_movements_csv(path):
            QMessageBox.information(self, "Export Réussi", f"Rapport sauvegardé:\n{path}")
        else:
            QMessageBox.critical(self, "Erreur Export", "Impossible de créer le fichier.")
