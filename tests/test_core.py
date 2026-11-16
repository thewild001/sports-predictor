import pytest
from sports_predictor.betting.paper import PaperLedger
from sports_predictor.betting.value import evaluate_bet
from sports_predictor.prediction.poisson import predict_match


def test_poisson_market_probabilities_sum_to_one():
    result = predict_match("Home", "Away", 1.6, 1.1)
    assert sum(result["markets"]["1x2"].values()) == pytest.approx(1)
    assert sum(result["markets"]["btts"].values()) == pytest.approx(1)
    assert sum(result["markets"]["total_goals"].values()) == pytest.approx(3)


def test_more_home_xg_increases_home_win_probability():
    low = predict_match("Home", "Away", .8, 1.2)
    high = predict_match("Home", "Away", 2.2, 1.2)
    assert high["markets"]["1x2"]["home"] > low["markets"]["1x2"]["home"]


@pytest.mark.parametrize("home_xg,away_xg", [(0, 1), (1, 0), (7, 1), (float("nan"), 1)])
def test_invalid_xg_is_rejected(home_xg, away_xg):
    with pytest.raises(ValueError):
        predict_match("Home", "Away", home_xg, away_xg)


def test_positive_value_stake_is_capped():
    result = evaluate_bet(.60, 2, bankroll=1000, profile="balanced")
    assert result["expected_value_per_unit"] == pytest.approx(.2)
    assert result["suggested_stake"] == pytest.approx(25)


def test_no_value_means_no_bet():
    result = evaluate_bet(.4, 2, bankroll=1000)
    assert result["recommended_action"] == "no_bet"
    assert result["suggested_stake"] == 0


def test_missing_bankroll_means_no_stake():
    result = evaluate_bet(.6, 2)
    assert result["value_detected"] is True
    assert result["suggested_stake"] == 0


def test_invalid_odds_are_rejected():
    with pytest.raises(ValueError):
        evaluate_bet(.5, 1)


def test_paper_bet_lifecycle(tmp_path):
    ledger = PaperLedger(tmp_path / "paper.sqlite3")
    bet = ledger.record("Home vs Away", "Home win", 2.2, 10)
    settled = ledger.settle(bet["id"], "won")
    assert settled["profit"] == pytest.approx(12.0)
    assert ledger.summary()["net_profit"] == pytest.approx(12.0)
    with pytest.raises(ValueError):
        ledger.settle(bet["id"], "lost")
