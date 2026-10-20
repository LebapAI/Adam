"""Owner authentication helpers for the local CLI."""
import hmac


def verify_owner_password(expected_password: str, supplied_password: str) -> bool:
    """Compare the configured owner password without ordinary string equality."""
    if not expected_password or not supplied_password:
        return False
    return hmac.compare_digest(
        expected_password.encode("utf-8"),
        supplied_password.encode("utf-8"),
    )
