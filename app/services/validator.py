"""
validator.py - Response validation service.

Runs user-defined assertions against API responses.
Supports checking:
- HTTP status code
- Response body contains text
- JSON key exists
- JSON key has expected value
- Response time is within limit
"""

import json


def run_assertions(assertions: list[dict], response_data: dict) -> list[dict]:
    """
    Run a list of assertions against the API response.

    Args:
        assertions: List of assertion dicts with 'type', 'expected', and optional 'key'
        response_data: The API response dict with status_code, response_body, response_time_ms

    Returns:
        List of result dicts with 'type', 'expected', 'actual', 'passed', and 'message'
    """
    results = []

    for assertion in assertions:
        assertion_type = assertion.get("type", "")
        expected = assertion.get("expected", "")
        key = assertion.get("key", "")

        result = {
            "type": assertion_type,
            "expected": expected,
            "actual": "",
            "passed": False,
            "message": "",
        }

        try:
            if assertion_type == "status_code":
                result = check_status_code(expected, response_data)

            elif assertion_type == "body_contains":
                result = check_body_contains(expected, response_data)

            elif assertion_type == "json_key":
                result = check_json_key(expected, response_data)

            elif assertion_type == "json_value":
                result = check_json_value(key, expected, response_data)

            elif assertion_type == "response_time":
                result = check_response_time(expected, response_data)

            else:
                result["message"] = f"Unknown assertion type: {assertion_type}"

        except Exception as e:
            result["message"] = f"Assertion error: {str(e)}"

        results.append(result)

    return results


def check_status_code(expected: str, response_data: dict) -> dict:
    """Check if the response status code matches the expected value."""
    try:
        expected_code = int(expected)
    except ValueError:
        return {
            "type": "status_code",
            "expected": expected,
            "actual": "",
            "passed": False,
            "message": f"Expected status code must be a number, got: {expected}",
        }

    actual_code = response_data.get("status_code")
    passed = actual_code == expected_code

    return {
        "type": "status_code",
        "expected": str(expected_code),
        "actual": str(actual_code) if actual_code is not None else "N/A",
        "passed": passed,
        "message": "Status code matches" if passed else f"Expected {expected_code}, got {actual_code}",
    }


def check_body_contains(expected: str, response_data: dict) -> dict:
    """Check if the response body contains the expected text."""
    body = response_data.get("response_body", "")
    passed = expected in body

    return {
        "type": "body_contains",
        "expected": expected,
        "actual": f"{'Found' if passed else 'Not found'} in response body",
        "passed": passed,
        "message": "Text found in response" if passed else f"Text '{expected}' not found in response body",
    }


def check_json_key(expected_key: str, response_data: dict) -> dict:
    """Check if a JSON key exists in the response body."""
    body = response_data.get("response_body", "")

    try:
        json_data = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return {
            "type": "json_key",
            "expected": expected_key,
            "actual": "Response is not valid JSON",
            "passed": False,
            "message": "Cannot check JSON key — response is not valid JSON",
        }

    # Support nested keys with dot notation (e.g., "data.name")
    passed = _key_exists(json_data, expected_key)

    return {
        "type": "json_key",
        "expected": expected_key,
        "actual": f"Key {'exists' if passed else 'not found'}",
        "passed": passed,
        "message": f"Key '{expected_key}' {'found' if passed else 'not found'} in response",
    }


def check_json_value(key: str, expected_value: str, response_data: dict) -> dict:
    """Check if a JSON key has the expected value."""
    body = response_data.get("response_body", "")

    try:
        json_data = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return {
            "type": "json_value",
            "expected": f"{key}={expected_value}",
            "actual": "Response is not valid JSON",
            "passed": False,
            "message": "Cannot check JSON value — response is not valid JSON",
        }

    actual_value = _get_value(json_data, key)

    if actual_value is None:
        return {
            "type": "json_value",
            "expected": f"{key}={expected_value}",
            "actual": f"Key '{key}' not found",
            "passed": False,
            "message": f"Key '{key}' not found in response JSON",
        }

    # Compare as strings for simplicity
    passed = str(actual_value) == str(expected_value)

    return {
        "type": "json_value",
        "expected": f"{key}={expected_value}",
        "actual": f"{key}={actual_value}",
        "passed": passed,
        "message": f"Value matches" if passed else f"Expected {key}={expected_value}, got {key}={actual_value}",
    }


def check_response_time(expected: str, response_data: dict) -> dict:
    """Check if response time is within the expected maximum (in ms)."""
    try:
        max_time = float(expected)
    except ValueError:
        return {
            "type": "response_time",
            "expected": expected,
            "actual": "",
            "passed": False,
            "message": f"Expected response time must be a number, got: {expected}",
        }

    actual_time = response_data.get("response_time_ms")
    if actual_time is None:
        return {
            "type": "response_time",
            "expected": f"≤ {max_time}ms",
            "actual": "N/A",
            "passed": False,
            "message": "No response time recorded (request may have failed)",
        }

    passed = actual_time <= max_time

    return {
        "type": "response_time",
        "expected": f"≤ {max_time}ms",
        "actual": f"{actual_time}ms",
        "passed": passed,
        "message": f"Response time OK ({actual_time}ms)" if passed else f"Too slow: {actual_time}ms > {max_time}ms",
    }


def _key_exists(data, key: str) -> bool:
    """Check if a key exists in a dict, supporting dot notation for nesting."""
    parts = key.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
                current = current[index]
            except (ValueError, IndexError):
                return False
        else:
            return False
    return True


def _get_value(data, key: str):
    """Get a value from a dict using dot notation."""
    parts = key.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
                current = current[index]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current
