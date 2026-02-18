from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStatusBar, QTabWidget
from PyQt6.QtCore import Qt
from app.ui.camera_view import CameraWidget
from app.ui.dashboard import DashboardView
from app.ui.stock_view import StockView
from config.settings import settings
from services.alert_service import AlertService

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(settings.APP_NAME)
        self.resize(1280, 720)
        
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Central Widget Layout
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Tabs
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        
        # Tab 1: Surveillance (Camera + Controls)
        self.surveillance_tab = QWidget()
        self.surveillance_layout = QHBoxLayout(self.surveillance_tab)
        
        self.camera_view = CameraWidget(source=0)
        self.surveillance_layout.addWidget(self.camera_view, stretch=3)
        
        self.controls_panel = QVBoxLayout()
        self.start_btn = QPushButton("Démarrer Caméra")
        self.start_btn.clicked.connect(self.start_camera)
        self.controls_panel.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Arrêter Caméra")
        self.stop_btn.clicked.connect(self.stop_camera)
        self.controls_panel.addWidget(self.stop_btn)
        self.controls_panel.addStretch()
        
        self.surveillance_layout.addLayout(self.controls_panel, stretch=1)
        
        # Tab 2: Dashboard
        self.dashboard_view = DashboardView()
        
        # Tab 3: Gestion Stock
        self.stock_view = StockView()
        
        # Add Tabs
        self.tabs.addTab(self.dashboard_view, "Tableau de Bord")
        self.tabs.addTab(self.surveillance_tab, "Surveillance Temps Réel")
        self.tabs.addTab(self.stock_view, "Gestion Stock")
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Prêt")
        
        # Connect Signals
        self.camera_view.alert_signal.connect(self.handle_alert)

        # Services
        self.alert_service = AlertService()

    def handle_alert(self, alerts):
        """
        Process alerts received from the camera worker.
        """
        for alert_data in alerts:
            # Persist
            self.alert_service.create_alert(alert_data['type'], alert_data['message'])
            # Update UI
            self.dashboard_view.add_alert(alert_data)
            # Notify in status bar
            self.status_bar.showMessage(f"ALERTE: {alert_data['message']}", 5000)

    def start_camera(self):
        self.camera_view.start_camera()
        self.status_bar.showMessage("Caméra démarrée")

    def stop_camera(self):
        self.camera_view.stop_camera()
        self.status_bar.showMessage("Caméra arrêtée")

    def closeEvent(self, event):
        self.camera_view.stop_camera()
        event.accept()
