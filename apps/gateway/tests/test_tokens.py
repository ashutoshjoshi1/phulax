"""Day 5 exit criteria (validation side): valid accepted; invalid, expired,
wrong-audience, and tampered tokens rejected."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from phulax_gateway.tokens import TokenError, validate_token

KEY = "unit-test-key-0123456789abcdef01"
AUD = "phulax-gateway"


def _claims(**overrides) -> dict:
    now = datetime.now(UTC)
    claims = {
        "iss": "phulax-control-plane",
        "aud": AUD,
        "sub": str(uuid.uuid4()),
        "org": str(uuid.uuid4()),
        "avid": str(uuid.uuid4()),
        "ver": "1.0.0",
        "sid": str(uuid.uuid4()),
        "env": "staging",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
    }
    return claims | overrides


def _token(**overrides) -> str:
    return jwt.encode(_claims(**overrides), KEY, algorithm="HS256")


def test_valid_token_accepted_with_bound_claims():
    claims = _claims()
    parsed = validate_token(jwt.encode(claims, KEY, algorithm="HS256"), key=KEY, audience=AUD)
    assert str(parsed.agent_id) == claims["sub"]
    assert parsed.version == "1.0.0"
    assert parsed.environment == "staging"
    assert str(parsed.session_id) == claims["sid"]


def test_expired_token_rejected():
    expired = _token(exp=int((datetime.now(UTC) - timedelta(minutes=1)).timestamp()))
    with pytest.raises(TokenError) as excinfo:
        validate_token(expired, key=KEY, audience=AUD)
    assert excinfo.value.code == "token_expired"


def test_wrong_audience_rejected():
    with pytest.raises(TokenError) as excinfo:
        validate_token(_token(aud="some-other-service"), key=KEY, audience=AUD)
    assert excinfo.value.code == "wrong_audience"


def test_tampered_signature_rejected():
    token = _token()
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    with pytest.raises(TokenError) as excinfo:
        validate_token(tampered, key=KEY, audience=AUD)
    assert excinfo.value.code == "invalid_token"


def test_missing_binding_claim_rejected():
    claims = _claims()
    del claims["sid"]
    token = jwt.encode(claims, KEY, algorithm="HS256")
    with pytest.raises(TokenError) as excinfo:
        validate_token(token, key=KEY, audience=AUD)
    assert excinfo.value.code == "missing_claim"


def test_wrong_key_rejected():
    token = jwt.encode(_claims(), "a-different-key-0123456789abcdef", algorithm="HS256")
    with pytest.raises(TokenError) as excinfo:
        validate_token(token, key=KEY, audience=AUD)
    assert excinfo.value.code == "invalid_token"
