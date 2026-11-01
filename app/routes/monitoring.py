"""
routes/monitoring.py - API routes for endpoint monitoring.

Provides endpoints to:
- Register endpoints for monitoring
- Run manual health checks
- View monitoring status and uptime
- Delete monitored endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MonitoredEndpoint, MonitoringCheck
from app.schemas import (
    EndpointCreate, EndpointUpdate, EndpointOut, MonitoringCheckOut,
)
from app.services.monitor import check_endpoint, check_all_endpoints, calculate_uptime, get_last_check

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])


@router.get("/endpoints", response_model=list[EndpointOut])
def list_endpoints(db: Session = Depends(get_db)):
    """List all monitored endpoints with their uptime stats."""
    endpoints = db.query(MonitoredEndpoint).order_by(MonitoredEndpoint.created_at.desc()).all()

    result = []
    for ep in endpoints:
        uptime = calculate_uptime(ep.id, db)
        last = get_last_check(ep.id, db)
        total = db.query(MonitoringCheck).filter(MonitoringCheck.endpoint_id == ep.id).count()

        endpoint_data = EndpointOut(
            id=ep.id,
            name=ep.name,
            url=ep.url,
            method=ep.method,
            expected_status=ep.expected_status,
            is_active=ep.is_active,
            created_at=ep.created_at,
            uptime_percentage=uptime,
            last_check=MonitoringCheckOut.model_validate(last) if last else None,
            total_checks=total,
        )
        result.append(endpoint_data)

    return result


@router.post("/endpoints", response_model=EndpointOut, status_code=201)
def create_endpoint(data: EndpointCreate, db: Session = Depends(get_db)):
    """Register a new endpoint for monitoring."""
    endpoint = MonitoredEndpoint(
        name=data.name,
        url=data.url,
        method=data.method.upper(),
        expected_status=data.expected_status,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)

    return EndpointOut(
        id=endpoint.id,
        name=endpoint.name,
        url=endpoint.url,
        method=endpoint.method,
        expected_status=endpoint.expected_status,
        is_active=endpoint.is_active,
        created_at=endpoint.created_at,
        uptime_percentage=None,
        last_check=None,
        total_checks=0,
    )


@router.put("/endpoints/{endpoint_id}", response_model=EndpointOut)
def update_endpoint(endpoint_id: int, data: EndpointUpdate, db: Session = Depends(get_db)):
    """Update a monitored endpoint's configuration."""
    endpoint = db.query(MonitoredEndpoint).filter(MonitoredEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    if data.name is not None:
        endpoint.name = data.name
    if data.url is not None:
        endpoint.url = data.url
    if data.method is not None:
        endpoint.method = data.method.upper()
    if data.expected_status is not None:
        endpoint.expected_status = data.expected_status
    if data.is_active is not None:
        endpoint.is_active = data.is_active

    db.commit()
    db.refresh(endpoint)

    uptime = calculate_uptime(endpoint.id, db)
    last = get_last_check(endpoint.id, db)
    total = db.query(MonitoringCheck).filter(MonitoringCheck.endpoint_id == endpoint.id).count()

    return EndpointOut(
        id=endpoint.id,
        name=endpoint.name,
        url=endpoint.url,
        method=endpoint.method,
        expected_status=endpoint.expected_status,
        is_active=endpoint.is_active,
        created_at=endpoint.created_at,
        uptime_percentage=uptime,
        last_check=MonitoringCheckOut.model_validate(last) if last else None,
        total_checks=total,
    )


@router.delete("/endpoints/{endpoint_id}")
def delete_endpoint(endpoint_id: int, db: Session = Depends(get_db)):
    """Delete a monitored endpoint and all its checks."""
    endpoint = db.query(MonitoredEndpoint).filter(MonitoredEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    db.delete(endpoint)
    db.commit()
    return {"message": "Endpoint deleted", "id": endpoint_id}


@router.post("/endpoints/{endpoint_id}/check", response_model=MonitoringCheckOut)
async def run_check(endpoint_id: int, db: Session = Depends(get_db)):
    """Manually trigger a health check for a single endpoint."""
    endpoint = db.query(MonitoredEndpoint).filter(MonitoredEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    check = await check_endpoint(endpoint, db)
    return check


@router.post("/check-all", response_model=list[MonitoringCheckOut])
async def run_all_checks(db: Session = Depends(get_db)):
    """Manually trigger health checks for all active endpoints."""
    results = await check_all_endpoints(db)
    return results


@router.get("/endpoints/{endpoint_id}/checks", response_model=list[MonitoringCheckOut])
def list_checks(endpoint_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """List recent monitoring checks for an endpoint."""
    endpoint = db.query(MonitoredEndpoint).filter(MonitoredEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    checks = (
        db.query(MonitoringCheck)
        .filter(MonitoringCheck.endpoint_id == endpoint_id)
        .order_by(MonitoringCheck.checked_at.desc())
        .limit(limit)
        .all()
    )
    return checks
