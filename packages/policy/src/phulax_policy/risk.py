"""Risk score (plan §11.5): weighted signals that *explain and prioritize*.

The score never decides. ``engine.evaluate`` has no parameter to receive it
— that absence is the enforcement. The moment a score can override a rule,
the product has rebuilt the anomaly-model mystery it exists to replace.
"""

from dataclasses import dataclass

_SIDE_EFFECT_WEIGHTS = {
    "write": ("SIDE_EFFECT_WRITE", 20),
    "irreversible": ("SIDE_EFFECT_IRREVERSIBLE", 40),
}
_SENSITIVITY_WEIGHTS = {"medium": ("SENSITIVITY_MEDIUM", 15), "high": ("SENSITIVITY_HIGH", 30)}
_PRODUCTION_WEIGHT = 10
_AMOUNT_TIERS = (
    (1000, "AMOUNT_OVER_1000", 20),
    (100, "AMOUNT_OVER_100", 10),
)
_MAX_SCORE = 100


@dataclass(frozen=True)
class RiskSignal:
    code: str
    weight: int


@dataclass(frozen=True)
class RiskScore:
    score: int
    signals: tuple[RiskSignal, ...]


def score_request(
    *,
    side_effect: str | None,
    sensitivity: str | None,
    environment: str,
    amount: float | None,
) -> RiskScore:
    signals: list[RiskSignal] = []
    if side_effect in _SIDE_EFFECT_WEIGHTS:
        signals.append(RiskSignal(*_SIDE_EFFECT_WEIGHTS[side_effect]))
    if sensitivity in _SENSITIVITY_WEIGHTS:
        signals.append(RiskSignal(*_SENSITIVITY_WEIGHTS[sensitivity]))
    if environment == "production":
        signals.append(RiskSignal("ENV_PRODUCTION", _PRODUCTION_WEIGHT))
    if isinstance(amount, int | float) and not isinstance(amount, bool):
        for threshold, code, weight in _AMOUNT_TIERS:
            if amount > threshold:
                signals.append(RiskSignal(code, weight))
                break
    score = min(_MAX_SCORE, sum(signal.weight for signal in signals))
    return RiskScore(score=score, signals=tuple(signals))
