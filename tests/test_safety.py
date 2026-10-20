"""Unit tests for best-effort remote output filtering."""
from safety import screen_remote_text


def test_redacts_key_value_secrets():
    text = "api_key=abc123 password:my-password secret=hidden"
    result = screen_remote_text(text)
    assert "abc123" not in result
    assert "my-password" not in result
    assert "hidden" not in result
    assert result.count("[REDACTED]") == 3


def test_redacts_common_token_shapes():
    text = (
        "Bearer eyJhbGciOiJIUzI1NiJ9.signature "
        "sk-proj-abcdefghijklmnop "
        "ghp_abcdefghijklmnopqrstuvwx "
        "github_pat_abcdefghijklmnopqrstuvwxyz "
        "AKIA1234567890ABCDEF"
    )
    result = screen_remote_text(text)
    assert "eyJhbGci" not in result
    assert "sk-proj-" not in result
    assert "ghp_" not in result
    assert "github_pat_" not in result
    assert "AKIA1234567890ABCDEF" not in result


def test_preserves_normal_text():
    text = "The remote agent suggests checking the documentation."
    assert screen_remote_text(text) == text


def test_empty_text_is_supported():
    assert screen_remote_text("") == ""
