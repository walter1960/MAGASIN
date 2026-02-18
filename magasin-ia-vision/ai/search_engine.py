"""
Object Search Engine for ASECNA Stock Management
Handles searching for specific items across all cameras and generating tracking links.
"""

from typing import List, Dict, Optional
import logging
from ai.temporal_detection import get_temporal_engine

logger = logging.getLogger(__name__)

class ObjectSearchEngine:
    """
    Search engine to locate objects across the camera network.
    """
    
    def __init__(self):
        self.temporal_engine = get_temporal_engine()

    def search_by_name(self, query: str) -> List[Dict]:
        """
        Search for objects matching the query string.
        """
        results = []
        trackings = self.temporal_engine.active_trackings
        
        for (obj_type, cam_id), tracking in trackings.items():
            if query.lower() in obj_type.lower():
                results.append({
                    "object_type": obj_type,
                    "camera_id": cam_id,
                    "status": tracking.status.value,
                    "duration_minutes": tracking.get_duration_minutes(),
                    "avg_confidence": tracking.avg_confidence,
                    "last_seen": tracking.last_seen.strftime("%Y-%m-%d %H:%M:%S"),
                    "tracking_id": tracking.detection_events[-1].tracking_id if tracking.detection_events else None,
                    "bbox": tracking.detection_events[-1].bbox_coords if tracking.detection_events else None
                })
        
        # Sort by confidence and duration
        results.sort(key=lambda x: (x['avg_confidence'], x['duration_minutes']), reverse=True)
        return results

    def get_object_locations(self, object_type: str) -> List[str]:
        """
        Get all camera IDs where a specific object type is currently tracked.
        """
        locations = []
        for (obj_type, cam_id) in self.temporal_engine.active_trackings.keys():
            if obj_type.lower() == object_type.lower():
                locations.append(cam_id)
        return list(set(locations))

# Singleton instance
_search_engine = None

def get_object_search_engine() -> ObjectSearchEngine:
    """Get or create the global search engine instance"""
    global _search_engine
    if _search_engine is None:
        _search_engine = ObjectSearchEngine()
    return _search_engine
