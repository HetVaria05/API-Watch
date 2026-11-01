"""
monitor.py - API monitoring service.

Checks the availability of registered endpoints and calculates uptime.
Does NOT run background monitoring automatically — checks are triggered
manually or via the API.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models import MonitoredEndpoint, MonitoringCheck
from app.services.api_client import send_request


async def check_endpoint(endpoint: MonitoredEndpoint, db: Session) -> MonitoringCheck:
    """
    Perform a health check on a single monitored endpoint.

    Sends a request to the endpoint URL, compares the status code
    to the expected value, and records the result.

    Args:
        endpoint: The MonitoredEndpoint to check
        db: Database session

    Returns:
        The created MonitoringCheck record
    """
    # Send the request
    response = await send_request(
        method=endpoint.method,
        url=endpoint.url,
    )

    # Determine if the endpoint is up
    is_up = (
        response["status_code"] is not None
        and response["status_code"] == endpoint.expected_status
        and not response["error_message"]
    )

    # Create the check record
    check = MonitoringCheck(
        endpoint_id=endpoint.id,
        status_code=response["status_code"],
        response_time_ms=response["response_time_ms"],
        is_up=is_up,
        error_message=response["error_message"],
        checked_at=datetime.now(timezone.utc),
    )

    db.add(check)
    db.commit()
    db.refresh(check)

    return check


async def check_all_endpoints(db: Session) -> list[MonitoringCheck]:
    """
    Check all active monitored endpoints.

    Returns:
        List of MonitoringCheck records created.
    """
    endpoints = db.query(MonitoredEndpoint).filter(
        MonitoredEndpoint.is_active == True
    ).all()

    results = []
    for endpoint in endpoints:
        check = await check_endpoint(endpoint, db)
        results.append(check)

    return results


def calculate_uptime(endpoint_id: int, db: Session) -> float | None:
    """
    Calculate the uptime percentage for a monitored endpoint.

    Uptime % = (number of successful checks / total checks) * 100

    Args:
        endpoint_id: The endpoint ID to calculate uptime for
        db: Database session

    Returns:
        Uptime percentage (0-100) or None if no checks exist
    """
    checks = db.query(MonitoringCheck).filter(
        MonitoringCheck.endpoint_id == endpoint_id
    ).all()

    if not checks:
        return None

    total = len(checks)
    successful = sum(1 for c in checks if c.is_up)

    return round((successful / total) * 100, 2)


def get_last_check(endpoint_id: int, db: Session) -> MonitoringCheck | None:
    """
    Get the most recent monitoring check for an endpoint.

    Args:
        endpoint_id: The endpoint ID
        db: Database session

    Returns:
        The most recent MonitoringCheck or None
    """
    return (
        db.query(MonitoringCheck)
        .filter(MonitoringCheck.endpoint_id == endpoint_id)
        .order_by(MonitoringCheck.checked_at.desc())
        .first()
    )
