"""Deterministic interpretation of season-level xG, xGA and xPTS metrics."""
from __future__ import annotations

import math
from typing import Any


def _number(name: str, value: float, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return result


def analyze_team_metrics(
    team: str,
    *,
    matches: int,
    xg: float,
    goals_scored: float,
    xga: float,
    goals_conceded: float,
    xpts: float,
    points: float,
    tolerance: float = 0.15,
) -> dict[str, Any]:
    """Calculate explicit over/under-performance deltas from season aggregates."""
    if not isinstance(team, str) or not team.strip():
        raise ValueError("team is required")
    if isinstance(matches, bool) or not isinstance(matches, int) or matches < 1:
        raise ValueError("matches must be a positive integer")

    tolerance = _number("tolerance", tolerance)
    values = {
        "xg": _number("xg", xg),
        "goals_scored": _number("goals_scored", goals_scored),
        "xga": _number("xga", xga),
        "goals_conceded": _number("goals_conceded", goals_conceded),
        "xpts": _number("xpts", xpts),
        "points": _number("points", points),
    }
    finishing = values["goals_scored"] - values["xg"]
    defending = values["xga"] - values["goals_conceded"]
    points_delta = values["points"] - values["xpts"]

    def status(delta: float) -> str:
        if delta > tolerance:
            return "overperforming"
        if delta < -tolerance:
            return "underperforming"
        return "approximately_in_line"

    return {
        "team": team.strip(),
        "matches": matches,
        "totals": values,
        "per_match": {key: value / matches for key, value in values.items()},
        "differentials": {
            "finishing_goals_minus_xg": finishing,
            "defense_xga_minus_goals_conceded": defending,
            "points_minus_xpts": points_delta,
        },
        "assessment": {
            "finishing": status(finishing),
            "defense": status(defending),
            "points": status(points_delta),
        },
        "interpretation": {
            "finishing": (
                "Positive means more goals scored than xG; it may regress and does not "
                "prove repeatable clinical finishing."
            ),
            "defense": (
                "Positive means fewer goals conceded than xGA; it may reflect goalkeeping, "
                "variance or defensive performance."
            ),
            "points": (
                "Positive means actual points exceed xPTS; it does not establish that the "
                "team is stronger."
            ),
        },
        "limitations": [
            "Season aggregates hide opponent strength, venue splits and sample composition.",
            "xG and xPTS definitions vary by provider and are not interchangeable across sources.",
            "Over-performance is descriptive and should not be projected forward without historical evidence.",
        ],
    }
