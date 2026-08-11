from phulax_api.health import health


def test_api_health_reports_ok():
    assert health() == {"service": "phulax-api", "status": "ok"}
