"""Tests for A2A URL and response trust-boundary validation."""

import pytest

from a2a_client import (
    MAX_TASK_CHARS,
    _https_origin,
    _parse_https_url,
    _validate_endpoint,
)


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
    with pytest.raises(ValueError, match="without credentials"):
        _https_origin("https://user:password@agent.example/card")


def test_rejects_url_fragment():
    with pytest.raises(ValueError, match="fragments"):
        _parse_https_url("https://agent.example/card#fragment")


def test_rejects_empty_endpoint():
    with pytest.raises(ValueError, match="valid HTTPS"):
        _validate_endpoint("https://agent.example/card", "")


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost/agent-card",
        "https://service.localhost/agent-card",
        "https://127.0.0.1/agent-card",
        "https://192.168.1.20/agent-card",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/agent-card",
    ],
)
def test_rejects_local_or_non_public_hosts(url):
    with pytest.raises(ValueError):
        _https_origin(url)


def test_task_limit_is_finite():
    assert MAX_TASK_CHARS == 12_000
