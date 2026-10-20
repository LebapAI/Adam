"""Tests for owner authentication."""
from owner_auth import verify_owner_password


def test_accepts_correct_password():
    assert verify_owner_password("correct horse battery staple", "correct horse battery staple")


def test_rejects_wrong_password():
    assert not verify_owner_password("correct-password", "wrong-password")


def test_rejects_missing_passwords():
    assert not verify_owner_password("", "anything")
    assert not verify_owner_password("configured", "")
