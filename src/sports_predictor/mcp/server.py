"""Optional MCP server exposing the Sports Predictor domain tools."""
from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit("MCP is optional. Install with: pip install 'sports-predictor[mcp]'") from exc
    from sports_predictor.betting.paper import PaperLedger
    from sports_predictor.betting.value import evaluate_bet
    from sports_predictor.data.fixtures import FixtureStore, ingest_fixture_file
    from sports_predictor.data.ingest import ingest_file
    from sports_predictor.data.store import MatchStore
    from sports_predictor.dashboard import export_dashboard
    from sports_predictor.prediction.backtest import backtest
    from sports_predictor.prediction.poisson import predict_match

    server = FastMCP("sports-predictor")
    ledger_path = Path(os.environ.get(
        "SPORTS_PREDICTOR_LEDGER", "~/.sports-predictor/paper-trading.sqlite3")).expanduser()
    dataset_path = Path(os.environ.get(
        "SPORTS_PREDICTOR_DATASET", "~/.sports-predictor/matches.jsonl")).expanduser()
    fixtures_path = Path(os.environ.get(
        "SPORTS_PREDICTOR_FIXTURES", "~/.sports-predictor/fixtures.jsonl")).expanduser()

    @server.tool()
    def search_competitions(query: str = "", season: str | None = None,
                            country: str | None = None) -> dict:
        """Search competitions and seasons currently present in the fixture catalogue."""
        competitions = FixtureStore(fixtures_path).search_competitions(query, season, country)
        return {"competitions": competitions, "count": len(competitions)}

    @server.tool()
    def get_competition_fixtures(competition_id: str, date_from: str | None = None,
                                 date_to: str | None = None, status: str | None = None,
                                 limit: int = 50) -> dict:
        """List fixtures for a discovered competition ID, optionally filtered by date and status."""
        fixtures = FixtureStore(fixtures_path).list_fixtures(
            competition_id, date_from=date_from, date_to=date_to, status=status, limit=limit
        )
        return {"competition_id": competition_id, "fixtures": fixtures, "count": len(fixtures)}

    @server.tool()
    def get_fixture_details(fixture_id: str) -> dict:
        """Return the latest stored source observation for a fixture ID."""
        fixture = FixtureStore(fixtures_path).get_fixture(fixture_id)
        return {"found": fixture is not None, "fixture": fixture}

    @server.tool()
    def ingest_fixture_file(file_path: str, provider: str | None = None) -> dict:
        """Import source-attributed fixture JSON into the local discovery catalogue."""
        fixtures_path.parent.mkdir(parents=True, exist_ok=True)
        return ingest_fixture_file(file_path, FixtureStore(fixtures_path), provider=provider)

    @server.tool()
    def predict_football_match(home_team: str, away_team: str, home_xg: float, away_xg: float) -> dict:
        """Calculate 1X2, BTTS, goal-total and scoreline probabilities from supplied xG."""
        return predict_match(home_team, away_team, home_xg, away_xg)

    @server.tool()
    def evaluate_betting_value(probability: float, decimal_odds: float,
                               bankroll: float | None = None, profile: str = "balanced") -> dict:
        """Calculate fair odds, expected value and capped fractional-Kelly stake."""
        return evaluate_bet(probability, decimal_odds, bankroll=bankroll, profile=profile)

    @server.tool()
    def ingest_match_file(file_path: str, provider: str = "manual") -> dict:
        """Ingest a local JSON file; each observation must carry source and retrieval timestamp."""
        dataset_path.parent.mkdir(parents=True, exist_ok=True)
        return ingest_file(file_path, MatchStore(dataset_path), provider=provider)

    @server.tool()
    def backtest_historical_matches(minimum_edge: float = 0.02, calibrate: bool = False) -> dict:
        """Evaluate 1X2 predictions and optional flat-stake value strategy on stored history."""
        return backtest(MatchStore(dataset_path).list(), minimum_edge=minimum_edge,
                        calibration=calibrate)

    @server.tool()
    def record_paper_bet(event: str, selection: str, decimal_odds: float, stake: float) -> dict:
        """Record a simulated bet. This tool never places a real wager."""
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        return PaperLedger(ledger_path).record(event, selection, decimal_odds, stake)

    @server.tool()
    def settle_paper_bet(bet_id: str, outcome: str) -> dict:
        """Settle a simulated bet with outcome won, lost or void."""
        return PaperLedger(ledger_path).settle(bet_id, outcome)

    @server.tool()
    def paper_trading_summary() -> dict:
        """Return ROI, win rate, net profit, drawdown and open-bet counts."""
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        return PaperLedger(ledger_path).summary()

    @server.tool()
    def export_paper_dashboard(output_path: str = "sports-predictor-dashboard.html") -> dict:
        """Export a self-contained local HTML dashboard from the paper ledger."""
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        output = export_dashboard(PaperLedger(ledger_path).list_bets(), output_path)
        return {"path": str(output.resolve()), "metrics": PaperLedger(ledger_path).summary()}

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
