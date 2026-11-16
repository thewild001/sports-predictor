from sports_predictor.betting.paper import PaperLedger
from sports_predictor.dashboard import export_dashboard, render_dashboard


def test_paper_metrics_and_dashboard_export(tmp_path):
    ledger = PaperLedger(tmp_path / "paper.sqlite3")
    won = ledger.record("Home v Away", "Home", 2.0, 10)
    lost = ledger.record("Team C v Team D", "Draw", 3.0, 5)
    ledger.settle(won["id"], "won")
    ledger.settle(lost["id"], "lost")
    metrics = ledger.summary()
    assert metrics["settled_bets"] == 2
    assert metrics["net_profit"] == 5
    assert metrics["roi"] == 1 / 3
    assert metrics["win_rate"] == .5
    html = render_dashboard(ledger.list_bets())
    assert "Paper Trading" in html
    assert "Home v Away" in html
    target = export_dashboard(ledger.list_bets(), tmp_path / "report.html")
    assert target.exists()
