"""Tests for explicit authorization confirmation."""
import pytest

from authorization import confirmation_granted, confirmation_phrase


@pytest.mark.parametrize("action", ["send_to_llm", "send_to_a2a"])
def test_external_transmission_requires_exact_send_confirmation(action):
    assert confirmation_granted(action, "SEND")
    assert not confirmation_granted(action, "yes")
    assert not confirmation_granted(action, "send")
    assert not confirmation_granted(action, "")


def test_starting_mcp_requires_exact_start_confirmation():
    assert confirmation_phrase("start_mcp_server") == "START"
    assert confirmation_granted("start_mcp_server", "START")
    assert not confirmation_granted("start_mcp_server", "SEND")


def test_unknown_action_fails_closed():
    assert not confirmation_granted("delete_everything", "YES")
    with pytest.raises(ValueError):
        confirmation_phrase("delete_everything")
