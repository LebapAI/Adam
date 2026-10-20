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

def test_risky_underscore_name_is_denied_even_with_allowlist():
    result = tool_policy(
        {"name": "delete_file", "description": "File operation"},
        {"delete_file"},
    )
    assert result["allowed"] is False
    assert result["reason"] == "potentially sensitive capability"



def test_non_string_tool_name_is_denied_without_crashing():
    result = tool_policy({"name": None, "description": "Search"}, {"search"})
    assert result["allowed"] is False
    assert result["reason"] == "missing or invalid tool name"


def test_non_mapping_tool_metadata_is_denied():
    result = tool_policy(None, {"search"})
    assert result["allowed"] is False
    assert result["reason"] == "invalid tool metadata"


def test_non_string_allowlist_setting_fails_closed():
    assert parse_tool_allowlist(None) == set()


def test_non_string_description_does_not_crash_or_grant_access():
    result = tool_policy({"name": "search_docs", "description": {"unexpected": "data"}}, {"search_docs"})
    assert result["allowed"] is True
    assert "execution is not implemented" in str(result["reason"])
