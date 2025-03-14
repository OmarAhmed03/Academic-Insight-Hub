from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
from sqlalchemy.pool import QueuePool
import logging
import streamlit as st
from sqlalchemy.ext.declarative import declarative_base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL - can be configured via environment variable
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///abdalla.db')

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {},
    echo=False  # Set to True for debugging SQL queries
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create scoped session for thread safety
ScopedSession = scoped_session(SessionLocal)

def get_db():
    """
    Get a database session.
    Usage:
        db = next(get_db())
    """
    db = ScopedSession()
    try:
        yield db
    finally:
        db.close()

def get_db_context():
    """
    Get a database session as a context manager.
    Usage:
        with get_db_context() as db:
            # use db here
    """
    db = ScopedSession()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables and default data."""
    from models import Base
    
    # Create tables
    if not st.session_state.get("db_initialized", False):
        logger.info("Creating database tables if they don't exist...")
        Base.metadata.create_all(bind=engine)
        st.session_state["db_initialized"] = True
        
        # Import and run database initialization
        try:
            import init_db
            init_db.initialize_database()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
    else:
        logger.debug("Database already initialized")
