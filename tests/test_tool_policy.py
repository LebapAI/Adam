"""Tests for the default-deny MCP tool policy."""
from tool_policy import parse_tool_allowlist, tool_policy


def test_empty_allowlist_denies_every_tool():
    result = tool_policy({"name": "search_docs", "description": "Search documentation"}, set())
    assert result["allowed"] is False
    assert result["reason"] == "not explicitly allowlisted"


def test_exact_allowlist_allows_low_risk_tool_for_review_only():
    allowed = parse_tool_allowlist("search_docs, lookup_status")
    result = tool_policy(
        {"name": "search_docs", "description": "Search public documentation"},
        allowed,
    )
    assert result["allowed"] is True
    assert "execution is not implemented" in str(result["reason"])


def test_risky_tool_is_denied_even_if_allowlisted():
    result = tool_policy(
        {"name": "delete_file", "description": "Delete a file"},
        {"delete_file"},
    )
    assert result["allowed"] is False
    assert result["reason"] == "potentially sensitive capability"


def test_allowlist_is_exact_and_strips_whitespace():
    assert parse_tool_allowlist(" search_docs, ,lookup_status ") == {
        "search_docs",
        "lookup_status",
    }


def test_missing_name_is_denied():
    assert tool_policy({"description": "No name"}, set())["allowed"] is False
