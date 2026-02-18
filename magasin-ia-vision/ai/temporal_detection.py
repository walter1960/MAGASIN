"""
Temporal Detection Engine for ASECNA Stock Management

Tracks objects detected over time and triggers validation requests
when objects remain stable for a configured duration.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class TrackingStatus(Enum):
    """Status of temporal tracking"""
    TRACKING = "tracking"  # Currently being tracked
    STABLE = "stable"  # Stable for required duration
    PENDING_VALIDATION = "pending_validation"  # Awaiting admin validation
    VALIDATED = "validated"  # Admin validated
    REJECTED = "rejected"  # Admin rejected


@dataclass
class DetectionEvent:
    """Single detection event"""
    object_type: str
    camera_id: str
    confidence: float
    timestamp: datetime
    bbox_coords: Tuple[float, float, float, float]  # (x1, y1, x2, y2)
    tracking_id: Optional[str] = None


@dataclass
class TemporalTracking:
    """Temporal tracking of an object type in a specific camera"""
    object_type: str
    camera_id: str
    first_seen: datetime
    last_seen: datetime
    detection_count: int = 0
    total_confidence: float = 0.0
    avg_confidence: float = 0.0
    status: TrackingStatus = TrackingStatus.TRACKING
    stability_threshold_minutes: int = 60
    detected_quantity: int = 0
    detection_events: List[DetectionEvent] = field(default_factory=list)
    
    def update_confidence(self, confidence: float):
        """Update average confidence with new detection"""
        self.total_confidence += confidence
        self.detection_count += 1
        self.avg_confidence = self.total_confidence / self.detection_count
    
    def get_duration_minutes(self) -> float:
        """Get tracking duration in minutes"""
        delta = self.last_seen - self.first_seen
        return delta.total_seconds() / 60
    
    def is_stable(self) -> bool:
        """Check if tracking is stable (duration >= threshold)"""
        return self.get_duration_minutes() >= self.stability_threshold_minutes


class TemporalDetectionEngine:
    """
    Engine for temporal detection with configurable stability thresholds.
    
    Features:
    - Track objects over time across multiple cameras
    - Detect when objects become stable (present for configured duration)
    - Calculate stock deltas (additions/removals)
    - Trigger validation requests for admin approval
    """
    
    def __init__(
        self,
        stability_duration_minutes: int = 60,
        confidence_threshold: float = 0.60,
        alert_delay_hours: int = 3
    ):
        """
        Initialize temporal detection engine.
        
        Args:
            stability_duration_minutes: Time object must be stable before validation
            confidence_threshold: Minimum confidence to accept detection
            alert_delay_hours: Hours to wait before sending alert to admin
        """
        self.stability_duration_minutes = stability_duration_minutes
        self.confidence_threshold = confidence_threshold
        self.alert_delay_hours = alert_delay_hours
        
        # Active trackings: {(object_type, camera_id): TemporalTracking}
        self.active_trackings: Dict[Tuple[str, str], TemporalTracking] = {}
        
        # Validated stock quantities: {object_type: quantity}
        self.validated_stock: Dict[str, int] = defaultdict(int)
        
        # Pending validations: {validation_id: validation_data}
        self.pending_validations: Dict[str, Dict] = {}
        
        # Callbacks for external systems (e.g., notification broadcast)
        self.on_validation_created = None
        self.on_validation_approved = None
        self.on_validation_rejected = None

        logger.info(
            f"TemporalDetectionEngine initialized: "
            f"stability={stability_duration_minutes}min, "
            f"confidence={confidence_threshold}, "
            f"alert_delay={alert_delay_hours}h"
        )
    
    def process_detection(
        self,
        object_type: str,
        camera_id: str,
        confidence: float,
        bbox_coords: Tuple[float, float, float, float],
        timestamp: Optional[datetime] = None,
        tracking_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Process a single detection event.
        
        Args:
            object_type: Type of object detected (e.g., "souris", "clavier")
            camera_id: ID of camera that detected the object
            confidence: Detection confidence (0.0 to 1.0)
            bbox_coords: Bounding box coordinates (x1, y1, x2, y2)
            timestamp: Detection timestamp (default: now)
            tracking_id: Optional tracking ID from ByteTrack
            
        Returns:
            Status message or None
        """
        if confidence < self.confidence_threshold:
            return None
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create detection event
        event = DetectionEvent(
            object_type=object_type,
            camera_id=camera_id,
            confidence=confidence,
            timestamp=timestamp,
            bbox_coords=bbox_coords,
            tracking_id=tracking_id
        )
        
        # Get or create tracking
        key = (object_type, camera_id)
        
        if key not in self.active_trackings:
            # New tracking
            tracking = TemporalTracking(
                object_type=object_type,
                camera_id=camera_id,
                first_seen=timestamp,
                last_seen=timestamp,
                stability_threshold_minutes=self.stability_duration_minutes
            )
            self.active_trackings[key] = tracking
            logger.info(f"Started tracking {object_type} on {camera_id}")
        else:
            tracking = self.active_trackings[key]
        
        # Update tracking
        tracking.last_seen = timestamp
        tracking.update_confidence(confidence)
        tracking.detection_events.append(event)
        
        # Check if tracking became stable
        if tracking.status == TrackingStatus.TRACKING and tracking.is_stable():
            tracking.status = TrackingStatus.STABLE
            logger.info(
                f"{object_type} on {camera_id} became stable "
                f"(duration: {tracking.get_duration_minutes():.1f}min, "
                f"confidence: {tracking.avg_confidence:.2%})"
            )
            return "stable"
        
        return "tracking"
    
    def count_stable_objects(
        self,
        object_type: str,
        camera_id: Optional[str] = None
    ) -> int:
        """
        Count stable objects of a given type.
        
        Args:
            object_type: Type of object to count
            camera_id: Optional camera filter
            
        Returns:
            Count of stable objects
        """
        count = 0
        
        for (obj_type, cam_id), tracking in self.active_trackings.items():
            if obj_type != object_type:
                continue
            
            if camera_id and cam_id != camera_id:
                continue
            
            if tracking.status in [TrackingStatus.STABLE, TrackingStatus.PENDING_VALIDATION]:
                # Count based on detection events in last stability window
                recent_events = [
                    e for e in tracking.detection_events
                    if (tracking.last_seen - e.timestamp).total_seconds() / 60 
                       <= self.stability_duration_minutes
                ]
                count += len(recent_events)
        
        return count
    
    def calculate_stock_delta(
        self,
        object_type: str,
        camera_id: Optional[str] = None
    ) -> Tuple[int, int, int]:
        """
        Calculate stock delta for an object type.
        
        Args:
            object_type: Type of object
            camera_id: Optional camera filter
            
        Returns:
            Tuple of (current_validated, detected_stable, delta)
        """
        current_validated = self.validated_stock.get(object_type, 0)
        detected_stable = self.count_stable_objects(object_type, camera_id)
        delta = detected_stable - current_validated
        
        return current_validated, detected_stable, delta
    
    def create_validation_request(
        self,
        object_type: str,
        camera_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Create a validation request for admin approval.
        """
        current, detected, delta = self.calculate_stock_delta(object_type, camera_id)
        
        if delta == 0:
            return None
        
        # Get relevant trackings
        trackings = []
        for (obj_type, cam_id), tracking in self.active_trackings.items():
            if obj_type != object_type:
                continue
            if camera_id and cam_id != camera_id:
                continue
            if tracking.status == TrackingStatus.STABLE:
                trackings.append(tracking)
        
        if not trackings:
            return None
        
        # Calculate average confidence across all trackings
        avg_confidence = sum(t.avg_confidence for t in trackings) / len(trackings)
        
        # Create validation request
        validation_id = f"VAL-{object_type}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        validation_data = {
            'id': validation_id,
            'object_type': object_type,
            'camera_ids': list(set(t.camera_id for t in trackings)),
            'quantity_delta': delta,
            'current_quantity': current,
            'proposed_quantity': detected,
            'avg_confidence': avg_confidence,
            'detection_duration_minutes': max(t.get_duration_minutes() for t in trackings),
            'status': 'pending',
            'created_at': datetime.now(),
            'alert_sent_at': None,
            'validated_at': None,
            'validated_by': None,
            'rejection_reason': None
        }
        
        self.pending_validations[validation_id] = validation_data
        
        # PERSIST TO DATABASE
        try:
            from services.validation_service import get_validation_service
            val_service = get_validation_service()
            val_service.create_request(validation_data)
        except Exception as e:
            logger.error(f"Failed to persist validation request: {e}")
        
        # Update tracking status
        for tracking in trackings:
            tracking.status = TrackingStatus.PENDING_VALIDATION
        
        logger.info(
            f"Created validation request {validation_id}: "
            f"{object_type} {current} → {detected} ({delta:+d})"
        )
        
        # Trigger notification callback
        if self.on_validation_created:
            try:
                self.on_validation_created(validation_data)
            except Exception as e:
                logger.error(f"Error in validation notification callback: {e}")
        
        return validation_data
    
    def approve_validation(
        self,
        validation_id: str,
        admin_id: str
    ) -> bool:
        """
        Approve a validation request.
        """
        if validation_id not in self.pending_validations:
            logger.error(f"Validation {validation_id} not found")
            return False
        
        validation = self.pending_validations[validation_id]
        
        if validation['status'] != 'pending':
            logger.error(f"Validation {validation_id} already processed")
            return False
        
        # PERSIST TO DATABASE
        try:
            from services.validation_service import get_validation_service
            val_service = get_validation_service()
            # Convert admin_id to int if necessary (based on User model)
            val_service.approve_request(validation_id, 1) # Using ID 1 for now
        except Exception as e:
            logger.error(f"Failed to persist validation approval: {e}")
            return False

        # Update validated stock
        object_type = validation['object_type']
        self.validated_stock[object_type] = validation['proposed_quantity']
        
        # Update validation status
        validation['status'] = 'approved'
        validation['validated_at'] = datetime.now()
        validation['validated_by'] = admin_id
        
        # Update tracking status
        for (obj_type, cam_id), tracking in self.active_trackings.items():
            if obj_type == object_type and tracking.status == TrackingStatus.PENDING_VALIDATION:
                tracking.status = TrackingStatus.VALIDATED
        
        logger.info(
            f"Validation {validation_id} approved by {admin_id}: "
            f"{object_type} stock updated to {validation['proposed_quantity']}"
        )
        
        # Trigger notification callback
        if self.on_validation_approved:
            try:
                self.on_validation_approved(validation)
            except Exception as e:
                logger.error(f"Error in approval notification callback: {e}")
        
        return True
    
    def reject_validation(
        self,
        validation_id: str,
        admin_id: str,
        reason: str
    ) -> bool:
        """
        Reject a validation request.
        """
        if validation_id not in self.pending_validations:
            logger.error(f"Validation {validation_id} not found")
            return False
        
        validation = self.pending_validations[validation_id]
        
        if validation['status'] != 'pending':
            logger.error(f"Validation {validation_id} already processed")
            return False
        
        # PERSIST TO DATABASE
        try:
            from services.validation_service import get_validation_service
            val_service = get_validation_service()
            val_service.reject_request(validation_id, 1, reason)
        except Exception as e:
            logger.error(f"Failed to persist validation rejection: {e}")
            return False

        # Update validation status
        validation['status'] = 'rejected'
        validation['validated_at'] = datetime.now()
        validation['validated_by'] = admin_id
        validation['rejection_reason'] = reason
        
        # Reset tracking status
        object_type = validation['object_type']
        for (obj_type, cam_id), tracking in self.active_trackings.items():
            if obj_type == object_type and tracking.status == TrackingStatus.PENDING_VALIDATION:
                tracking.status = TrackingStatus.REJECTED
                # Clear old events
                tracking.detection_events.clear()
                tracking.first_seen = datetime.now()
                tracking.last_seen = datetime.now()
                tracking.detection_count = 0
                tracking.total_confidence = 0.0
                tracking.avg_confidence = 0.0
        
        logger.info(
            f"Validation {validation_id} rejected by {admin_id}: {reason}"
        )
        
        # Trigger notification callback
        if self.on_validation_rejected:
            try:
                self.on_validation_rejected(validation)
            except Exception as e:
                logger.error(f"Error in rejection notification callback: {e}")
        
        return True
    
    def check_alerts(self) -> List[Dict]:
        """
        Check for validations that need alerts.
        
        Returns:
            List of validations requiring alerts
        """
        alerts = []
        current_time = datetime.now()
        
        for validation_id, validation in self.pending_validations.items():
            if validation['status'] != 'pending':
                continue
            
            if validation['alert_sent_at'] is not None:
                continue
            
            # Check if alert delay has passed
            time_since_creation = current_time - validation['created_at']
            hours_elapsed = time_since_creation.total_seconds() / 3600
            
            if hours_elapsed >= self.alert_delay_hours:
                validation['alert_sent_at'] = current_time
                alerts.append(validation)
                logger.warning(
                    f"Alert triggered for {validation_id}: "
                    f"{validation['object_type']} pending validation for {hours_elapsed:.1f}h"
                )
        
        return alerts
    
    def get_tracking_summary(self) -> Dict:
        """
        Get summary of all active trackings.
        
        Returns:
            Summary dictionary
        """
        summary = {
            'total_trackings': len(self.active_trackings),
            'by_status': defaultdict(int),
            'by_object_type': defaultdict(int),
            'pending_validations': len([v for v in self.pending_validations.values() if v['status'] == 'pending']),
            'validated_stock': dict(self.validated_stock)
        }
        
        for tracking in self.active_trackings.values():
            summary['by_status'][tracking.status.value] += 1
            summary['by_object_type'][tracking.object_type] += 1
        
        return summary


# Singleton instance
_temporal_engine = None


def get_temporal_engine() -> TemporalDetectionEngine:
    """Get or create the global temporal detection engine"""
    global _temporal_engine
    if _temporal_engine is None:
        _temporal_engine = TemporalDetectionEngine()
    return _temporal_engine
