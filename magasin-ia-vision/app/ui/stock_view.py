from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QPushButton, QLabel, QHeaderView, QLineEdit, QComboBox, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt
from data.database import get_db
from data.repositories.equipment_repo import EquipmentRepository
from data.models import EquipmentStatus

class StockView(QWidget):
    def __init__(self):
        super().__init__()
        # Database session management manually or via dependency injection in a real app
        # Here we open a session for the widget's lifecycle for simplicity
        self.db_gen = get_db()
        self.db = next(self.db_gen)
        self.repo = EquipmentRepository(self.db)
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Gestion du Stock")
        header.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Form for adding new items (Simplified)
        form_layout = QHBoxLayout()
        self.ref_input = QLineEdit()
        self.ref_input.setPlaceholderText("Référence Unique (ex: PERCEUSE-001)")
        
        # We need types loaded here normally, hardcoding for UI demo or need a fetch
        self.type_combo = QComboBox()
        self.load_types()
        
        add_btn = QPushButton("Ajouter Équipement")
        add_btn.clicked.connect(self.add_item)
        
        form_layout.addWidget(QLabel("Réf:"))
        form_layout.addWidget(self.ref_input)
        form_layout.addWidget(QLabel("Type:"))
        form_layout.addWidget(self.type_combo)
        form_layout.addWidget(add_btn)
        
        layout.addLayout(form_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5) # + Actions
        self.table.setHorizontalHeaderLabels(["ID", "Référence", "Type", "Statut", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Refresh Button
        refresh_btn = QPushButton("Actualiser")
        refresh_btn.clicked.connect(self.load_data)
        layout.addWidget(refresh_btn)

        self.setLayout(layout)

    def load_types(self):
        types = self.repo.get_all_types()
        self.type_combo.clear()
        if not types:
            # Create a default type if none exist for demo
             try:
                self.repo.create_type("Générique", "Type par défaut")
                types = self.repo.get_all_types()
             except:
                 pass
        
        for t in types:
            self.type_combo.addItem(t.name, t.id)

    def load_data(self):
        self.table.setRowCount(0)
        items = self.repo.get_all_items()
        
        for row, item in enumerate(items):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(item.id)))
            self.table.setItem(row, 1, QTableWidgetItem(item.unique_ref))
            self.table.setItem(row, 2, QTableWidgetItem(item.equipment_type.name if item.equipment_type else "N/A"))
            self.table.setItem(row, 3, QTableWidgetItem(item.status.value))
            
            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(2, 2, 2, 2)
            
            if item.status == EquipmentStatus.IN_STOCK:
                btn = QPushButton("Sortir")
                btn.clicked.connect(lambda checked, i=item.id: self.change_status(i, EquipmentStatus.IN_USE))
                btn.setStyleSheet("background-color: #f39c12; color: white;")
            else:
                btn = QPushButton("Retour")
                btn.clicked.connect(lambda checked, i=item.id: self.change_status(i, EquipmentStatus.IN_STOCK))
                btn.setStyleSheet("background-color: #2ecc71; color: white;")
                
            action_layout.addWidget(btn)
            action_widget.setLayout(action_layout)
            self.table.setCellWidget(row, 4, action_widget)

    def change_status(self, item_id, new_status):
        self.repo.update_item_status(item_id, new_status)
        self.load_data()


    def add_item(self):
        ref = self.ref_input.text().strip()
        type_id = self.type_combo.currentData()
        
        if not ref:
            QMessageBox.warning(self, "Erreur", "La référence est obligatoire.")
            return
            
        try:
            self.repo.create_item(ref, type_id)
            self.ref_input.clear()
            self.load_data()
            QMessageBox.information(self, "Succès", "Équipement ajouté.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'ajout: {str(e)}")

    def closeEvent(self, event):
        self.db.close()
        event.accept()
