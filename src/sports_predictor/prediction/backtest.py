"""Historical evaluation for 1X2 and goal markets, with optional calibration."""
from __future__ import annotations
import math
from collections import defaultdict
from typing import Any, Iterable
from sports_predictor.data.models import MatchRecord
from sports_predictor.prediction.calibration import fit_temperature, apply_temperature
from sports_predictor.prediction.poisson import predict_match


def _actual_1x2(record: MatchRecord) -> int:
    if record.home_goals > record.away_goals:
        return 0
    if record.home_goals == record.away_goals:
        return 1
    return 2


def _brier(probabilities: list[float], actual: int) -> float:
    return sum((probability - (1.0 if index == actual else 0.0)) ** 2
               for index, probability in enumerate(probabilities)) / len(probabilities)


def backtest(records: Iterable[MatchRecord], *, minimum_edge: float = 0.02,
             calibration: bool = False) -> dict[str, Any]:
    """Evaluate predictions on supplied historical records.

    Calibration is fitted on the same records for exploratory diagnostics only.
    For unbiased evaluation, fit on an earlier chronological window and evaluate
    on a separate later holdout (the CLI does not silently split user datasets).
    """
    rows = list(records)
    if not rows:
        raise ValueError("backtest requires at least one historical match")
    if minimum_edge < 0 or not math.isfinite(minimum_edge):
        raise ValueError("minimum_edge must be finite and non-negative")

    predictions: list[tuple[MatchRecord, dict[str, tuple[list[float], int]]]] = []
    for record in rows:
        output = predict_match(record.home_team, record.away_team, record.home_xg, record.away_xg)
        markets = output["markets"]
        actual_1x2 = _actual_1x2(record)
        actual_btts = int(record.home_goals > 0 and record.away_goals > 0)
        actual_total = record.home_goals + record.away_goals
        targets = {
            "1x2": ([markets["1x2"]["home"], markets["1x2"]["draw"], markets["1x2"]["away"]], actual_1x2),
            "btts": ([markets["btts"]["no"], markets["btts"]["yes"]], actual_btts),
            "over_1_5": ([markets["total_goals"]["under_1_5"], markets["total_goals"]["over_1_5"]],
                         int(actual_total >= 2)),
            "over_2_5": ([markets["total_goals"]["under_2_5"], markets["total_goals"]["over_2_5"]],
                         int(actual_total >= 3)),
            "over_3_5": ([markets["total_goals"]["under_3_5"], markets["total_goals"]["over_3_5"]],
                         int(actual_total >= 4)),
        }
        predictions.append((record, targets))

    grouped_samples: dict[str, list[tuple[list[float], int]]] = defaultdict(list)
    for record, targets in predictions:
        for market, sample in targets.items():
            grouped_samples[f"{record.competition}|{market}"].append(sample)

    temperatures: dict[str, float] = {}
    if calibration:
        for key, samples in grouped_samples.items():
            if len(samples) >= 10:
                temperatures[key] = float(fit_temperature(samples)["temperature"])

    market_accumulators: dict[str, dict[str, float | int]] = {}
    competition_market: dict[str, dict[str, float | int]] = {}
    competition_1x2: dict[str, dict[str, float | int]] = {}
    strategy_bets = strategy_wins = strategy_losses = 0
    staked = profit = 0.0

    for record, targets in predictions:
        evaluated_targets: dict[str, tuple[list[float], int]] = {}
        for market, (raw_probs, actual) in targets.items():
            calibration_key = f"{record.competition}|{market}"
            probs = (apply_temperature(raw_probs, temperatures[calibration_key])
                     if calibration_key in temperatures else raw_probs)
            evaluated_targets[market] = (probs, actual)
            loss = -math.log(max(probs[actual], 1e-12))
            brier = _brier(probs, actual)
            correct = int(max(range(len(probs)), key=lambda index: probs[index]) == actual)
            aggregate = market_accumulators.setdefault(
                market, {"samples": 0, "log_loss": 0.0, "brier_score": 0.0, "correct": 0})
            aggregate["samples"] += 1
            aggregate["log_loss"] += loss
            aggregate["brier_score"] += brier
            aggregate["correct"] += correct
            group_key = f"{record.competition}|{market}"
            group = competition_market.setdefault(
                group_key, {"competition": record.competition, "market": market, "samples": 0,
                            "log_loss": 0.0, "brier_score": 0.0, "correct": 0})
            group["samples"] += 1
            group["log_loss"] += loss
            group["brier_score"] += brier
            group["correct"] += correct

            if market == "1x2":
                comp = competition_1x2.setdefault(
                    record.competition, {"matches": 0, "log_loss": 0.0, "brier": 0.0, "correct": 0})
                comp["matches"] += 1
                comp["log_loss"] += loss
                comp["brier"] += brier
                comp["correct"] += correct

        # The baseline betting simulation is deliberately limited to supplied 1X2 prices.
        if record.odds:
            probs = evaluated_targets["1x2"][0]
            candidates = [(probs[index], record.odds[key], key, index)
                          for index, key in enumerate(("home", "draw", "away")) if key in record.odds]
            eligible = [(p, price, key, index) for p, price, key, index in candidates
                        if p * price - 1 >= minimum_edge]
            if eligible:
                _, price, _, index = max(eligible, key=lambda item: item[0] * item[1] - 1)
                strategy_bets += 1
                staked += 1.0
                if index == targets["1x2"][1]:
                    strategy_wins += 1
                    profit += price - 1
                else:
                    strategy_losses += 1
                    profit -= 1.0

    def finalize(group: dict[str, float | int], samples_key: str = "samples") -> dict[str, float | int]:
        result = dict(group)
        n = int(result[samples_key])
        result["log_loss"] = float(result["log_loss"]) / n
        result["brier_score"] = float(result["brier_score"]) / n
        result["accuracy"] = int(result["correct"]) / n
        return result

    per_market = {name: finalize(group) for name, group in market_accumulators.items()}
    per_competition_market_result = {
        key: finalize(group) for key, group in competition_market.items()
    }
    per_competition = {}
    for name, group in competition_1x2.items():
        n = int(group["matches"])
        per_competition[name] = {
            "matches": n, "log_loss": group["log_loss"] / n, "brier": group["brier"] / n,
            "accuracy": group["correct"] / n,
        }

    return {
        "matches": len(rows), "per_market": per_market,
        "per_competition": per_competition,
        "per_competition_market": per_competition_market_result,
        "calibration_temperatures": temperatures,
        "calibration_fit_is_in_sample": bool(temperatures),
        "paper_strategy_1x2": {
            "bets": strategy_bets, "wins": strategy_wins, "losses": strategy_losses,
            "staked_units": staked, "net_profit_units": profit,
            "roi": profit / staked if staked else 0.0,
        },
        "caveats": [
            "Metrics cover 1X2, BTTS and over 1.5/2.5/3.5 markets.",
            "This evaluates the xG-driven baseline, not a trained forecasting model.",
            "Temperature fitting is in-sample; reserve a chronological holdout for honest evaluation.",
            "ROI uses one flat unit per selected match and supplied 1X2 decimal odds only.",
            "No market-margin correction or closing-line-value measurement is applied.",
        ],
    }
