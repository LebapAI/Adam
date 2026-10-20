"""Safe, actionable hints for HTTP errors from external LLM providers."""


def http_status_hint(status_code: int) -> str:
    """Return a fixed hint without exposing provider response bodies or credentials."""
    if status_code == 401:
        return (
            "Authentication failed. Check that LLM_API_KEY is valid, active, "
            "and belongs to the intended API project. Do not share the key."
        )
    if status_code == 403:
        return (
            "Access was denied. Check project permissions, organization restrictions, "
            "and whether this model is available to your account."
        )
    if status_code == 404:
        return "The endpoint or model was not found. Check LLM_BASE_URL and LLM_MODEL."
    if status_code == 429:
        return (
            "The request limit or API quota may have been reached. Check usage limits "
            "and billing in your provider dashboard."
        )
    if 500 <= status_code <= 599:
        return "The provider returned a server error. Try again later and check its status page."
    return f"The provider rejected the request (HTTP {status_code}). Check the API configuration."
