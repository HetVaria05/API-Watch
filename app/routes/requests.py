"""
routes/requests.py - API routes for sending and testing HTTP requests.

Handles the core API tester functionality:
- Sending HTTP requests to external APIs
- Running response assertions
- Saving results to history
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.models import RequestHistory
from app.schemas import APIRequestIn, APIResponseOut
from app.services.api_client import send_request, parse_headers
from app.services.validator import run_assertions

router = APIRouter(prefix="/api/requests", tags=["API Tester"])


@router.post("/send", response_model=APIResponseOut)
async def send_api_request(request_data: APIRequestIn, db: Session = Depends(get_db)):
    """
    Send an HTTP request and return the response.

    This is the main endpoint for the API tester. It:
    1. Sends the request using HTTPX
    2. Runs any provided assertions
    3. Saves the result to history
    4. Returns the response to the frontend
    """
    # Send the HTTP request
    response = await send_request(
        method=request_data.method,
        url=request_data.url,
        headers=request_data.headers,
        body=request_data.body,
        query_params=request_data.query_params,
    )

    # Run assertions if provided
    assertion_results = []
    test_result = ""
    if request_data.assertions:
        assertion_results = run_assertions(request_data.assertions, response)
        # Overall test result: PASS only if all assertions pass
        if assertion_results:
            all_passed = all(a["passed"] for a in assertion_results)
            test_result = "PASS" if all_passed else "FAIL"

    # Sanitize headers before storing in history
    sanitized_headers = parse_headers(request_data.headers)

    # Save to request history
    history_record = RequestHistory(
        method=request_data.method.upper(),
        url=request_data.url,
        headers=json.dumps(sanitized_headers),
        body=request_data.body,
        query_params=json.dumps(request_data.query_params),
        status_code=response["status_code"],
        response_time_ms=response["response_time_ms"],
        response_headers=json.dumps(response["response_headers"]),
        response_body=response["response_body"],
        error_message=response["error_message"],
        test_result=test_result,
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
        assertion_results=assertion_results,
        history_id=history_record.id,
    )
