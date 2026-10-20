"""Tests for privacy-conscious audit logging."""
import json

import pytest

from audit_log import AuditLogError, write_audit_event


def test_writes_only_fixed_codes_and_timestamp(tmp_path, monkeypatch):
    path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("ADAM_AUDIT_LOG", str(path))

    write_audit_event("external_llm_request", "success", "request_completed")

    event = json.loads(path.read_text(encoding="utf-8"))
    assert event["action"] == "external_llm_request"
    assert event["outcome"] == "success"
    assert event["reason"] == "request_completed"
    assert "timestamp" in event
    assert set(event) == {"timestamp", "action", "outcome", "reason"}


def test_rejects_user_text_or_secret_as_event_code(tmp_path, monkeypatch):
    path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("ADAM_AUDIT_LOG", str(path))

    with pytest.raises(ValueError):
        write_audit_event("external_llm_request", "success", "my-secret-api-key")

    assert not path.exists()


def test_appends_multiple_events(tmp_path, monkeypatch):
    path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("ADAM_AUDIT_LOG", str(path))

    write_audit_event("owner_auth", "success", "authenticated")
    write_audit_event("owner_auth", "failure", "invalid_password")

    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_missing_parent_directory_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("ADAM_AUDIT_LOG", str(tmp_path / "missing" / "audit.jsonl"))

    with pytest.raises(AuditLogError):
        write_audit_event("owner_auth", "success", "authenticated")
