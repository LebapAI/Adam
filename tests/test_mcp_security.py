"""Tests for MCP command validation and child environment isolation."""

import pytest

from mcp_client import _child_environment, _validate_command


@pytest.mark.parametrize("command", [[], ["python", "bad\x00arg"], ["python", 12]])
def test_rejects_invalid_command(command):
    with pytest.raises(ValueError):
        _validate_command(command)


def test_rejects_excessive_command_arguments():
    with pytest.raises(ValueError, match="too many"):
        _validate_command(["python"] * 65)


def test_accepts_normal_argument_list():
    assert _validate_command(["python", "-m", "example"]) == [
        "python",
        "-m",
        "example",
    ]


def test_child_environment_excludes_adam_secrets(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("ADAM_OWNER_PASSWORD", "do-not-forward")
    monkeypatch.setenv("LLM_API_KEY", "do-not-forward")
    monkeypatch.setenv("A2A_BEARER_TOKEN", "do-not-forward")
    monkeypatch.setenv("MCP_SERVER_ENV_ALLOWLIST", "CUSTOM_MCP_KEY")
    monkeypatch.setenv("CUSTOM_MCP_KEY", "dedicated-tool-key")

    env = _child_environment()

    assert env["PATH"] == "/usr/bin"
    assert env["CUSTOM_MCP_KEY"] == "dedicated-tool-key"
    assert "ADAM_OWNER_PASSWORD" not in env
    assert "LLM_API_KEY" not in env
    assert "A2A_BEARER_TOKEN" not in env


def test_invalid_environment_allowlist_names_are_ignored(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_ENV_ALLOWLIST", "BAD-NAME, ADAM_OWNER_PASSWORD")
    monkeypatch.setenv("ADAM_OWNER_PASSWORD", "secret")

    assert "BAD-NAME" not in _child_environment()
    assert "ADAM_OWNER_PASSWORD" not in _child_environment()
