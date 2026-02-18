from typing import List, Optional
from sqlalchemy.orm import Session
from data.models import Zone, EquipmentType
from services.logger_service import logger

class ZoneRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> List[Zone]:
        """Fetch all zones with their equipment types"""
        return self.session.query(Zone).all()

    def get_by_id(self, zone_id: int) -> Optional[Zone]:
        return self.session.query(Zone).filter(Zone.id == zone_id).first()

    def get_by_name(self, name: str) -> Optional[Zone]:
        return self.session.query(Zone).filter(Zone.name == name).first()

    def add_zone(self, name: str, camera_id: str, equipment_type_id: Optional[int] = None, polygon_coords: Optional[str] = None) -> Zone:
        """Create and persist a new zone"""
        zone = Zone(
            name=name,
            camera_id=camera_id,
            equipment_type_id=equipment_type_id,
            polygon_coordinates=polygon_coords
        )
        self.session.add(zone)
        self.session.commit()
        self.session.refresh(zone)
        logger.info(f"Zone {name} created in database with camera {camera_id}")
        return zone

    def delete_zone(self, zone_id: int) -> bool:
        """Remove a zone from database"""
        zone = self.get_by_id(zone_id)
        if zone:
            self.session.delete(zone)
            self.session.commit()
            return True
        return False

    def update_roi(self, zone_id: int, polygon_coords: str) -> bool:
        """Update ROI coordinates for a zone"""
        zone = self.get_by_id(zone_id)
        if zone:
            zone.polygon_coordinates = polygon_coords
            self.session.commit()
            return True
        return False

def get_zone_repo(session: Session) -> ZoneRepository:
    return ZoneRepository(session)
