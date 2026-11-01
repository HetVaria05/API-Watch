"""
test_validator.py - Tests for the response assertion validator.

Tests all 5 assertion types:
- status_code
- body_contains
- json_key
- json_value
- response_time
"""

import pytest
from app.services.validator import (
    run_assertions, check_status_code, check_body_contains,
    check_json_key, check_json_value, check_response_time,
)

# A sample response to run assertions against
SAMPLE_RESPONSE = {
    "status_code": 200,
    "response_time_ms": 120.5,
    "response_body": '{"name": "Alice", "age": 30, "active": true, "data": {"city": "Mumbai"}}',
    "response_headers": {},
    "error_message": "",
}


class TestStatusCodeAssertion:
    def test_matching_status_code_passes(self):
        result = check_status_code("200", SAMPLE_RESPONSE)
        assert result["passed"] is True

    def test_non_matching_status_code_fails(self):
        result = check_status_code("404", SAMPLE_RESPONSE)
        assert result["passed"] is False

    def test_non_numeric_expected_fails_gracefully(self):
        result = check_status_code("ok", SAMPLE_RESPONSE)
        assert result["passed"] is False
        assert "number" in result["message"].lower()

    def test_none_status_code_fails(self):
        response = {**SAMPLE_RESPONSE, "status_code": None}
        result = check_status_code("200", response)
        assert result["passed"] is False


class TestBodyContainsAssertion:
    def test_text_present_in_body_passes(self):
        result = check_body_contains("Alice", SAMPLE_RESPONSE)
        assert result["passed"] is True

    def test_text_absent_from_body_fails(self):
        result = check_body_contains("not-present-xyz", SAMPLE_RESPONSE)
        assert result["passed"] is False

    def test_partial_match_passes(self):
        result = check_body_contains("name", SAMPLE_RESPONSE)
        assert result["passed"] is True


class TestJsonKeyAssertion:
    def test_top_level_key_exists_passes(self):
        result = check_json_key("name", SAMPLE_RESPONSE)
        assert result["passed"] is True

    def test_missing_key_fails(self):
        result = check_json_key("email", SAMPLE_RESPONSE)
        assert result["passed"] is False

    def test_nested_key_dot_notation_passes(self):
        result = check_json_key("data.city", SAMPLE_RESPONSE)
        assert result["passed"] is True

    def test_nested_key_missing_fails(self):
        result = check_json_key("data.country", SAMPLE_RESPONSE)
        assert result["passed"] is False

    def test_non_json_response_fails_gracefully(self):
        response = {**SAMPLE_RESPONSE, "response_body": "plain text"}
        result = check_json_key("name", response)
        assert result["passed"] is False
        assert "not valid JSON" in result["message"]


class TestJsonValueAssertion:
    def test_correct_value_passes(self):
        result = check_json_value("name", "Alice", SAMPLE_RESPONSE)
        assert result["passed"] is True

    def test_wrong_value_fails(self):
        result = check_json_value("name", "Bob", SAMPLE_RESPONSE)
        assert result["passed"] is False

    def test_numeric_value_matches_as_string(self):
        result = check_json_value("age", "30", SAMPLE_RESPONSE)
        assert result["passed"] is True

    def test_nested_key_value_passes(self):
        result = check_json_value("data.city", "Mumbai", SAMPLE_RESPONSE)
        assert result["passed"] is True

    def test_missing_key_fails_gracefully(self):
        result = check_json_value("email", "test@test.com", SAMPLE_RESPONSE)
        assert result["passed"] is False
        assert "not found" in result["message"]

    def test_non_json_response_fails_gracefully(self):
        response = {**SAMPLE_RESPONSE, "response_body": "not json"}
        result = check_json_value("name", "Alice", response)
        assert result["passed"] is False


class TestResponseTimeAssertion:
    def test_response_within_limit_passes(self):
        result = check_response_time("500", SAMPLE_RESPONSE)
        assert result["passed"] is True

    def test_response_over_limit_fails(self):
        result = check_response_time("100", SAMPLE_RESPONSE)  # 120.5ms > 100ms
        assert result["passed"] is False

    def test_exact_limit_passes(self):
        result = check_response_time("120.5", SAMPLE_RESPONSE)
        assert result["passed"] is True

    def test_non_numeric_expected_fails_gracefully(self):
        result = check_response_time("fast", SAMPLE_RESPONSE)
        assert result["passed"] is False

    def test_no_response_time_fails_gracefully(self):
        response = {**SAMPLE_RESPONSE, "response_time_ms": None}
        result = check_response_time("500", response)
        assert result["passed"] is False
        assert "No response time" in result["message"]


class TestRunAssertions:
    def test_all_assertions_pass_returns_all_true(self):
        assertions = [
            {"type": "status_code", "expected": "200"},
            {"type": "body_contains", "expected": "Alice"},
        ]
        results = run_assertions(assertions, SAMPLE_RESPONSE)
        assert len(results) == 2
        assert all(r["passed"] for r in results)

    def test_mixed_assertions_returns_correct_results(self):
        assertions = [
            {"type": "status_code", "expected": "200"},     # PASS
            {"type": "status_code", "expected": "404"},     # FAIL
        ]
        results = run_assertions(assertions, SAMPLE_RESPONSE)
        assert results[0]["passed"] is True
        assert results[1]["passed"] is False

    def test_unknown_assertion_type_handled(self):
        assertions = [{"type": "unknown_type", "expected": "value"}]
        results = run_assertions(assertions, SAMPLE_RESPONSE)
        assert len(results) == 1
        assert results[0]["passed"] is False

    def test_empty_assertions_returns_empty(self):
        results = run_assertions([], SAMPLE_RESPONSE)
        assert results == []
