from data.database import engine, Base
from data.models import User, EquipmentType, Zone
from sqlalchemy.orm import Session
from services.logger_service import logger

def init_db():
    logger.info("Initializing database...")
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.success("Tables created successfully.")
        
        # Seed initial data
        with Session(engine) as session:
            # Check if we have types
            if session.query(EquipmentType).count() == 0:
                logger.info("Seeding default equipment types...")
                types = [
                    EquipmentType(name="Perceuse", description="Perceuses électriques", alert_threshold=2),
                    EquipmentType(name="Multimètre", description="Appareils de mesure", alert_threshold=5),
                    EquipmentType(name="Gilet Sécu", description="EPI", alert_threshold=10)
                ]
                session.add_all(types)
                session.commit()
                logger.success("Default types seeded.")
                
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}")

if __name__ == "__main__":
    init_db()
