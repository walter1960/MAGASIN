from sqlalchemy.orm import Session, joinedload
from data.models import EquipmentItem, EquipmentType, EquipmentStatus, MovementHistory
from services.logger_service import logger
import datetime

class EquipmentRepository:
    """
    Data Access Layer for Equipment entities.
    """
    def __init__(self, db: Session):
        self.db = db

    def get_all_types(self):
        """Retrieve all equipment types."""
        return self.db.query(EquipmentType).all()

    def create_type(self, name, description, alert_threshold=5):
        """Create a new equipment type."""
        try:
            etype = EquipmentType(
                name=name, 
                description=description, 
                alert_threshold=alert_threshold
            )
            self.db.add(etype)
            self.db.commit()
            self.db.refresh(etype)
            logger.info(f"Created EquipmentType: {name}")
            return etype
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating equipment type: {e}")
            raise e

    def get_all_items(self):
        """Retrieve all specific equipment items with their types and zones."""
        return self.db.query(EquipmentItem).options(
            joinedload(EquipmentItem.equipment_type),
            joinedload(EquipmentItem.current_zone)
        ).all()

    def create_item(self, unique_ref, type_id, status=EquipmentStatus.IN_STOCK):
        """Create a new specific item instance."""
        try:
            item = EquipmentItem(
                unique_ref=unique_ref, 
                type_id=type_id, 
                status=status
            )
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            logger.info(f"Created EquipmentItem: {unique_ref}")
            return item
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating equipment item: {e}")
            raise e

    def update_item_status(self, item_id, status: EquipmentStatus, user_id=None, zone_id=None):
        """Update the status of an item and record history."""
        try:
            item = self.db.query(EquipmentItem).filter(EquipmentItem.id == item_id).first()
            if item:
                # Record History
                history = MovementHistory(
                    item_id=item.id,
                    from_zone_id=item.current_zone_id,
                    to_zone_id=zone_id, # Assuming zone change if provided, else None
                    timestamp=datetime.datetime.now(),
                    # user_id... (if we had auth context)
                )
                self.db.add(history)
                
                # Update Item
                item.status = status
                if zone_id:
                    item.current_zone_id = zone_id
                    
                self.db.commit()
                self.db.refresh(item)
                logger.info(f"Updated item {item.unique_ref} status to {status} with history.")
            return item
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating item status: {e}")
            raise e
