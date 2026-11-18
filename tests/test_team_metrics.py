import pytest
from sports_predictor.analysis.team_metrics import analyze_team_metrics

def test_team_metric_differentials_use_explicit_sign_conventions():
    result = analyze_team_metrics("Example FC", matches=10, xg=15, goals_scored=18,
        xga=12, goals_conceded=8, xpts=16, points=20)
    assert result["differentials"] == {
        "finishing_goals_minus_xg": 3.0,
        "defense_xga_minus_goals_conceded": 4.0,
        "points_minus_xpts": 4.0,
    }
    assert set(result["assessment"].values()) == {"overperforming"}

def test_team_metrics_can_be_underperforming_or_in_line():
    result = analyze_team_metrics("Example FC", matches=5, xg=8, goals_scored=6,
        xga=4, goals_conceded=6, xpts=7, points=7)
    assert result["assessment"]["finishing"] == "underperforming"
    assert result["assessment"]["defense"] == "underperforming"
    assert result["assessment"]["points"] == "approximately_in_line"

@pytest.mark.parametrize("kwargs", [
    {"matches": 0}, {"matches": True}, {"xg": float("nan")},
    {"goals_scored": -1}, {"xga": float("inf")}, {"points": -0.1},
])
def test_team_metrics_reject_invalid_values(kwargs):
    values = dict(matches=10, xg=10, goals_scored=10, xga=10,
        goals_conceded=10, xpts=10, points=10)
    values.update(kwargs)
    with pytest.raises(ValueError):
        analyze_team_metrics("Example FC", **values)
