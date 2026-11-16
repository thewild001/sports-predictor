"""Command-line interface for predictions, ingestion, backtesting and paper trading."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from sports_predictor.betting.paper import PaperLedger
from sports_predictor.betting.value import evaluate_bet
from sports_predictor.data.ingest import ingest_file
from sports_predictor.data.store import MatchStore
from sports_predictor.dashboard import export_dashboard
from sports_predictor.prediction.backtest import backtest
from sports_predictor.prediction.poisson import predict_match


def main() -> None:
    parser = argparse.ArgumentParser(prog="sports-predictor")
    commands = parser.add_subparsers(dest="command", required=True)
    predict = commands.add_parser("predict", help="calculate match probabilities from xG inputs")
    predict.add_argument("--home", required=True)
    predict.add_argument("--away", required=True)
    predict.add_argument("--home-xg", required=True, type=float)
    predict.add_argument("--away-xg", required=True, type=float)
    bet = commands.add_parser("evaluate", help="evaluate a selection against decimal odds")
    bet.add_argument("--probability", required=True, type=float)
    bet.add_argument("--odds", required=True, type=float)
    bet.add_argument("--bankroll", type=float)
    bet.add_argument("--profile", choices=["conservative", "balanced", "aggressive"], default="balanced")

    ingest = commands.add_parser("ingest", help="ingest canonical match JSON with provenance")
    ingest.add_argument("file")
    ingest.add_argument("--provider", choices=["manual", "fotmob"], default="manual")
    ingest.add_argument("--database", default="sports-predictor-matches.jsonl")

    test = commands.add_parser("backtest", help="evaluate predictions against historical match data")
    test.add_argument("--database", default="sports-predictor-matches.jsonl")
    test.add_argument("--minimum-edge", type=float, default=0.02)
    test.add_argument("--calibrate", action="store_true")

    dashboard = commands.add_parser("dashboard", help="export the paper-trading HTML dashboard")
    dashboard.add_argument("--database", default="~/.sports-predictor/paper-trading.sqlite3")
    dashboard.add_argument("--output", default="sports-predictor-dashboard.html")

    summary = commands.add_parser("paper-summary", help="show paper-trading performance metrics")
    summary.add_argument("--database", default="~/.sports-predictor/paper-trading.sqlite3")

    args = parser.parse_args()
    if args.command == "predict":
        result = predict_match(args.home, args.away, args.home_xg, args.away_xg)
    elif args.command == "evaluate":
        result = evaluate_bet(args.probability, args.odds, bankroll=args.bankroll, profile=args.profile)
    elif args.command == "ingest":
        result = ingest_file(args.file, MatchStore(args.database), provider=args.provider)
    elif args.command == "backtest":
        result = backtest(MatchStore(args.database).list(), minimum_edge=args.minimum_edge,
                          calibration=args.calibrate)
    elif args.command == "dashboard":
        ledger = PaperLedger(Path(args.database).expanduser())
        destination = export_dashboard(ledger.list_bets(), args.output)
        result = {"dashboard": str(destination.resolve()), "metrics": ledger.summary()}
    else:
        result = PaperLedger(Path(args.database).expanduser()).summary()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
