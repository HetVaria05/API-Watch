"""
api_client.py - Service for sending HTTP requests to external APIs.

This is the core engine of APIWatch. It:
1. Validates the URL for safety (SSRF protection)
2. Sends the HTTP request using HTTPX
3. Measures response time in milliseconds
4. Returns structured response data

Security: Blocks requests to private/loopback/metadata addresses
to prevent Server-Side Request Forgery (SSRF) attacks.
"""

import httpx
import time
import json
import ipaddress
import socket
from urllib.parse import urlparse

# HTTP methods we support
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

# Request timeout in seconds
REQUEST_TIMEOUT = 30.0

# Maximum response body size to store (50KB)
MAX_RESPONSE_SIZE = 50_000


def is_safe_url(url: str) -> tuple[bool, str]:
    """
    Check if a URL is safe to request (not targeting internal/private networks).

    Returns (is_safe, reason) tuple.

    Security note: This blocks requests to:
    - Private IP ranges (10.x, 172.16-31.x, 192.168.x)
    - Loopback addresses (127.x, ::1)
    - Link-local addresses (169.254.x — cloud metadata)
    - IPv6 private ranges

    Exception: localhost is allowed for local development/testing.
    This exception is documented and should be removed in production.
    """
    try:
        parsed = urlparse(url)

        # Must have a scheme (http or https)
        if parsed.scheme not in ("http", "https"):
            return False, "Only HTTP and HTTPS URLs are allowed"

        # Must have a hostname
        hostname = parsed.hostname
        if not hostname:
            return False, "URL must include a hostname"

        # Allow localhost for local development/testing
        if hostname in ("localhost", "127.0.0.1", "::1"):
            return True, "localhost allowed for local testing"

        # Resolve hostname to IP and check if it's private
        try:
            addr_infos = socket.getaddrinfo(hostname, None)
            for addr_info in addr_infos:
                ip_str = addr_info[4][0]
                ip = ipaddress.ip_address(ip_str)

                # Block private, loopback, link-local, and reserved addresses
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False, f"Requests to private/internal addresses are blocked ({ip_str})"
        except socket.gaierror:
            # DNS resolution failed — URL might be invalid
            return False, f"Could not resolve hostname: {hostname}"

        return True, "URL is safe"

    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


def validate_method(method: str) -> tuple[bool, str]:
    """Validate that the HTTP method is supported."""
    method_upper = method.upper()
    if method_upper not in ALLOWED_METHODS:
        return False, f"Unsupported method: {method}. Allowed: {', '.join(ALLOWED_METHODS)}"
    return True, "Valid method"


def parse_headers(headers: dict) -> dict:
    """
    Parse and sanitize request headers.
    Filters out sensitive headers from being logged/stored.
    """
    # Headers that should not be stored in history
    sensitive_keys = {"authorization", "cookie", "set-cookie", "x-api-key", "api-key"}
    sanitized = {}
    for key, value in headers.items():
        if key.lower() in sensitive_keys:
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value
    return sanitized


async def send_request(
    method: str,
    url: str,
    headers: dict | None = None,
    body: str = "",
    query_params: dict | None = None,
) -> dict:
    """
    Send an HTTP request and return the response details.

    Args:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        url: Target URL
        headers: Optional custom headers
        body: Optional JSON request body (as string)
        query_params: Optional query parameters

    Returns:
        Dictionary with status_code, response_time_ms, response_headers,
        response_body, and error_message fields.
    """
    result = {
        "status_code": None,
        "response_time_ms": None,
        "response_headers": {},
        "response_body": "",
        "error_message": "",
    }

    # Validate the HTTP method
    method_valid, method_msg = validate_method(method)
    if not method_valid:
        result["error_message"] = method_msg
        return result

    # Validate URL safety (SSRF protection)
    url_safe, url_msg = is_safe_url(url)
    if not url_safe:
        result["error_message"] = url_msg
        return result

    # Prepare request parameters
    request_headers = headers or {}
    request_params = query_params or {}

    # Parse JSON body if provided
    json_body = None
    if body and body.strip():
        try:
            json_body = json.loads(body)
        except json.JSONDecodeError:
            result["error_message"] = "Invalid JSON in request body"
            return result

    try:
        # Send the request using HTTPX with timeout
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            # Measure response time
            start_time = time.perf_counter()

            response = await client.request(
                method=method.upper(),
                url=url,
                headers=request_headers,
                params=request_params,
                json=json_body,
            )

            end_time = time.perf_counter()
            response_time_ms = round((end_time - start_time) * 1000, 2)

            # Get response body (truncate if too large)
            response_text = response.text
            if len(response_text) > MAX_RESPONSE_SIZE:
                response_text = response_text[:MAX_RESPONSE_SIZE] + "\n... [truncated]"

            # Build result
            result["status_code"] = response.status_code
            result["response_time_ms"] = response_time_ms
            result["response_headers"] = dict(response.headers)
            result["response_body"] = response_text

    except httpx.TimeoutException:
        result["error_message"] = f"Request timed out after {REQUEST_TIMEOUT} seconds"
    except httpx.ConnectError:
        result["error_message"] = f"Could not connect to {url}"
    except httpx.TooManyRedirects:
        result["error_message"] = "Too many redirects (max 5)"
    except httpx.InvalidURL:
        result["error_message"] = f"Invalid URL format: {url}"
    except Exception as e:
        result["error_message"] = f"Request failed: {str(e)}"

    return result
