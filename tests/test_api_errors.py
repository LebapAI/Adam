"""Tests for safe HTTP error diagnostics."""
from api_errors import http_status_hint


def test_auth_error_hint_does_not_request_secret_disclosure():
    hint = http_status_hint(401)
    assert "LLM_API_KEY" in hint
    assert "Do not share the key" in hint


def test_model_not_found_hint():
    hint = http_status_hint(404)
    assert "LLM_BASE_URL" in hint
    assert "LLM_MODEL" in hint


def test_quota_hint():
    assert "quota" in http_status_hint(429).lower()


def test_server_error_hint():
    assert "server error" in http_status_hint(503).lower()


def test_unknown_status_uses_safe_generic_hint():
    assert http_status_hint(418) == "The provider rejected the request (HTTP 418). Check the API configuration."
