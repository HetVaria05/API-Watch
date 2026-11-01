"""
test_routes.py - Integration tests for all FastAPI routes.

Uses the TestClient with an in-memory database (from conftest.py).
Tests CRUD operations for history, collections, monitoring,
and the request sender route.
"""

import pytest
import httpx
import respx


# ─── Health Check ─────────────────────────────────────────────────────────────

def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


# ─── Request Sender Route ─────────────────────────────────────────────────────

class TestRequestSenderRoute:

    @respx.mock
    def test_send_get_request_success(self, client):
        """Sending a GET request records history and returns a response."""
        respx.get("http://localhost/api/hello").mock(
            return_value=httpx.Response(200, json={"message": "hello"})
        )
        res = client.post("/api/requests/send", json={
            "method": "GET",
            "url": "http://localhost/api/hello",
            "headers": {},
            "body": "",
            "query_params": {},
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status_code"] == 200
        assert data["history_id"] is not None

    @respx.mock
    def test_send_post_request_with_assertions(self, client):
        """POST request with assertions runs them and returns results."""
        respx.post("http://localhost/api/create").mock(
            return_value=httpx.Response(201, json={"id": 42})
        )
        res = client.post("/api/requests/send", json={
            "method": "POST",
            "url": "http://localhost/api/create",
            "headers": {},
            "body": '{"name": "test"}',
            "query_params": {},
            "assertions": [
                {"type": "status_code", "expected": "201"},
                {"type": "json_key", "expected": "id"},
            ],
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status_code"] == 201
        assert len(data["assertion_results"]) == 2
        assert all(a["passed"] for a in data["assertion_results"])

    def test_send_request_with_invalid_method(self, client):
        """Invalid HTTP method returns a response with error_message."""
        res = client.post("/api/requests/send", json={
            "method": "INVALID",
            "url": "http://localhost/api/test",
            "headers": {},
            "body": "",
            "query_params": {},
        })
        assert res.status_code == 200
        data = res.json()
        assert data["error_message"] != ""
        assert data["status_code"] is None


# ─── History Routes ───────────────────────────────────────────────────────────

class TestHistoryRoutes:

    @respx.mock
    def test_history_is_saved_after_request(self, client):
        respx.get("http://localhost/api/check").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        # Send a request to create history
        client.post("/api/requests/send", json={
            "method": "GET",
            "url": "http://localhost/api/check",
            "headers": {},
            "body": "",
            "query_params": {},
        })

        # Check history is recorded
        res = client.get("/api/history/")
        assert res.status_code == 200
        history = res.json()
        assert len(history) >= 1
        assert history[0]["url"] == "http://localhost/api/check"

    def test_get_history_detail(self, client):
        """Can fetch details of a specific history record."""
        # First create a history record
        from app.models import RequestHistory
        from datetime import datetime, timezone

        # We need to add one directly since we can't easily mock respx here
        # Use the route which will create a real error record
        client.post("/api/requests/send", json={
            "method": "INVALID",
            "url": "http://localhost/x",
            "headers": {},
            "body": "",
            "query_params": {},
        })
        res = client.get("/api/history/")
        assert res.status_code == 200
        history = res.json()
        if len(history) > 0:
            record_id = history[0]["id"]
            detail = client.get(f"/api/history/{record_id}")
            assert detail.status_code == 200
            assert detail.json()["id"] == record_id

    def test_get_history_detail_not_found(self, client):
        res = client.get("/api/history/99999")
        assert res.status_code == 404

    def test_delete_history_record(self, client):
        # Create a record
        client.post("/api/requests/send", json={
            "method": "INVALID",
            "url": "http://localhost/del-test",
            "headers": {},
            "body": "",
            "query_params": {},
        })
        history = client.get("/api/history/").json()
        if len(history) > 0:
            record_id = history[0]["id"]
            res = client.delete(f"/api/history/{record_id}")
            assert res.status_code == 200
            # Verify it's gone
            res2 = client.get(f"/api/history/{record_id}")
            assert res2.status_code == 404

    def test_history_filter_by_method(self, client):
        res = client.get("/api/history/?method=GET")
        assert res.status_code == 200

    def test_history_search_by_url(self, client):
        res = client.get("/api/history/?search=localhost")
        assert res.status_code == 200
        for record in res.json():
            assert "localhost" in record["url"]


# ─── Collection Routes ────────────────────────────────────────────────────────

class TestCollectionRoutes:

    def test_create_collection(self, client):
        res = client.post("/api/collections/", json={
            "name": "My Tests",
            "description": "Test collection"
        })
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "My Tests"
        assert data["id"] is not None

    def test_list_collections(self, client):
        client.post("/api/collections/", json={"name": "Col A"})
        res = client.get("/api/collections/")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_get_collection_by_id(self, client):
        created = client.post("/api/collections/", json={"name": "Col B"}).json()
        res = client.get(f"/api/collections/{created['id']}")
        assert res.status_code == 200
        assert res.json()["name"] == "Col B"

    def test_get_collection_not_found(self, client):
        res = client.get("/api/collections/99999")
        assert res.status_code == 404

    def test_update_collection(self, client):
        created = client.post("/api/collections/", json={"name": "Old Name"}).json()
        res = client.put(f"/api/collections/{created['id']}", json={"name": "New Name"})
        assert res.status_code == 200
        assert res.json()["name"] == "New Name"

    def test_delete_collection(self, client):
        created = client.post("/api/collections/", json={"name": "To Delete"}).json()
        res = client.delete(f"/api/collections/{created['id']}")
        assert res.status_code == 200
        # Verify it's gone
        res2 = client.get(f"/api/collections/{created['id']}")
        assert res2.status_code == 404

    def test_create_saved_request_in_collection(self, client):
        collection = client.post("/api/collections/", json={"name": "API Tests"}).json()
        res = client.post("/api/collections/requests", json={
            "name": "Get Users",
            "method": "GET",
            "url": "http://localhost/api/users",
            "headers": "{}",
            "body": "",
            "query_params": "{}",
            "collection_id": collection["id"],
        })
        assert res.status_code == 201
        assert res.json()["name"] == "Get Users"

    def test_create_saved_request_invalid_collection(self, client):
        res = client.post("/api/collections/requests", json={
            "name": "Test",
            "method": "GET",
            "url": "http://localhost/x",
            "headers": "{}",
            "body": "",
            "query_params": "{}",
            "collection_id": 99999,
        })
        assert res.status_code == 404

    def test_delete_saved_request(self, client):
        collection = client.post("/api/collections/", json={"name": "Delete Test"}).json()
        saved = client.post("/api/collections/requests", json={
            "name": "To Remove",
            "method": "DELETE",
            "url": "http://localhost/api/del",
            "headers": "{}",
            "body": "",
            "query_params": "{}",
            "collection_id": collection["id"],
        }).json()

        res = client.delete(f"/api/collections/requests/{saved['id']}")
        assert res.status_code == 200


# ─── Monitoring Routes ────────────────────────────────────────────────────────

class TestMonitoringRoutes:

    def test_create_monitored_endpoint(self, client):
        res = client.post("/api/monitoring/endpoints", json={
            "name": "My API",
            "url": "http://localhost/health",
            "method": "GET",
            "expected_status": 200,
        })
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "My API"
        assert data["uptime_percentage"] is None  # No checks yet

    def test_list_monitored_endpoints(self, client):
        client.post("/api/monitoring/endpoints", json={
            "name": "Test Endpoint",
            "url": "http://localhost/test",
        })
        res = client.get("/api/monitoring/endpoints")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_delete_monitored_endpoint(self, client):
        created = client.post("/api/monitoring/endpoints", json={
            "name": "Remove Me",
            "url": "http://localhost/bye",
        }).json()
        res = client.delete(f"/api/monitoring/endpoints/{created['id']}")
        assert res.status_code == 200

    def test_delete_nonexistent_endpoint(self, client):
        res = client.delete("/api/monitoring/endpoints/99999")
        assert res.status_code == 404

    @respx.mock
    def test_manual_check_records_result(self, client):
        """Running a manual check saves a MonitoringCheck record."""
        endpoint = client.post("/api/monitoring/endpoints", json={
            "name": "Health Check",
            "url": "http://localhost/health",
            "expected_status": 200,
        }).json()

        respx.get("http://localhost/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )

        res = client.post(f"/api/monitoring/endpoints/{endpoint['id']}/check")
        assert res.status_code == 200
        check = res.json()
        assert check["status_code"] == 200
        assert check["is_up"] is True


# ─── Reports Routes ───────────────────────────────────────────────────────────

class TestReportsRoutes:

    def test_summary_returns_stats(self, client):
        res = client.get("/api/reports/summary")
        assert res.status_code == 200
        data = res.json()
        assert "total_requests" in data
        assert "successful_requests" in data
        assert "failed_requests" in data

    def test_csv_download_returns_csv(self, client):
        res = client.get("/api/reports/csv")
        assert res.status_code == 200
        assert "text/csv" in res.headers.get("content-type", "")
        assert "ID" in res.text  # CSV header row

    def test_dashboard_returns_combined_stats(self, client):
        res = client.get("/api/reports/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert "total_requests" in data
        assert "recent_history" in data


# ─── Monitoring Calculation Tests ─────────────────────────────────────────────

class TestUptimeCalculation:

    def test_uptime_100_percent(self, db):
        """All checks successful = 100% uptime."""
        from app.models import MonitoredEndpoint, MonitoringCheck
        from app.services.monitor import calculate_uptime

        ep = MonitoredEndpoint(name="Test", url="http://localhost/x", method="GET", expected_status=200)
        db.add(ep)
        db.commit()
        db.refresh(ep)

        for _ in range(5):
            db.add(MonitoringCheck(endpoint_id=ep.id, status_code=200, is_up=True))
        db.commit()

        uptime = calculate_uptime(ep.id, db)
        assert uptime == 100.0

    def test_uptime_50_percent(self, db):
        """Half checks successful = 50% uptime."""
        from app.models import MonitoredEndpoint, MonitoringCheck
        from app.services.monitor import calculate_uptime

        ep = MonitoredEndpoint(name="Half", url="http://localhost/half", method="GET", expected_status=200)
        db.add(ep)
        db.commit()
        db.refresh(ep)

        for i in range(4):
            db.add(MonitoringCheck(endpoint_id=ep.id, status_code=200, is_up=(i < 2)))
        db.commit()

        uptime = calculate_uptime(ep.id, db)
        assert uptime == 50.0

    def test_uptime_none_when_no_checks(self, db):
        """No checks = None uptime."""
        from app.models import MonitoredEndpoint
        from app.services.monitor import calculate_uptime

        ep = MonitoredEndpoint(name="New", url="http://localhost/new", method="GET", expected_status=200)
        db.add(ep)
        db.commit()
        db.refresh(ep)

        uptime = calculate_uptime(ep.id, db)
        assert uptime is None


# ─── Report Generation Tests ──────────────────────────────────────────────────

class TestReportGeneration:

    def test_csv_contains_header_row(self, db):
        from app.services.report_generator import generate_csv_report
        csv = generate_csv_report(db)
        assert "ID" in csv
        assert "Method" in csv
        assert "URL" in csv
        assert "Status Code" in csv

    def test_csv_contains_history_data(self, db):
        from app.models import RequestHistory
        from app.services.report_generator import generate_csv_report

        record = RequestHistory(
            method="GET", url="http://test.com/api",
            status_code=200, response_time_ms=55.5
        )
        db.add(record)
        db.commit()

        csv = generate_csv_report(db)
        assert "GET" in csv
        assert "http://test.com/api" in csv

    def test_summary_stats_with_no_data(self, db):
        from app.services.report_generator import get_summary_statistics
        stats = get_summary_statistics(db)
        assert stats["total_requests"] == 0
        assert stats["average_response_time_ms"] is None

    def test_summary_stats_counts_correctly(self, db):
        from app.models import RequestHistory
        from app.services.report_generator import get_summary_statistics

        db.add(RequestHistory(method="GET", url="http://a.com", status_code=200, response_time_ms=100))
        db.add(RequestHistory(method="GET", url="http://b.com", status_code=200, response_time_ms=200))
        db.add(RequestHistory(method="POST", url="http://c.com", status_code=500, response_time_ms=50))
        db.commit()

        stats = get_summary_statistics(db)
        assert stats["total_requests"] == 3
        assert stats["successful_requests"] == 2
        assert stats["failed_requests"] == 1
        assert stats["average_response_time_ms"] == round((100 + 200 + 50) / 3, 2)
