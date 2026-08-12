"""Risk score (plan §11.5): explains and prioritizes — never decides.

The engine's evaluate() does not accept a risk score; that absence is the
enforcement. These tests pin the scoring itself: additive named signals,
clamped to 0–100.
"""

import inspect

from phulax_policy import engine
from phulax_policy.risk import score_request


def test_read_low_sensitivity_scores_zero():
    result = score_request(
        side_effect="read", sensitivity="low", environment="staging", amount=None
    )
    assert result.score == 0
    assert result.signals == ()


def test_signals_are_named_and_additive():
    result = score_request(
        side_effect="write", sensitivity="high", environment="production", amount=None
    )
    assert result.score == sum(signal.weight for signal in result.signals)
    assert {signal.code for signal in result.signals} == {
        "SIDE_EFFECT_WRITE",
        "SENSITIVITY_HIGH",
        "ENV_PRODUCTION",
    }


def test_large_amount_raises_score():
    small = score_request(side_effect="write", sensitivity="high", environment="staging", amount=10)
    large = score_request(
        side_effect="write", sensitivity="high", environment="staging", amount=5000
    )
    assert large.score > small.score


def test_score_clamps_at_100():
    result = score_request(
        side_effect="irreversible",
        sensitivity="high",
        environment="production",
        amount=10_000_000,
    )
    assert result.score == 100


def test_engine_cannot_see_the_score():
    # Structural guarantee: a score can never override a rule, because
    # evaluate() has no parameter to receive one (plan §11.5).
    parameters = inspect.signature(engine.evaluate).parameters
    assert set(parameters) == {"request", "bundle", "state"}
