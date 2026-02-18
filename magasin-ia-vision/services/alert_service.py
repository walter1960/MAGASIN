from sqlalchemy.orm import Session
from data.models import Alert
from data.database import get_db
from services.logger_service import logger
import datetime

class AlertService:
    def __init__(self, db: Session = None):
        if db:
            self.db = db
        else:
            self.db_gen = get_db()
            self.db = next(self.db_gen)

    def create_alert(self, alert_type: str, message: str):
        """
        Create and persist a new alert.
        """
        try:
            alert = Alert(
                type=alert_type,
                message=message,
                timestamp=datetime.datetime.now(),
                is_acknowledged=False
            )
            self.db.add(alert)
            self.db.commit()
            self.db.refresh(alert)
            logger.warning(f"New Alert: {alert_type} - {message}")
            return alert
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create alert: {e}")
            return None

    def get_active_alerts(self):
        """
        Get all unacknowledged alerts.
        """
        return self.db.query(Alert).filter(Alert.is_acknowledged == False).order_by(Alert.timestamp.desc()).all()

    def acknowledge_alert(self, alert_id: int):
        """
        Mark an alert as acknowledged.
        """
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.is_acknowledged = True
            self.db.commit()
            return True
        return False
        
    def close(self):
        self.db.close()
