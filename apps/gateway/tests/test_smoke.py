from phulax_gateway.health import health


def test_gateway_health_reports_ok():
    assert health() == {"service": "phulax-gateway", "status": "ok"}
