"""Tests for A2A URL trust-boundary validation."""
import pytest

from a2a_client import _https_origin, _validate_endpoint


def test_allows_same_https_origin():
    assert _validate_endpoint(
        "https://agent.example/.well-known/agent.json",
        "https://agent.example/tasks",
    ) == "https://agent.example/tasks"


def test_normalizes_default_https_port():
    assert _validate_endpoint(
        "https://agent.example/card",
        "https://agent.example:443/tasks",
    ) == "https://agent.example:443/tasks"


def test_rejects_different_origin():
    with pytest.raises(ValueError, match="same HTTPS origin"):
        _validate_endpoint(
            "https://agent.example/card",
            "https://attacker.example/collect",
        )


def test_rejects_http_url():
    with pytest.raises(ValueError, match="valid HTTPS URL"):
        _https_origin("http://agent.example/card")


def test_rejects_embedded_credentials():
    with pytest.raises(ValueError, match="without embedded credentials"):
        _https_origin("https://user:password@agent.example/card")


def test_rejects_empty_endpoint():
    with pytest.raises(ValueError, match="valid HTTPS"):
        _validate_endpoint("https://agent.example/card", "")
