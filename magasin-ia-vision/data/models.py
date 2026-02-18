from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, Float, JSON, LargeBinary
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from data.database import Base

class UserRole(enum.Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    SUPERVISOR = "supervisor"

class EquipmentStatus(enum.Enum):
    IN_STOCK = "in_stock"
    IN_USE = "in_use"
    MISSING = "missing"
    MAINTENANCE = "maintenance"

class WithdrawalStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.OPERATOR)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EquipmentType(Base):
    __tablename__ = "equipment_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    alert_threshold = Column(Integer, default=5)  # Alert if stock drops below this
    image_path = Column(String, nullable=True)  # Reference image for manual check

    items = relationship("EquipmentItem", back_populates="equipment_type")

class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    camera_id = Column(String, nullable=True)  # ID or URL of the camera covering this zone
    polygon_coordinates = Column(Text, nullable=True)  # JSON or string representation of ROI
    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id"), nullable=True)  # Type of equipment in this zone

    equipment_type = relationship("EquipmentType")

class EquipmentItem(Base):
    __tablename__ = "equipment_items"

    id = Column(Integer, primary_key=True, index=True)
    unique_ref = Column(String, unique=True, index=True, nullable=False)  # Serial number or QR code
    type_id = Column(Integer, ForeignKey("equipment_types.id"))
    status = Column(Enum(EquipmentStatus), default=EquipmentStatus.IN_STOCK)
    current_zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # NEW: Comptage fields
    declared_quantity = Column(Integer, default=1)  # Manually declared quantity
    detected_quantity = Column(Integer, nullable=True)  # AI-detected quantity
    last_count_timestamp = Column(DateTime(timezone=True), nullable=True)
    counting_confidence = Column(Float, nullable=True)  # AI confidence (0-1)

    equipment_type = relationship("EquipmentType", back_populates="items")
    current_zone = relationship("Zone")

class MovementHistory(Base):
    __tablename__ = "movement_history"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("equipment_items.id"))
    from_zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    to_zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    video_clip_path = Column(String, nullable=True)  # Path to clip evidence
    
    item = relationship("EquipmentItem")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # MISSING_ITEM, UNAUTHORIZED_MOVEMENT
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    is_acknowledged = Column(Boolean, default=False)

# NEW TABLES FOR ASECNA SYSTEM

class AutoCount(Base):
    """Automatic object counting results"""
    __tablename__ = "auto_counts"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id"), nullable=False)
    count = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)  # Average detection confidence
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    detection_frame = Column(LargeBinary, nullable=True)  # Screenshot of detection (optional)
    
    zone = relationship("Zone")
    equipment_type = relationship("EquipmentType")

class WithdrawalRequest(Base):
    """Material withdrawal requests from countries"""
    __tablename__ = "withdrawal_requests"

    id = Column(Integer, primary_key=True, index=True)
    requester_name = Column(String(100), nullable=False)
    requester_country = Column(String(50), nullable=False)  # One of 19 African countries
    requester_email = Column(String(100), nullable=True)
    
    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id"), nullable=False)
    quantity_requested = Column(Integer, nullable=False)
    
    status = Column(Enum(WithdrawalStatus), default=WithdrawalStatus.PENDING)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    
    approved_by = Column(String(100), nullable=True)  # Admin who approved
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_reason = Column(Text, nullable=True)
    
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    
    equipment_type = relationship("EquipmentType")

# NEW TABLES FOR TEMPORAL DETECTION SYSTEM

class TrackingStatus(enum.Enum):
    """Status of temporal tracking"""
    TRACKING = "tracking"
    STABLE = "stable"
    PENDING_VALIDATION = "pending_validation"
    VALIDATED = "validated"
    REJECTED = "rejected"

class TemporalTracking(Base):
    """Temporal tracking of objects over time"""
    __tablename__ = "temporal_trackings"

    id = Column(Integer, primary_key=True, index=True)
    object_type = Column(String, nullable=False, index=True)
    camera_id = Column(String, nullable=False, index=True)
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    detection_count = Column(Integer, default=0)
    avg_confidence = Column(Float, default=0.0)
    status = Column(Enum(TrackingStatus), default=TrackingStatus.TRACKING, index=True)
    stability_threshold_minutes = Column(Integer, default=60)
    detected_quantity = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    detection_events = relationship("DetectionEvent", back_populates="temporal_tracking")

class DetectionEvent(Base):
    """Individual detection events from cameras"""
    __tablename__ = "detection_events"

    id = Column(Integer, primary_key=True, index=True)
    object_type = Column(String, nullable=False, index=True)
    camera_id = Column(String, nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    bbox_coords = Column(JSON, nullable=True)
    tracking_id = Column(String, nullable=True)
    temporal_tracking_id = Column(Integer, ForeignKey("temporal_trackings.id"), nullable=True)

    temporal_tracking = relationship("TemporalTracking", back_populates="detection_events")

class ValidationRequest(Base):
    """Admin validation requests for stock changes"""
    __tablename__ = "validation_requests"

    id = Column(Integer, primary_key=True, index=True)
    validation_code = Column(String, unique=True, nullable=False, index=True)
    object_type = Column(String, nullable=False, index=True)
    camera_ids = Column(JSON, nullable=False)
    quantity_delta = Column(Integer, nullable=False)
    current_quantity = Column(Integer, nullable=False)
    proposed_quantity = Column(Integer, nullable=False)
    avg_confidence = Column(Float, nullable=False)
    detection_duration_minutes = Column(Float, nullable=False)
    status = Column(String, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    alert_sent_at = Column(DateTime(timezone=True), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    validated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    validator = relationship("User")

class AdminConfig(Base):
    """Admin configuration for temporal detection"""
    __tablename__ = "admin_config"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String, unique=True, nullable=False, index=True)
    config_value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    updater = relationship("User")
