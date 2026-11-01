"""
models.py - SQLAlchemy ORM models.

Defines the database tables for:
- RequestHistory: stores every API request made through APIWatch
- Collection: groups of saved requests
- SavedRequest: reusable API request configurations
- MonitoredEndpoint: endpoints registered for uptime monitoring
- MonitoringCheck: individual health check results
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base


class RequestHistory(Base):
    """Stores the history of every API request sent through APIWatch."""
    __tablename__ = "request_history"

    id = Column(Integer, primary_key=True, index=True)
    method = Column(String(10), nullable=False)          # GET, POST, etc.
    url = Column(String(2048), nullable=False)
    headers = Column(Text, default="{}")                  # JSON string of headers
    body = Column(Text, default="")                       # JSON request body
    query_params = Column(Text, default="{}")             # JSON string of query params
    status_code = Column(Integer, nullable=True)          # Response status code
    response_time_ms = Column(Float, nullable=True)       # Response time in milliseconds
    response_headers = Column(Text, default="{}")         # JSON string of response headers
    response_body = Column(Text, default="")              # Response body text
    error_message = Column(Text, default="")              # Error if request failed
    test_result = Column(String(10), default="")          # PASS, FAIL, or empty
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Collection(Base):
    """A named group of saved API requests."""
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship: one collection has many saved requests
    saved_requests = relationship(
        "SavedRequest", back_populates="collection", cascade="all, delete-orphan"
    )


class SavedRequest(Base):
    """A reusable API request configuration saved inside a collection."""
    __tablename__ = "saved_requests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    url = Column(String(2048), nullable=False)
    headers = Column(Text, default="{}")
    body = Column(Text, default="")
    query_params = Column(Text, default="{}")
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship back to the parent collection
    collection = relationship("Collection", back_populates="saved_requests")


class MonitoredEndpoint(Base):
    """An API endpoint registered for availability monitoring."""
    __tablename__ = "monitored_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    method = Column(String(10), default="GET")
    expected_status = Column(Integer, default=200)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship: one endpoint has many checks
    checks = relationship(
        "MonitoringCheck", back_populates="endpoint", cascade="all, delete-orphan"
    )


class MonitoringCheck(Base):
    """A single health check result for a monitored endpoint."""
    __tablename__ = "monitoring_checks"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("monitored_endpoints.id"), nullable=False)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    is_up = Column(Boolean, default=False)              # True if status matches expected
    error_message = Column(Text, default="")
    checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship back to the parent endpoint
    endpoint = relationship("MonitoredEndpoint", back_populates="checks")
