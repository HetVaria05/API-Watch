"""
routes/reports.py - API routes for report generation.

Provides endpoints to:
- Download CSV report of request history
- Get summary statistics
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.database import get_db
from app.schemas import ReportSummary
from app.services.report_generator import generate_csv_report, get_summary_statistics

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/csv")
def download_csv_report(db: Session = Depends(get_db)):
    """
    Download a CSV report of all request history.

    Returns the CSV file as a downloadable attachment.
    """
    csv_content = generate_csv_report(db)

    # Create a streaming response with CSV content type
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=apiwatch_report.csv"
        },
    )


@router.get("/summary", response_model=ReportSummary)
def get_report_summary(db: Session = Depends(get_db)):
    """
    Get summary statistics of all API requests.

    Returns total requests, successful/failed counts, and average response time.
    """
    stats = get_summary_statistics(db)
    return ReportSummary(**stats)


@router.get("/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Get dashboard statistics including summary and recent activity.

    Combines summary stats with the 10 most recent history records.
    """
    from app.models import RequestHistory

    stats = get_summary_statistics(db)

    # Get recent history
    recent = (
        db.query(RequestHistory)
        .order_by(RequestHistory.timestamp.desc())
        .limit(10)
        .all()
    )

    # Convert to dicts for JSON response
    recent_list = []
    for r in recent:
        recent_list.append({
            "id": r.id,
            "method": r.method,
            "url": r.url,
            "status_code": r.status_code,
            "response_time_ms": r.response_time_ms,
            "test_result": r.test_result,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        })

    return {
        **stats,
        "recent_history": recent_list,
    }
