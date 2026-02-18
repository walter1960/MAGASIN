"""
Multi-Camera Manager for ASECNA Stock Management System

Manages multiple camera streams simultaneously with zone-based configuration.
Supports up to 50 cameras with individual ROI (Region of Interest) settings.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
import cv2
from workers.async_video_worker import AsyncVideoWorker

logger = logging.getLogger(__name__)


@dataclass
class CameraConfig:
    """Configuration for a single camera"""
    camera_id: str
    source: str  # RTSP URL or device index
    zone_id: str
    zone_name: str
    roi_coords: Optional[List[List[int]]] = None  # [[x1,y1], [x2,y2], ...]
    fps: int = 15
    enabled: bool = True


@dataclass
class Zone:
    """Storage zone definition"""
    zone_id: str
    name: str
    camera_id: str
    equipment_type: Optional[str] = None  # 'ram', 'computer', 'pen_box', etc.
    roi_coords: Optional[List[List[int]]] = None


class MultiCameraManager:
    """
    Manages multiple camera streams for warehouse surveillance.
    
    Features:
    - Add/remove cameras dynamically
    - Zone-based organization
    - Individual stream access
    - Centralized frame distribution
    """
    
    def __init__(self):
        self.cameras: Dict[str, AsyncVideoWorker] = {}
        self.zones: Dict[str, Zone] = {}
        self.camera_configs: Dict[str, CameraConfig] = {}
        self.running = False
        
        # Global AI state to sync new cameras
        self.current_model = "yolov8n"
        self.current_tracker = None
        self.current_segmenter = None
        
        logger.info("MultiCameraManager initialized")

    def load_from_db(self):
        """Load persisted zones/cameras from database"""
        try:
            from sqlalchemy.orm import Session
            from data.database import engine
            from data.repositories.zone_repo import get_zone_repo
            
            with Session(engine) as session:
                repo = get_zone_repo(session)
                zones = repo.get_all()
                
                for zone in zones:
                    if not zone.camera_id:
                        continue
                        
                    # Skip if source 0 (Webcam handled separately or protected)
                    if zone.camera_id == "0":
                        continue
                        
                    config = CameraConfig(
                        camera_id=f"CAM-{zone.id}",
                        source=zone.camera_id,
                        zone_id=f"ZONE-{zone.id}",
                        zone_name=zone.name,
                        roi_coords=json.loads(zone.polygon_coordinates) if zone.polygon_coordinates else None
                    )
                    self.add_camera(config)
            
            logger.success(f"Loaded {len(self.cameras)} camera(s) from database")
        except Exception as e:
            logger.error(f"Failed to load cameras from DB: {e}")
    
    def add_camera(self, config: CameraConfig) -> bool:
        """
        Add a new camera to the system.
        
        Args:
            config: Camera configuration
            
        Returns:
            True if camera added successfully, False otherwise
        """
        try:
            if config.camera_id in self.cameras:
                logger.warning(f"Camera {config.camera_id} already exists")
                return False
            
            # Create video worker for this camera with global settings
            worker = AsyncVideoWorker(
                source=config.source, 
                camera_id=config.camera_id,
                model_id=self.current_model,
                tracker_id=self.current_tracker,
                segmentation_id=self.current_segmenter
            )
            worker.start()
            
            self.cameras[config.camera_id] = worker
            self.camera_configs[config.camera_id] = config
            
            # Create or update zone
            zone = Zone(
                zone_id=config.zone_id,
                name=config.zone_name,
                camera_id=config.camera_id,
                roi_coords=config.roi_coords
            )
            self.zones[config.zone_id] = zone
            
            logger.info(f"Camera {config.camera_id} added for zone {config.zone_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add camera {config.camera_id}: {e}")
            return False
    
    def remove_camera(self, camera_id: str) -> bool:
        """
        Remove a camera from the system.
        
        Args:
            camera_id: ID of camera to remove
            
        Returns:
            True if removed successfully
        """
        try:
            if camera_id not in self.cameras:
                logger.warning(f"Camera {camera_id} not found")
                return False
            
            # Stop the worker
            worker = self.cameras[camera_id]
            worker.stop()
            
            # Remove from dictionaries
            del self.cameras[camera_id]
            del self.camera_configs[camera_id]
            
            # Remove zone if no other cameras use it
            config = self.camera_configs.get(camera_id)
            if config and config.zone_id in self.zones:
                # Check if other cameras use this zone
                other_cameras = [c for c in self.camera_configs.values() 
                               if c.zone_id == config.zone_id and c.camera_id != camera_id]
                if not other_cameras:
                    del self.zones[config.zone_id]
            
            logger.info(f"Camera {camera_id} removed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove camera {camera_id}: {e}")
            return False
    
    def get_camera(self, camera_id: str) -> Optional[AsyncVideoWorker]:
        """Get a specific camera worker"""
        return self.cameras.get(camera_id)
    
    def get_zone_camera(self, zone_id: str) -> Optional[AsyncVideoWorker]:
        """Get the camera associated with a zone"""
        zone = self.zones.get(zone_id)
        if zone:
            return self.cameras.get(zone.camera_id)
        return None
    
    def get_all_cameras(self) -> Dict[str, AsyncVideoWorker]:
        """Get all active cameras"""
        return self.cameras
    
    def get_all_zones(self) -> Dict[str, Zone]:
        """Get all configured zones"""
        return self.zones
    
    def get_camera_config(self, camera_id: str) -> Optional[CameraConfig]:
        """Get configuration for a specific camera"""
        return self.camera_configs.get(camera_id)
    
    def update_zone_roi(self, zone_id: str, roi_coords: List[List[int]]) -> bool:
        """
        Update ROI coordinates for a zone.
        
        Args:
            zone_id: Zone identifier
            roi_coords: New ROI polygon coordinates
            
        Returns:
            True if updated successfully
        """
        try:
            if zone_id not in self.zones:
                logger.warning(f"Zone {zone_id} not found")
                return False
            
            self.zones[zone_id].roi_coords = roi_coords
            
            # Update camera config as well
            camera_id = self.zones[zone_id].camera_id
            if camera_id in self.camera_configs:
                self.camera_configs[camera_id].roi_coords = roi_coords
            
            logger.info(f"ROI updated for zone {zone_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update ROI for zone {zone_id}: {e}")
            return False
    
    def get_active_camera_count(self) -> int:
        """Get number of active cameras"""
        return len([w for w in self.cameras.values() if w.running])
    
    def get_zone_count(self) -> int:
        """Get number of configured zones"""
        return len(self.zones)
    
    def stop_all(self):
        """Stop all camera workers"""
        logger.info("Stopping all cameras...")
        for camera_id, worker in self.cameras.items():
            try:
                worker.stop()
                logger.info(f"Stopped camera {camera_id}")
            except Exception as e:
                logger.error(f"Error stopping camera {camera_id}: {e}")
        
        self.cameras.clear()
        self.zones.clear()
        self.camera_configs.clear()
        logger.info("All cameras stopped")
    
    def get_status(self) -> Dict:
        """
        Get overall system status.
        
        Returns:
            Dictionary with status information
        """
        return {
            "total_cameras": len(self.cameras),
            "active_cameras": self.get_active_camera_count(),
            "total_zones": self.get_zone_count(),
            "cameras": {
                camera_id: {
                    "id": camera_id,
                    "zone": config.zone_name,
                    "source": config.source,
                    "enabled": config.enabled,
                    "running": self.cameras[camera_id].running if camera_id in self.cameras else False
                }
                for camera_id, config in self.camera_configs.items()
            }
        }

    def update_all_workers_model(self, model_id: str):
        """Update detection model for all active cameras"""
        self.current_model = model_id
        for worker in self.cameras.values():
            worker.switch_model(model_id)

    def update_all_workers_tracker(self, tracker_id: str):
        """Update tracker for all active cameras"""
        self.current_tracker = tracker_id
        for worker in self.cameras.values():
            worker.switch_tracker(tracker_id)

    def update_all_workers_segmenter(self, model_id: str):
        """Update segmenter for all active cameras"""
        self.current_segmenter = model_id
        for worker in self.cameras.values():
            worker.switch_segmenter(model_id)


# Singleton instance
_multi_camera_manager = None


def get_multi_camera_manager() -> MultiCameraManager:
    """Get or create the global multi-camera manager instance"""
    global _multi_camera_manager
    if _multi_camera_manager is None:
        _multi_camera_manager = MultiCameraManager()
    return _multi_camera_manager
