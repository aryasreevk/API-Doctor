from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    JSON
)

from datetime import datetime, timezone

from backend.database import Base


# ==========================================
# API REQUEST HISTORY MODEL
# ==========================================

class APIHistory(Base):

    __tablename__ = "api_history"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # API request details
    url = Column(String(1000), nullable=False)
    method = Column(String(10), nullable=False)

    # Response information
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=True)

    # Health information
    health = Column(String(50), nullable=True)
    health_score = Column(Integer, nullable=True)
    json_valid = Column(Boolean, nullable=True)

    # Diagnostic information
    issues = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    ai_diagnosis = Column(Text, nullable=True)

    # Request timestamp
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )


# ==========================================
# SAVED API REQUEST COLLECTIONS MODEL
# ==========================================

class APIRequestCollection(Base):

    __tablename__ = "api_request_collections"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Collection details
    name = Column(String(120), nullable=False)

    # API request details
    url = Column(String(1000), nullable=False)
    method = Column(String(10), nullable=False, default="GET")

    # Request configuration
    headers = Column(JSON, default=dict)
    params = Column(JSON, default=dict)
    json_body = Column(JSON, nullable=True)

    # Creation timestamp
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )