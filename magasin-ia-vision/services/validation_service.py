"""
Validation Service for ASECNA Stock Management
Handles the persistence of validation requests and admin approvals in the database.
"""

from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from data.database import SessionLocal
from data.models import ValidationRequest, TemporalTracking, DetectionEvent, User, TrackingStatus
import logging

logger = logging.getLogger(__name__)

class ValidationService:
    """
    Handles persistence logic for stock validation requests.
    """
    
    def __init__(self, db: Optional[Session] = None):
        self._db = db
        self._db_owned = False
        
    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
            self._db_owned = True
        return self._db
        
    def __del__(self):
        if self._db_owned and self._db:
            self._db.close()

    def create_request(self, data: Dict) -> ValidationRequest:
        """
        Create a new validation request in the database.
        """
        try:
            request = ValidationRequest(
                validation_code=data['id'],
                object_type=data['object_type'],
                camera_ids=data['camera_ids'],
                quantity_delta=data['quantity_delta'],
                current_quantity=data['current_quantity'],
                proposed_quantity=data['proposed_quantity'],
                avg_confidence=data['avg_confidence'],
                detection_duration_minutes=data['detection_duration_minutes'],
                status="pending",
                created_at=datetime.now()
            )
            self.db.add(request)
            self.db.commit()
            self.db.refresh(request)
            logger.info(f"Persistent validation request created: {request.validation_code}")
            return request
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create persistent validation request: {e}")
            raise

    def get_pending_requests(self) -> List[ValidationRequest]:
        """
        Retrieve all pending validation requests.
        """
        return self.db.query(ValidationRequest).filter(ValidationRequest.status == "pending").all()

    def approve_request(self, validation_code: str, admin_id: int) -> bool:
        """
        Approve a validation request and update stock.
        """
        try:
            request = self.db.query(ValidationRequest).filter(
                ValidationRequest.validation_code == validation_code,
                ValidationRequest.status == "pending"
            ).first()
            
            if not request:
                logger.warning(f"Pending validation request not found: {validation_code}")
                return False
                
            request.status = "approved"
            request.validated_at = datetime.now()
            request.validated_by = admin_id
            
            # Update equipment_items quantity
            from data.models import EquipmentItem, EquipmentType, Zone
            
            # Find the equipment type
            eq_type = self.db.query(EquipmentType).filter(EquipmentType.name == request.object_type).first()
            if not eq_type:
                logger.error(f"Equipment type {request.object_type} not found for validation")
                return False
                
            # For each camera involved, find the zone and update/create items
            # Simplified logic: Update the first zone found for these cameras
            camera_id = request.camera_ids[0] if isinstance(request.camera_ids, list) and request.camera_ids else str(request.camera_ids)
            zone = self.db.query(Zone).filter(Zone.camera_id == camera_id).first()
            
            if zone:
                # Update declared quantity for items of this type in this zone
                # Note: In this simplified model, we might have multiple items or one aggregate
                item = self.db.query(EquipmentItem).filter(
                    EquipmentItem.type_id == eq_type.id,
                    EquipmentItem.current_zone_id == zone.id
                ).first()
                
                if item:
                    item.declared_quantity = request.proposed_quantity
                    item.detected_quantity = request.proposed_quantity
                    item.last_count_timestamp = datetime.now()
                    item.counting_confidence = request.avg_confidence
                else:
                    # Create new item record for this type in this zone
                    new_item = EquipmentItem(
                        unique_ref=f"{eq_type.name.upper()}-{zone.name.upper()}-{datetime.now().strftime('%H%M%S')}",
                        type_id=eq_type.id,
                        current_zone_id=zone.id,
                        declared_quantity=request.proposed_quantity,
                        detected_quantity=request.proposed_quantity,
                        last_count_timestamp=datetime.now(),
                        counting_confidence=request.avg_confidence
                    )
                    self.db.add(new_item)
            
            self.db.commit()
            logger.info(f"Validation request {validation_code} approved and stock updated in DB")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to approve validation request in DB: {e}")
            return False

    def reject_request(self, validation_code: str, admin_id: int, reason: str) -> bool:
        """
        Reject a validation request.
        """
        try:
            request = self.db.query(ValidationRequest).filter(
                ValidationRequest.validation_code == validation_code,
                ValidationRequest.status == "pending"
            ).first()
            
            if not request:
                logger.warning(f"Pending validation request not found: {validation_code}")
                return False
                
            request.status = "rejected"
            request.validated_at = datetime.now()
            request.validated_by = admin_id
            request.rejection_reason = reason
            
            self.db.commit()
            logger.info(f"Validation request {validation_code} rejected in DB")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to reject validation request in DB: {e}")
            return False

    def sync_temporal_tracking(self, tracking_data: Dict) -> TemporalTracking:
        """
        Synchronize in-memory tracking with database.
        """
        try:
            # Simple sync for now: check if exists or create
            tracking = self.db.query(TemporalTracking).filter(
                TemporalTracking.object_type == tracking_data['object_type'],
                TemporalTracking.camera_id == tracking_data['camera_id'],
                TemporalTracking.status == TrackingStatus.TRACKING
            ).first()
            
            if not tracking:
                tracking = TemporalTracking(
                    object_type=tracking_data['object_type'],
                    camera_id=tracking_data['camera_id'],
                    first_seen=tracking_data['first_seen'],
                    last_seen=tracking_data['last_seen'],
                    status=TrackingStatus.TRACKING,
                    stability_threshold_minutes=tracking_data['stability_threshold_minutes']
                )
                self.db.add(tracking)
            else:
                tracking.last_seen = tracking_data['last_seen']
                tracking.detection_count = tracking_data['detection_count']
                tracking.avg_confidence = tracking_data['avg_confidence']
                
            self.db.commit()
            self.db.refresh(tracking)
            return tracking
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to sync temporal tracking: {e}")
            raise

# Singleton instance
_validation_service = None

def get_validation_service(db: Optional[Session] = None) -> ValidationService:
    """Get or create the global validation service instance"""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService(db)
    return _validation_service
