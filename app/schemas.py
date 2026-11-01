"""
schemas.py - Pydantic models for request/response validation.

These schemas define the shape of data that flows between
the frontend and backend. They ensure type safety and validation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ─── API Request Schemas ──────────────────────────────────────────────

class APIRequestIn(BaseModel):
    """Input schema for sending an API request."""
    method: str = Field(..., description="HTTP method: GET, POST, PUT, PATCH, DELETE")
    url: str = Field(..., description="The URL to send the request to")
    headers: dict = Field(default_factory=dict, description="Custom headers")
    body: str = Field(default="", description="JSON request body as a string")
    query_params: dict = Field(default_factory=dict, description="Query parameters")
    assertions: Optional[list] = Field(default=None, description="List of assertions")


class AssertionIn(BaseModel):
    """A single assertion to validate against the response."""
    type: str = Field(..., description="status_code, body_contains, json_key, json_value, response_time")
    expected: str = Field(..., description="The expected value")
    key: Optional[str] = Field(default=None, description="JSON key (for json_key/json_value)")


class APIResponseOut(BaseModel):
    """Output schema for the API response."""
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    response_headers: dict = Field(default_factory=dict)
    response_body: str = ""
    error_message: str = ""
    assertion_results: list = Field(default_factory=list)
    history_id: Optional[int] = None


# ─── Request History Schemas ──────────────────────────────────────────

class HistoryOut(BaseModel):
    """Output schema for a request history entry."""
    id: int
    method: str
    url: str
    headers: str = "{}"
    body: str = ""
    query_params: str = "{}"
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    response_headers: str = "{}"
    response_body: str = ""
    error_message: str = ""
    test_result: str = ""
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Collection Schemas ───────────────────────────────────────────────

class CollectionCreate(BaseModel):
    """Input schema to create a collection."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")


class CollectionUpdate(BaseModel):
    """Input schema to update a collection."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None


class SavedRequestCreate(BaseModel):
    """Input schema to save a request into a collection."""
    name: str = Field(..., min_length=1, max_length=255)
    method: str
    url: str
    headers: str = "{}"
    body: str = ""
    query_params: str = "{}"
    collection_id: int


class SavedRequestUpdate(BaseModel):
    """Input schema to update a saved request."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    method: Optional[str] = None
    url: Optional[str] = None
    headers: Optional[str] = None
    body: Optional[str] = None
    query_params: Optional[str] = None


class SavedRequestOut(BaseModel):
    """Output schema for a saved request."""
    id: int
    name: str
    method: str
    url: str
    headers: str = "{}"
    body: str = ""
    query_params: str = "{}"
    collection_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CollectionOut(BaseModel):
    """Output schema for a collection with its saved requests."""
    id: int
    name: str
    description: str = ""
    created_at: Optional[datetime] = None
    saved_requests: list[SavedRequestOut] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ─── Monitoring Schemas ───────────────────────────────────────────────

class EndpointCreate(BaseModel):
    """Input schema to register an endpoint for monitoring."""
    name: str = Field(..., min_length=1, max_length=255)
    url: str
    method: str = "GET"
    expected_status: int = 200


class EndpointUpdate(BaseModel):
    """Input schema to update a monitored endpoint."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    url: Optional[str] = None
    method: Optional[str] = None
    expected_status: Optional[int] = None
    is_active: Optional[bool] = None


class MonitoringCheckOut(BaseModel):
    """Output schema for a single monitoring check result."""
    id: int
    endpoint_id: int
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    is_up: bool = False
    error_message: str = ""
    checked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EndpointOut(BaseModel):
    """Output schema for a monitored endpoint with stats."""
    id: int
    name: str
    url: str
    method: str = "GET"
    expected_status: int = 200
    is_active: bool = True
    created_at: Optional[datetime] = None
    uptime_percentage: Optional[float] = None
    last_check: Optional[MonitoringCheckOut] = None
    total_checks: int = 0

    class Config:
        from_attributes = True


# ─── Report Schemas ───────────────────────────────────────────────────

class ReportSummary(BaseModel):
    """Summary statistics for the report."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time_ms: Optional[float] = None


# ─── Dashboard Schemas ────────────────────────────────────────────────

class DashboardStats(BaseModel):
    """Aggregate statistics for the dashboard."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time_ms: Optional[float] = None
    recent_history: list[HistoryOut] = Field(default_factory=list)
