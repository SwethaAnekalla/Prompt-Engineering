import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database Upgrade Path Comment:
# For production PostgreSQL migration:
# 1. Install driver: pip install psycopg2-binary
# 2. Update DATABASE_URL environment variable to:
#    postgresql://username:password@hostname:5432/databasename
# 3. Create engine without check_same_thread connect_args (specific to SQLite).

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meeting_minutes.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI Dependency for database session retrieval."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
