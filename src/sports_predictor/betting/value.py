"""Expected-value and fractional-Kelly evaluation."""
from __future__ import annotations
import math
from typing import Any

PROFILES = {
    "conservative": {"kelly_fraction": 0.10, "max_stake_fraction": 0.01},
    "balanced": {"kelly_fraction": 0.25, "max_stake_fraction": 0.025},
    "aggressive": {"kelly_fraction": 0.50, "max_stake_fraction": 0.05},
}


def evaluate_bet(probability: float, decimal_odds: float, *, bankroll: float | None = None,
                 profile: str = "balanced", minimum_edge: float = 0.02) -> dict[str, Any]:
    """Evaluate a selection; stake is zero unless positive edge is sufficient."""
    if not isinstance(probability, (int, float)) or not math.isfinite(probability) or not 0 < probability < 1:
        raise ValueError("probability must be between 0 and 1")
    if not isinstance(decimal_odds, (int, float)) or not math.isfinite(decimal_odds) or decimal_odds <= 1:
        raise ValueError("decimal_odds must be greater than 1")
    if profile not in PROFILES:
        raise ValueError(f"profile must be one of: {', '.join(PROFILES)}")
    if not math.isfinite(minimum_edge) or minimum_edge < 0:
        raise ValueError("minimum_edge must be finite and non-negative")
    if bankroll is not None and (not math.isfinite(bankroll) or bankroll <= 0):
        raise ValueError("bankroll must be a positive finite amount")

    implied = 1 / decimal_odds
    edge = probability - implied
    ev = probability * decimal_odds - 1
    kelly = max(0.0, ev / (decimal_odds - 1))
    settings = PROFILES[profile]
    eligible = ev >= minimum_edge
    stake_fraction = 0.0
    if bankroll is not None and eligible:
        stake_fraction = min(kelly * settings["kelly_fraction"], settings["max_stake_fraction"])
    return {
        "probability": float(probability), "decimal_odds": float(decimal_odds),
        "implied_probability": implied, "fair_odds": 1 / probability,
        "probability_edge": edge, "expected_value_per_unit": ev, "profile": profile,
        "minimum_edge": minimum_edge, "value_detected": eligible,
        "recommended_action": "consider" if eligible else "no_bet", "bankroll": bankroll,
        "stake_fraction": stake_fraction, "suggested_stake": (bankroll or 0) * stake_fraction,
        "stake_cap_fraction": settings["max_stake_fraction"],
        "disclaimer": "Model estimate only; not a guarantee of profit. Validate data and prices before acting.",
    }
