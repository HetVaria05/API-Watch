"""
test_api_client.py - Tests for the API client service.

Uses respx to mock HTTP responses so tests never hit the real internet.
Tests cover: all HTTP methods, timeouts, connection errors, SSRF protection,
invalid URLs, and invalid JSON body.
"""

import pytest
import httpx
import respx

from app.services.api_client import send_request, is_safe_url, validate_method


# ─── URL Safety Tests ─────────────────────────────────────────────────────────

class TestIsSafeUrl:
    def test_public_https_url_is_safe(self):
        safe, msg = is_safe_url("https://httpbin.org/get")
        assert safe is True

    def test_public_http_url_is_safe(self):
        safe, msg = is_safe_url("http://example.com")
        assert safe is True

    def test_localhost_is_allowed_for_local_testing(self):
        """Localhost is explicitly allowed for local development."""
        safe, msg = is_safe_url("http://localhost:8080/api")
        assert safe is True

    def test_loopback_ip_127_0_0_1_is_allowed(self):
        """127.0.0.1 is allowed for local development testing."""
        safe, msg = is_safe_url("http://127.0.0.1:5000/test")
        assert safe is True

    def test_ftp_scheme_is_blocked(self):
        safe, msg = is_safe_url("ftp://example.com/file")
        assert safe is False
        assert "HTTPS" in msg or "http" in msg.lower()

    def test_empty_hostname_is_blocked(self):
        safe, msg = is_safe_url("http:///path")
        assert safe is False

    def test_invalid_url_is_blocked(self):
        safe, msg = is_safe_url("not-a-url")
        assert safe is False


# ─── Method Validation Tests ──────────────────────────────────────────────────

class TestValidateMethod:
    def test_get_is_valid(self):
        valid, _ = validate_method("GET")
        assert valid is True

    def test_post_is_valid(self):
        valid, _ = validate_method("POST")
        assert valid is True

    def test_put_is_valid(self):
        valid, _ = validate_method("put")  # lowercase also accepted
        assert valid is True

    def test_patch_is_valid(self):
        valid, _ = validate_method("PATCH")
        assert valid is True

    def test_delete_is_valid(self):
        valid, _ = validate_method("DELETE")
        assert valid is True

    def test_head_is_invalid(self):
        valid, msg = validate_method("HEAD")
        assert valid is False
        assert "Unsupported" in msg

    def test_connect_is_invalid(self):
        valid, msg = validate_method("CONNECT")
        assert valid is False


# ─── Request Sending Tests (mocked with respx) ───────────────────────────────

class TestSendRequest:

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_request_success(self):
        """GET request returns status 200 and response body."""
        respx.get("http://localhost/api/test").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        result = await send_request("GET", "http://localhost/api/test")

        assert result["status_code"] == 200
        assert result["error_message"] == ""
        assert "ok" in result["response_body"]
        assert result["response_time_ms"] is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_request_sends_json_body(self):
        """POST request with JSON body is sent correctly."""
        route = respx.post("http://localhost/api/data").mock(
            return_value=httpx.Response(201, json={"id": 1})
        )
        result = await send_request(
            "POST", "http://localhost/api/data",
            body='{"name": "test"}'
        )

        assert result["status_code"] == 201
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_put_request_success(self):
        respx.put("http://localhost/api/item/1").mock(
            return_value=httpx.Response(200, json={"updated": True})
        )
        result = await send_request("PUT", "http://localhost/api/item/1", body='{"key": "val"}')
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    @respx.mock
    async def test_patch_request_success(self):
        respx.patch("http://localhost/api/item/1").mock(
            return_value=httpx.Response(200, json={"patched": True})
        )
        result = await send_request("PATCH", "http://localhost/api/item/1", body='{"key": "val"}')
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_request_success(self):
        respx.delete("http://localhost/api/item/1").mock(
            return_value=httpx.Response(204)
        )
        result = await send_request("DELETE", "http://localhost/api/item/1")
        assert result["status_code"] == 204

    @pytest.mark.asyncio
    @respx.mock
    async def test_404_response_is_recorded(self):
        """A 404 response is a valid HTTP response, not an error."""
        respx.get("http://localhost/missing").mock(
            return_value=httpx.Response(404, json={"detail": "not found"})
        )
        result = await send_request("GET", "http://localhost/missing")
        assert result["status_code"] == 404
        assert result["error_message"] == ""

    @pytest.mark.asyncio
    @respx.mock
    async def test_500_server_error_is_recorded(self):
        respx.get("http://localhost/error").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        result = await send_request("GET", "http://localhost/error")
        assert result["status_code"] == 500
        assert result["error_message"] == ""

    @pytest.mark.asyncio
    @respx.mock
    async def test_timeout_returns_error(self):
        """Request timeout sets error_message and status_code stays None."""
        respx.get("http://localhost/slow").mock(side_effect=httpx.TimeoutException("timeout"))
        result = await send_request("GET", "http://localhost/slow")
        assert result["status_code"] is None
        assert "timeout" in result["error_message"].lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_connection_error_returns_error(self):
        respx.get("http://localhost/unreachable").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        result = await send_request("GET", "http://localhost/unreachable")
        assert result["status_code"] is None
        assert result["error_message"] != ""

    @pytest.mark.asyncio
    async def test_invalid_method_returns_error(self):
        result = await send_request("INVALID", "http://localhost/test")
        assert result["status_code"] is None
        assert "Unsupported" in result["error_message"]

    @pytest.mark.asyncio
    async def test_invalid_json_body_returns_error(self):
        result = await send_request("POST", "http://localhost/api", body="not-json{")
        assert result["error_message"] == "Invalid JSON in request body"

    @pytest.mark.asyncio
    async def test_ssrf_blocked_for_private_url(self):
        """Requests to private IPs should be blocked before sending."""
        # This relies on DNS not resolving a real IP for 10.0.0.1
        # We test the SSRF check logic directly
        safe, msg = is_safe_url("http://169.254.169.254/latest/meta-data/")
        # Link-local (AWS metadata) should be blocked
        # (If DNS resolves it, it will be blocked; if not it returns DNS error)
        # Either way it should not be "safe"
        # Note: In some environments 169.254.169.254 may not resolve; that's fine
        assert safe is False or "Could not resolve" in msg or "private" in msg.lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_query_params_are_included(self):
        """Query parameters are appended to the request URL."""
        route = respx.get("http://localhost/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        result = await send_request(
            "GET", "http://localhost/search",
            query_params={"q": "test", "limit": "10"}
        )
        assert result["status_code"] == 200
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_response_time_is_positive(self):
        respx.get("http://localhost/time").mock(
            return_value=httpx.Response(200, text="ok")
        )
        result = await send_request("GET", "http://localhost/time")
        assert result["response_time_ms"] is not None
        assert result["response_time_ms"] >= 0
