def health() -> dict[str, str]:
    """Liveness signal for the smoke test and, later, the /health endpoint."""
    return {"service": "phulax-api", "status": "ok"}
