from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from config.settings import settings

# Create engine
engine = create_engine(
    settings.DB_URL,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    pool_pre_ping=True
)

# Create thread-safe session factory
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

Base = declarative_base()

def get_db():
    """
    Dependency generator for database sessions.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
