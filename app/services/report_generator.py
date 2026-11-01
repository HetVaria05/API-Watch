"""
report_generator.py - CSV report generation service.

Generates CSV reports from request history and provides summary statistics.
"""

import csv
import io
from sqlalchemy.orm import Session

from app.models import RequestHistory


def generate_csv_report(db: Session) -> str:
    """
    Generate a CSV report of all request history.

    The CSV includes:
    - Method, URL, Status Code, Response Time (ms), Timestamp, Test Result

    Args:
        db: Database session

    Returns:
        CSV content as a string
    """
    history = (
        db.query(RequestHistory)
        .order_by(RequestHistory.timestamp.desc())
        .all()
    )

    # Use StringIO to build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    writer.writerow([
        "ID",
        "Method",
        "URL",
        "Status Code",
        "Response Time (ms)",
        "Timestamp",
        "Test Result",
        "Error Message",
    ])

    # Write data rows
    for record in history:
        writer.writerow([
            record.id,
            record.method,
            record.url,
            record.status_code or "N/A",
            record.response_time_ms or "N/A",
            record.timestamp.isoformat() if record.timestamp else "N/A",
            record.test_result or "N/A",
            record.error_message or "",
        ])

    return output.getvalue()


def get_summary_statistics(db: Session) -> dict:
    """
    Calculate summary statistics from request history.

    Returns:
        Dictionary with total_requests, successful_requests,
        failed_requests, and average_response_time_ms.
    """
    history = db.query(RequestHistory).all()

    if not history:
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time_ms": None,
        }

    total = len(history)

    # A request is "successful" if it has a status code in the 200-399 range
    successful = sum(
        1 for r in history
        if r.status_code is not None and 200 <= r.status_code < 400
    )

    failed = total - successful

    # Calculate average response time (excluding failed requests with no time)
    response_times = [
        r.response_time_ms for r in history
        if r.response_time_ms is not None
    ]
    avg_time = round(sum(response_times) / len(response_times), 2) if response_times else None

    return {
        "total_requests": total,
        "successful_requests": successful,
        "failed_requests": failed,
        "average_response_time_ms": avg_time,
    }
