"""
FastAPI Server - Magasin Intelligent IA
Backend principal avec REST API + WebSocket streaming vidéo
"""
import asyncio
import base64
import cv2
import json
from typing import List, Dict, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path

from workers.async_video_worker import AsyncVideoWorker
from workers.multi_camera_manager import get_multi_camera_manager, CameraConfig
from data.database import get_db
from data.repositories.zone_repo import get_zone_repo
from data.models import EquipmentType
from services.logger_service import logger
from ai.temporal_detection import get_temporal_engine

# Global variables
video_worker = None
multi_camera_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app"""
    global video_worker, multi_camera_manager
    
    # Startup
    logger.info("Starting FastAPI server...")
    
    # Register notification callbacks for Temporal engine
    temporal_engine = get_temporal_engine()
    
    def on_validation_created(data):
        asyncio.create_task(notification_manager.broadcast({
            "type": "VALIDATION_CREATED",
            "message": f"Nouveau stock détecté: {data['object_type']} ({data['quantity_delta']:+d})",
            "data": data
        }))
        
    def on_validation_approved(data):
        asyncio.create_task(notification_manager.broadcast({
            "type": "VALIDATION_APPROVED",
            "message": f"Validation approuvée: {data['object_type']} ({data['quantity_delta']:+d})",
            "data": data
        }))

    def on_validation_rejected(data):
        asyncio.create_task(notification_manager.broadcast({
            "type": "VALIDATION_REJECTED",
            "message": f"Validation rejetée: {data['object_type']}",
            "data": data
        }))

    temporal_engine.on_validation_created = on_validation_created
    temporal_engine.on_validation_approved = on_validation_approved
    temporal_engine.on_validation_rejected = on_validation_rejected

    # Initialize multi-camera manager
    multi_camera_manager = get_multi_camera_manager()
    multi_camera_manager.load_from_db()
    logger.success("Multi-Camera Manager initialized and cameras loaded from DB")
    
    # Initialize default camera (webcam) and add to manager
    # Diagnostic showed index 2 is the working one on this system
    video_worker = AsyncVideoWorker(source=2, camera_id="0")
    video_worker.start()
    
    if multi_camera_manager:
        multi_camera_manager.cameras["0"] = video_worker
        multi_camera_manager.camera_configs["0"] = CameraConfig(
            camera_id="0",
            source="2",
            zone_id="ZONE-0",
            zone_name="Webcam Locale"
        )
    
    logger.success("Video worker started and registered with manager")
    
    yield
    
    # Shutdown
    logger.info("Shutting down server...")
    if multi_camera_manager:
        multi_camera_manager.stop_all()
    if video_worker:
        video_worker.stop()
    logger.success("Server shutdown complete")

app = FastAPI(title="Magasin IA API", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
frontend_path = Path(__file__).parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# ============================================================================
# Notification System - Global Broadcast
# ============================================================================

class NotificationManager:
    """Manages active WebSocket connections for notifications."""
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Notification client connected: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Notification client disconnected")

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        if not self.active_connections:
            return
            
        message_str = json.dumps(message)
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting notification: {e}")
                disconnected.add(connection)
        
        for conn in disconnected:
            self.active_connections.remove(conn)

notification_manager = NotificationManager()

@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """WebSocket endpoint for system-wide notifications."""
    await notification_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, we primarily push data to client
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Notification WebSocket error: {e}")
        notification_manager.disconnect(websocket)

# ============================================================================
# WebSocket Endpoint - Video Streaming
# ============================================================================

@app.websocket("/ws/video/{camera_id}")
async def websocket_video(websocket: WebSocket, camera_id: str):
    """
    WebSocket endpoint for real-time video streaming of a specific camera.
    """
    await websocket.accept()
    logger.info(f"WebSocket client connected to {camera_id}: {websocket.client}")
    
    # Get the correct worker
    worker = None
    if camera_id in ["0", "default", "webcam"]:
        worker = video_worker
    elif multi_camera_manager:
        worker = multi_camera_manager.get_camera(camera_id)
        
    if not worker:
        logger.error(f"Worker for camera {camera_id} not found")
        await websocket.close()
        return

    try:
        while True:
            frame_data = worker.get_frame()
            
            if frame_data:
                frame, detections, alerts = frame_data
                
                # Prepare metadata
                metadata = {
                    "camera_id": camera_id,
                    "detections": detections,
                    "alerts": alerts,
                    "timestamp": asyncio.get_event_loop().time()
                }
                metadata_json = json.dumps(metadata).encode('utf-8')
                metadata_len = len(metadata_json)
                
                # Encode frame to JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                # Binary format: [4 bytes metadata_len] [N bytes metadata] [Raw JPEG bytes]
                header = metadata_len.to_bytes(4, byteorder='big')
                payload = header + metadata_json + buffer.tobytes()
                
                await websocket.send_bytes(payload)
            
            await asyncio.sleep(0.01)  # High performance polling
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from {camera_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {camera_id}: {e}")
        try:
            await websocket.close()
        except:
            pass

# ============================================================================
# REST API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Redirect to surveillance dashboard"""
    return FileResponse(str(frontend_path / "surveillance.html"))

@app.get("/{page}.html")
async def get_page(page: str):
    """Serve any HTML page from the frontend directory"""
    path = frontend_path / f"{page}.html"
    if path.exists():
        return FileResponse(str(path))
    return {"error": "Page not found"}, 404

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "video_worker": "running" if video_worker and video_worker.running else "stopped"
    }

@app.get("/api/equipment")
async def get_equipment():
    """Get all equipment items with full metadata for ASECNA inventory"""
    from data.repositories.equipment_repo import EquipmentRepository
    db = next(get_db())
    repo = EquipmentRepository(db)
    items = repo.get_all_items()
    
    return {
        "success": True,
        "data": [
            {
                "id": item.id,
                "unique_ref": item.unique_ref,
                "name": item.equipment_type.name if item.equipment_type else "Unknown Item",
                "category": item.equipment_type.description if item.equipment_type else "Uncategorized",
                "status": item.status.value if hasattr(item.status, 'value') else item.status,
                "declared_quantity": item.declared_quantity,
                "detected_quantity": item.detected_quantity,
                "counting_confidence": item.counting_confidence,
                "zone_name": item.current_zone.name if item.current_zone else "Storage B",
                "last_seen": item.last_seen_at.strftime("%Y-%m-%d %H:%M") if item.last_seen_at else "Never"
            }
            for item in items
        ]
    }

@app.get("/api/alerts")
async def get_alerts():
    """Get recent alerts"""
    from services.alert_service import AlertService
    service = AlertService()
    alerts = service.get_recent_alerts(limit=50)
    
    return {
        "success": True,
        "data": [
            {
                "id": alert.id,
                "type": alert.alert_type,
                "message": alert.message,
                "severity": alert.severity,
                "timestamp": alert.created_at.isoformat()
            }
            for alert in alerts
        ]
    }

@app.get("/api/stats")
async def get_statistics():
    """Get real system statistics from DB"""
    from services.statistics_service import StatisticsService
    service = StatisticsService()
    stats = service.get_inventory_stats()
    
    return {
        "success": True,
        "data": {
            "movements_today": service.get_todays_movements_count(),
            "total_inventory": stats["total_equipment"],
            "active_in_use": stats["active_equipment"],
            "critical_alerts": stats["critical_alerts"],
            "low_stock_warnings": stats["low_stock_warnings"]
        }
    }


@app.get("/api/models/available")
async def get_available_models():
    """Get list of available AI models"""
    return {
        "success": True,
        "data": {
            "detectors": [
                {"id": "yolov8n", "name": "YOLOv8 Nano", "size": "6MB"},
                {"id": "yolov8s", "name": "YOLOv8 Small", "size": "22MB"},
                {"id": "yolov8m", "name": "YOLOv8 Medium", "size": "52MB"},
                {"id": "yolov8l", "name": "YOLOv8 Large", "size": "88MB"},
                {"id": "yolov11n", "name": "YOLOv11 Nano", "size": "5MB"},
            ],
            "trackers": [
                {"id": "bytetrack", "name": "ByteTrack", "description": "High-performance multi-object tracking"},
                {"id": "botsort", "name": "BoT-SORT", "description": "Robust tracking with ReID"},
                {"id": "deepsort", "name": "DeepSORT", "description": "Classic deep learning tracker"},
            ],
            "segmenters": [
                {"id": "sam2-base", "name": "SAM2 Base", "size": "154MB"},
                {"id": "sam2-large", "name": "SAM2 Large", "size": "220MB"},
            ]
        }
    }

@app.post("/api/models/detector")
async def switch_detector(model_id: str):
    """Switch detection model for all cameras"""
    logger.info(f"Switching detector to: {model_id}")
    if multi_camera_manager:
        multi_camera_manager.update_all_workers_model(model_id)
        return {"success": True, "message": f"Switched all cameras to {model_id}"}
    return {"success": False, "message": "Multi-camera manager not found"}

@app.post("/api/models/tracker")
async def switch_tracker(tracker_id: str):
    """Switch tracking model for all cameras"""
    logger.info(f"Switching tracker to: {tracker_id}")
    if multi_camera_manager:
        multi_camera_manager.update_all_workers_tracker(tracker_id)
        return {"success": True, "message": f"Switched tracker to {tracker_id} for all cameras"}
    return {"success": False, "message": "Multi-camera manager not found"}

@app.post("/api/models/segmentation")
async def switch_segmenter(model_id: str):
    """Switch segmentation model for all cameras"""
    logger.info(f"Switching segmenter to: {model_id}")
    if multi_camera_manager:
        multi_camera_manager.update_all_workers_segmenter(model_id)
        return {"success": True, "message": f"Switched segmenter to {model_id} for all cameras"}
    return {"success": False, "message": "Multi-camera manager not found"}

# === Multi-Camera Management Endpoints ===

@app.get("/api/cameras")
async def get_cameras():
    """Get all active cameras and their status"""
    if multi_camera_manager:
        status = multi_camera_manager.get_status()
        return {"success": True, "data": status}
    return {"success": False, "message": "Multi-camera manager not initialized"}

@app.post("/api/cameras/add")
async def add_camera_persistent(data: dict):
    """Add a new camera with IP and Zone, and persist it"""
    global multi_camera_manager
    
    zone_name = data.get("zone_name")
    ip_address = data.get("ip_address")
    equipment_type_id = data.get("equipment_type_id")
    
    if not zone_name or not ip_address:
        return {"success": False, "message": "Missing zone name or IP address"}
    
    # 1. Persist in Database
    try:
        from sqlalchemy.orm import Session
        from data.database import engine
        with Session(engine) as session:
            repo = get_zone_repo(session)
            zone = repo.add_zone(
                name=zone_name,
                camera_id=ip_address,
                equipment_type_id=equipment_type_id
            )
            zone_id = f"ZONE-{zone.id}"
            camera_id = f"CAM-{zone.id}"
    except Exception as e:
        logger.error(f"Failed to persist camera in DB: {e}")
        return {"success": False, "message": f"DB Error: {e}"}

    # 2. Add to MultiCameraManager
    if multi_camera_manager:
        config = CameraConfig(
            camera_id=camera_id,
            source=ip_address,
            zone_id=zone_id,
            zone_name=zone_name
        )
        success = multi_camera_manager.add_camera(config)
        if success:
            return {"success": True, "message": f"Camera {camera_id} added successfully for zone {zone_name}"}
    
    return {"success": False, "message": f"Failed to add camera {camera_id} to manager"}

@app.get("/api/equipment-types")
async def get_equipment_types():
    """Get list of equipment types for dropdowns"""
    from sqlalchemy.orm import Session
    from data.database import engine
    with Session(engine) as session:
        types = session.query(EquipmentType).all()
        return {
            "success": True, 
            "data": [{"id": t.id, "name": t.name} for t in types]
        }

@app.delete("/api/cameras/{camera_id}")
async def remove_camera(camera_id: str):
    """Remove a camera from the system"""
    if not multi_camera_manager:
        return {"success": False, "message": "Multi-camera manager not initialized"}
    
    success = multi_camera_manager.remove_camera(camera_id)
    if success:
        return {"success": True, "message": f"Camera {camera_id} removed"}
    return {"success": False, "message": f"Failed to remove camera {camera_id}"}

@app.get("/api/zones")
async def get_zones():
    """Get all configured zones"""
    if not multi_camera_manager:
        return {"success": False, "message": "Multi-camera manager not initialized"}
    
    zones = multi_camera_manager.get_all_zones()
    zones_data = [
        {
            "zone_id": zone.zone_id,
            "name": zone.name,
            "camera_id": zone.camera_id,
            "equipment_type": zone.equipment_type,
            "roi_coords": zone.roi_coords
        }
        for zone in zones.values()
    ]
    return {"success": True, "data": zones_data}

@app.put("/api/zones/{zone_id}/roi")
async def update_zone_roi(zone_id: str, roi_coords: list):
    """Update ROI coordinates for a zone"""
    if not multi_camera_manager:
        return {"success": False, "message": "Multi-camera manager not initialized"}
    
    success = multi_camera_manager.update_zone_roi(zone_id, roi_coords)
    if success:
        return {"success": True, "message": f"ROI updated for zone {zone_id}"}
    return {"success": False, "message": f"Failed to update ROI for zone {zone_id}"}

@app.get("/api/cameras/status")
async def cameras_status():
    """Get full status of camera system"""
    if not multi_camera_manager:
        return {"success": False, "message": "Multi-camera manager not initialized"}
    
    status = multi_camera_manager.get_status()
    # Add success flag for frontend consistency
    status["success"] = True
    return status

# === Reports & Analytics Endpoints ===

@app.get("/api/reports/weekly")
async def get_weekly_report():
    """Generate weekly report data"""
    from services.report_service import get_report_service
    
    try:
        report_service = get_report_service()
        report_data = report_service.generate_weekly_report()
        return {"success": True, "data": report_data}
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        return {"success": False, "message": str(e)}

@app.get("/api/reports/export/excel")
async def export_excel_report():
    """Export weekly report as Excel file"""
    from services.report_service import get_report_service
    from fastapi.responses import Response
    
    try:
        report_service = get_report_service()
        report_data = report_service.generate_weekly_report()
        excel_bytes = report_service.export_to_excel(report_data)
        
        filename = f"ASECNA_Weekly_Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Error exporting Excel: {e}")
        return {"success": False, "message": str(e)}

@app.get("/api/reports/export/csv")
async def export_csv_report(sheet: str = "summary"):
    """Export specific sheet as CSV"""
    from services.report_service import get_report_service
    from fastapi.responses import Response
    
    try:
        report_service = get_report_service()
        report_data = report_service.generate_weekly_report()
        csv_bytes = report_service.export_to_csv(report_data, sheet_name=sheet)
        
        filename = f"ASECNA_{sheet}_{datetime.now().strftime('%Y-%m-%d')}.csv"
        
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return {"success": False, "message": str(e)}
@app.get("/api/analytics/stats")
async def get_analytics_stats():
    """Get real-time analytics statistics for dashboard"""
    # Mock data - replace with actual queries
    return {
        "success": True,
        "data": {
            "total_stock": 1385,
            "total_value": 2450000,  # in XOF
            "movements_today": 23,
            "withdrawals_pending": 5,
            "ai_accuracy": 0.91,
            "stock_by_category": [
                {"name": "RAM", "value": 450},
                {"name": "Computers", "value": 535},
                {"name": "HVAC", "value": 180},
                {"name": "Printers", "value": 120},
                {"name": "Network", "value": 100}
            ],
            "movements_trend": [
                {"date": "2026-02-07", "entries": 12, "exits": 18},
                {"date": "2026-02-08", "entries": 15, "exits": 20},
                {"date": "2026-02-09", "entries": 10, "exits": 15},
                {"date": "2026-02-10", "entries": 18, "exits": 22},
                {"date": "2026-02-11", "entries": 20, "exits": 25},
                {"date": "2026-02-12", "entries": 16, "exits": 19},
                {"date": "2026-02-13", "entries": 14, "exits": 17}
            ],
            "withdrawals_by_country": [
                {"country": "Côte d'Ivoire", "count": 8},
                {"country": "Mali", "count": 5},
                {"country": "Burkina Faso", "count": 4},
                {"country": "Sénégal", "count": 3},
                {"country": "Gabon", "count": 2},
                {"country": "Other", "count": 1}
            ]
        }
    }

# === Temporal Detection & Validation Endpoints ===

@app.get("/api/config/detection")
async def get_detection_config():
    """Get current detection configuration from DB"""
    from services.config_service import get_config_manager
    config_manager = get_config_manager()
    configs = config_manager.get_all_configs()
    
    return {
        "success": True,
        "data": {
            "stability_duration_minutes": int(configs.get("stability_duration_minutes", 60)),
            "confidence_threshold": float(configs.get("confidence_threshold", 0.60)),
            "alert_delay_hours": int(configs.get("alert_delay_hours", 3)),
            "asecna_countries": configs.get("asecna_countries", "[]")
        }
    }

@app.post("/api/config/detection/update")
async def update_detection_config(config: dict):
    """Update detection configuration in DB and sync engine"""
    from services.config_service import get_config_manager
    config_manager = get_config_manager()
    
    for key, value in config.items():
        config_manager.set_config(key, value)
        
    return {"success": True, "message": "Database configuration updated and engine synced"}

@app.get("/api/detection/temporal/status")
async def get_temporal_status():
    """Get status summary of temporal detection engine"""
    from ai.temporal_detection import get_temporal_engine
    engine = get_temporal_engine()
    return {"success": True, "data": engine.get_tracking_summary()}

@app.get("/api/validation/requests")
async def get_validation_requests():
    """Get list of pending validation requests"""
    from ai.temporal_detection import get_temporal_engine
    engine = get_temporal_engine()
    requests = [v for v in engine.pending_validations.values() if v['status'] == 'pending']
    return {"success": True, "data": requests}

@app.post("/api/validation/approve/{validation_id}")
async def approve_validation(validation_id: str, admin_id: str = "admin_1"):
    """Approve a validation request"""
    from ai.temporal_detection import get_temporal_engine
    engine = get_temporal_engine()
    success = engine.approve_validation(validation_id, admin_id)
    if success:
        return {"success": True, "message": f"Validation {validation_id} approved"}
    return {"success": False, "message": "Failed to approve validation"}

@app.post("/api/validation/reject/{validation_id}")
async def reject_validation(validation_id: str, reason: str, admin_id: str = "admin_1"):
    """Reject a validation request"""
    from ai.temporal_detection import get_temporal_engine
    engine = get_temporal_engine()
    success = engine.reject_validation(validation_id, admin_id, reason)
    if success:
        return {"success": True, "message": f"Validation {validation_id} rejected"}
    return {"success": False, "message": "Failed to reject validation"}

@app.get("/api/search/object")
async def search_object(name: str):
    """Search for an object across all cameras"""
    from ai.temporal_detection import get_temporal_engine
    engine = get_temporal_engine()
    
    results = []
    for (obj_type, cam_id), tracking in engine.active_trackings.items():
        if name.lower() in obj_type.lower():
            results.append({
                "object_type": obj_type,
                "camera_id": cam_id,
                "status": tracking.status.value,
                "duration": tracking.get_duration_minutes(),
                "avg_confidence": tracking.avg_confidence,
                "tracking_link": f"/surveillance?camera={cam_id}&highlight={obj_type}"
            })
            
    return {"success": True, "data": results}

if __name__ == "__main__":
    from datetime import datetime
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
