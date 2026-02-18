import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data.models import Base, EquipmentStatus
from data.repositories.equipment_repo import EquipmentRepository
from services.alert_service import AlertService
from services.statistics_service import StatisticsService
import datetime

# Setup in-memory DB for testing
@pytest.fixture(scope="module")
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_equipment_repo(test_db):
    repo = EquipmentRepository(test_db)
    
    # Create Type
    etype = repo.create_type("TestDrill", "Drill for testing")
    assert etype.id is not None
    
    # Create Item
    item = repo.create_item("DRILL-001", etype.id)
    assert item.id is not None
    assert item.status == EquipmentStatus.IN_STOCK
    
    # Update Status (Movement)
    updated_item = repo.update_item_status(item.id, EquipmentStatus.IN_USE)
    assert updated_item.status == EquipmentStatus.IN_USE

def test_alert_service(test_db):
    service = AlertService(test_db)
    
    # Create Alert
    alert = service.create_alert("TEST", "Test Message")
    assert alert is not None
    assert alert.is_acknowledged == False
    
    # Get Alerts
    alerts = service.get_active_alerts()
    assert len(alerts) >= 1
    assert alerts[0].message == "Test Message"
    
    # Acknowledge
    service.acknowledge_alert(alert.id)
    alerts_after = service.get_active_alerts()
    # Should be filtered out or check status
    assert len([a for a in alerts_after if a.id == alert.id]) == 0

def test_statistics_service(test_db):
    stats = StatisticsService(test_db)
    
    # We created a movement in equipment_repo test (update_item_status creates history)
    # So we should have at least 1 movement today
    
    count = stats.get_todays_movements_count()
    assert count >= 1
    
    top_items = stats.get_top_used_items()
    assert len(top_items) > 0
    assert top_items[0].unique_ref == "DRILL-001"
