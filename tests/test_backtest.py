from datetime import datetime, timezone, timedelta
import pytest
from sports_predictor.data.models import DataSource, MatchRecord
from sports_predictor.prediction.backtest import backtest
from sports_predictor.prediction.calibration import apply_temperature, fit_temperature


def history(size=12):
    rows = []
    for index in range(size):
        rows.append(MatchRecord(
            match_id=f"m-{index}", competition="League A" if index < 10 else "League B",
            season="2025/26", kickoff=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index),
            home_team="Home", away_team="Away",
            home_goals=2 if index % 3 else 0, away_goals=0 if index % 3 else 1,
            home_xg=1.8, away_xg=.8,
            source=DataSource("test", datetime(2026, 3, 1, tzinfo=timezone.utc)),
            odds={"home": 1.9, "draw": 3.4, "away": 4.2},
        ))
    return rows


def test_backtest_returns_market_and_competition_breakdowns():
    result = backtest(history())
    assert result["matches"] == 12
    assert "1x2" in result["per_market"]
    assert "btts" in result["per_market"]
    assert "over_2_5" in result["per_market"]
    assert "League A" in result["per_competition"]
    assert "League A|btts" in result["per_competition_market"]
    assert result["paper_strategy_1x2"]["staked_units"] >= 0


def test_calibration_requires_enough_samples():
    with pytest.raises(ValueError, match="at least 10"):
        fit_temperature([([.5, .3, .2], 0)] * 9)


def test_temperature_calibration_preserves_probability_sum():
    calibrated = apply_temperature([.6, .25, .15], 1.5)
    assert sum(calibrated) == pytest.approx(1)
    assert all(0 < probability < 1 for probability in calibrated)


def test_backtest_calibration_is_reported_as_in_sample():
    result = backtest(history(), calibration=True)
    assert result["calibration_fit_is_in_sample"] is True
    assert "League A|1x2" in result["calibration_temperatures"]
    assert "League B|1x2" not in result["calibration_temperatures"]
