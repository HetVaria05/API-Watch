"""
routes/history.py - API routes for request history.

Provides endpoints to:
- List all request history
- Get details of a single history record
- Delete history records
- Clear all history
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import RequestHistory
from app.schemas import HistoryOut

router = APIRouter(prefix="/api/history", tags=["Request History"])


@router.get("/", response_model=list[HistoryOut])
def list_history(
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    search: Optional[str] = Query(None, description="Search URL"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    db: Session = Depends(get_db),
):
    """
    List request history with optional filtering.

    Supports filtering by HTTP method and searching by URL.
    Results are ordered by timestamp (newest first).
    """
    query = db.query(RequestHistory)

    if method:
        query = query.filter(RequestHistory.method == method.upper())

    if search:
        query = query.filter(RequestHistory.url.contains(search))

    records = query.order_by(RequestHistory.timestamp.desc()).limit(limit).all()
    return records


@router.get("/{history_id}", response_model=HistoryOut)
def get_history_detail(history_id: int, db: Session = Depends(get_db)):
    """Get the full details of a single history record."""
    record = db.query(RequestHistory).filter(RequestHistory.id == history_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="History record not found")
    return record


@router.delete("/{history_id}")
def delete_history(history_id: int, db: Session = Depends(get_db)):
    """Delete a single history record."""
    record = db.query(RequestHistory).filter(RequestHistory.id == history_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="History record not found")

    db.delete(record)
    db.commit()
    return {"message": "History record deleted", "id": history_id}


@router.delete("/")
def clear_history(db: Session = Depends(get_db)):
    """Delete all request history."""
    count = db.query(RequestHistory).delete()
    db.commit()
    return {"message": f"Deleted {count} history records"}
