"""Independent-goals Poisson model with an explicit expected-goals input."""
from __future__ import annotations
import math
from typing import Any


def _poisson_probabilities(lam: float, max_goals: int) -> list[float]:
    probabilities = [math.exp(-lam)]
    for goals in range(1, max_goals + 1):
        probabilities.append(probabilities[-1] * lam / goals)
    return probabilities


def predict_match(home_team: str, away_team: str, home_xg: float, away_xg: float,
                  *, max_goals: int = 10) -> dict[str, Any]:
    """Return normalized scoreline and market probabilities.

    xG values are caller-supplied, not fetched or inferred here. The score grid is
    truncated at max_goals and normalized to sum to one.
    """
    if not home_team.strip() or not away_team.strip():
        raise ValueError("home_team and away_team are required")
    if home_team.strip().casefold() == away_team.strip().casefold():
        raise ValueError("home_team and away_team must be different")
    for name, value in (("home_xg", home_xg), ("away_xg", away_xg)):
        if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= 6:
            raise ValueError(f"{name} must be a finite number in the interval (0, 6]")
    if not isinstance(max_goals, int) or not 5 <= max_goals <= 15:
        raise ValueError("max_goals must be an integer between 5 and 15")

    hp = _poisson_probabilities(float(home_xg), max_goals)
    ap = _poisson_probabilities(float(away_xg), max_goals)
    grid = [[h * a for a in ap] for h in hp]
    total = sum(map(sum, grid))
    grid = [[p / total for p in row] for row in grid]

    home_win = draw = away_win = btts = 0.0
    totals = {1: 0.0, 2: 0.0, 3: 0.0}
    scores = []
    for h, row in enumerate(grid):
        for a, probability in enumerate(row):
            if h > a:
                home_win += probability
            elif h == a:
                draw += probability
            else:
                away_win += probability
            if h and a:
                btts += probability
            for threshold in totals:
                if h + a >= threshold + 1:
                    totals[threshold] += probability
            scores.append({"score": f"{h}-{a}", "probability": probability})
    scores.sort(key=lambda item: item["probability"], reverse=True)
    return {
        "home_team": home_team, "away_team": away_team,
        "inputs": {"home_xg": float(home_xg), "away_xg": float(away_xg)},
        "model": "independent_poisson_v1",
        "markets": {
            "1x2": {"home": home_win, "draw": draw, "away": away_win},
            "btts": {"yes": btts, "no": 1 - btts},
            "total_goals": {
                "over_1_5": totals[1], "under_1_5": 1 - totals[1],
                "over_2_5": totals[2], "under_2_5": 1 - totals[2],
                "over_3_5": totals[3], "under_3_5": 1 - totals[3],
            },
        },
        "top_scorelines": scores[:5], "score_grid_max_goals": max_goals,
        "limitations": [
            "Expected goals are caller-supplied; no provider data is fetched.",
            "Independent Poisson does not model tactical dependence or team news.",
            "Probabilities are not calibrated against historical competitions yet.",
        ],
    }
