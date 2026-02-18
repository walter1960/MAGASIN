from sqlalchemy import func
from sqlalchemy.orm import Session
from data.models import MovementHistory, EquipmentItem, EquipmentType, Alert
from data.database import get_db
import datetime
import csv
import os

class StatisticsService:
    def __init__(self, db: Session = None):
        if db:
            self.db = db
        else:
            self.db_gen = get_db()
            self.db = next(self.db_gen)

    def get_todays_movements_count(self):
        today = datetime.date.today()
        return self.db.query(MovementHistory).filter(func.date(MovementHistory.timestamp) == today).count()

    def get_top_used_items(self, limit=5):
        """
        Returns items with most movements.
        """
        return self.db.query(
            EquipmentItem.unique_ref, 
            func.count(MovementHistory.id).label('count')
        ).join(MovementHistory).group_by(EquipmentItem.id).order_by(func.count(MovementHistory.id).desc()).limit(limit).all()

    def export_movements_csv(self, filepath):
        """
        Export full movement history to CSV.
        """
        movements = self.db.query(MovementHistory).order_by(MovementHistory.timestamp.desc()).all()
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['ID', 'Item Ref', 'From Zone', 'To Zone', 'Timestamp']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for mov in movements:
                    writer.writerow({
                        'ID': mov.id,
                        'Item Ref': mov.item.unique_ref if mov.item else 'Unknown',
                        'From Zone': mov.from_zone_id,
                        'To Zone': mov.to_zone_id,
                        'Timestamp': mov.timestamp.isoformat()
                    })
            return True
        except Exception as e:
            return False

    def get_inventory_stats(self):
        """
        Returns real statistics for the inventory dashboard.
        """
        total = self.db.query(EquipmentItem).count()
        active = self.db.query(EquipmentItem).filter(EquipmentItem.status != 'missing').count()
        critical = self.db.query(Alert).filter(Alert.is_acknowledged == False).count()
        
        # Low stock based on declared vs detected or alert thresholds
        # For now, let's use EquipmentType alert_threshold
        low_stock = 0
        from data.models import EquipmentType
        types = self.db.query(EquipmentType).all()
        for t in types:
            count = self.db.query(EquipmentItem).filter(EquipmentItem.type_id == t.id).count()
            if count < t.alert_threshold:
                low_stock += 1

        return {
            "total_equipment": total,
            "active_equipment": active,
            "critical_alerts": critical,
            "low_stock_warnings": low_stock
        }

    def close(self):
        self.db.close()
