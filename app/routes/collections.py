"""
routes/collections.py - API routes for request collections.

Provides endpoints to:
- Create, list, update, and delete collections
- Create, update, delete, and execute saved requests
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.models import Collection, SavedRequest
from app.schemas import (
    CollectionCreate, CollectionUpdate, CollectionOut,
    SavedRequestCreate, SavedRequestUpdate, SavedRequestOut,
    APIRequestIn, APIResponseOut,
)
from app.services.api_client import send_request, parse_headers
from app.services.validator import run_assertions
from app.models import RequestHistory

router = APIRouter(prefix="/api/collections", tags=["Collections"])


# ─── Collection CRUD ──────────────────────────────────────────────────

@router.get("/", response_model=list[CollectionOut])
def list_collections(db: Session = Depends(get_db)):
    """List all collections with their saved requests."""
    return db.query(Collection).order_by(Collection.created_at.desc()).all()


@router.post("/", response_model=CollectionOut, status_code=201)
def create_collection(data: CollectionCreate, db: Session = Depends(get_db)):
    """Create a new collection."""
    collection = Collection(name=data.name, description=data.description)
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(collection_id: int, db: Session = Depends(get_db)):
    """Get a single collection with its saved requests."""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.put("/{collection_id}", response_model=CollectionOut)
def update_collection(collection_id: int, data: CollectionUpdate, db: Session = Depends(get_db)):
    """Update a collection's name or description."""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    if data.name is not None:
        collection.name = data.name
    if data.description is not None:
        collection.description = data.description

    db.commit()
    db.refresh(collection)
    return collection


@router.delete("/{collection_id}")
def delete_collection(collection_id: int, db: Session = Depends(get_db)):
    """Delete a collection and all its saved requests."""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    db.delete(collection)
    db.commit()
    return {"message": "Collection deleted", "id": collection_id}


# ─── Saved Request CRUD ──────────────────────────────────────────────

@router.post("/requests", response_model=SavedRequestOut, status_code=201)
def create_saved_request(data: SavedRequestCreate, db: Session = Depends(get_db)):
    """Save a new request into a collection."""
    # Verify the collection exists
    collection = db.query(Collection).filter(Collection.id == data.collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    saved = SavedRequest(
        name=data.name,
        method=data.method,
        url=data.url,
        headers=data.headers,
        body=data.body,
        query_params=data.query_params,
        collection_id=data.collection_id,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


@router.put("/requests/{request_id}", response_model=SavedRequestOut)
def update_saved_request(request_id: int, data: SavedRequestUpdate, db: Session = Depends(get_db)):
    """Update a saved request."""
    saved = db.query(SavedRequest).filter(SavedRequest.id == request_id).first()
    if not saved:
        raise HTTPException(status_code=404, detail="Saved request not found")

    if data.name is not None:
        saved.name = data.name
    if data.method is not None:
        saved.method = data.method
    if data.url is not None:
        saved.url = data.url
    if data.headers is not None:
        saved.headers = data.headers
    if data.body is not None:
        saved.body = data.body
    if data.query_params is not None:
        saved.query_params = data.query_params

    db.commit()
    db.refresh(saved)
    return saved


@router.delete("/requests/{request_id}")
def delete_saved_request(request_id: int, db: Session = Depends(get_db)):
    """Delete a saved request."""
    saved = db.query(SavedRequest).filter(SavedRequest.id == request_id).first()
    if not saved:
        raise HTTPException(status_code=404, detail="Saved request not found")

    db.delete(saved)
    db.commit()
    return {"message": "Saved request deleted", "id": request_id}


@router.post("/requests/{request_id}/execute", response_model=APIResponseOut)
async def execute_saved_request(request_id: int, db: Session = Depends(get_db)):
    """Execute a saved request and return the response."""
    saved = db.query(SavedRequest).filter(SavedRequest.id == request_id).first()
    if not saved:
        raise HTTPException(status_code=404, detail="Saved request not found")

    # Parse stored JSON strings back to dicts
    try:
        headers = json.loads(saved.headers) if saved.headers else {}
    except json.JSONDecodeError:
        headers = {}

    try:
        query_params = json.loads(saved.query_params) if saved.query_params else {}
    except json.JSONDecodeError:
        query_params = {}

    # Send the request
    response = await send_request(
        method=saved.method,
        url=saved.url,
        headers=headers,
        body=saved.body,
        query_params=query_params,
    )

    # Save to history
    sanitized_headers = parse_headers(headers)
    history_record = RequestHistory(
        method=saved.method.upper(),
        url=saved.url,
        headers=json.dumps(sanitized_headers),
        body=saved.body,
        query_params=json.dumps(query_params),
        status_code=response["status_code"],
        response_time_ms=response["response_time_ms"],
        response_headers=json.dumps(response["response_headers"]),
        response_body=response["response_body"],
        error_message=response["error_message"],
    )
    db.add(history_record)
    db.commit()
    db.refresh(history_record)

    return APIResponseOut(
        status_code=response["status_code"],
        response_time_ms=response["response_time_ms"],
        response_headers=response["response_headers"],
        response_body=response["response_body"],
        error_message=response["error_message"],
        history_id=history_record.id,
    )
