"""Performance metrics for settled paper bets."""
from __future__ import annotations
from typing import Any


def summarize_bets(rows: list[dict[str, Any]]) -> dict[str, Any]:
    settled = [row for row in rows if row["status"] != "open"]
    open_bets = [row for row in rows if row["status"] == "open"]
    wins = [row for row in settled if row["status"] == "won"]
    losses = [row for row in settled if row["status"] == "lost"]
    staked = sum(float(row["stake"]) for row in settled if row["status"] != "void")
    profit = sum(float(row["profit"] or 0) for row in settled)
    equity, peak, max_drawdown = 0.0, 0.0, 0.0
    for row in sorted(settled, key=lambda item: item["settled_at"] or ""):
        equity += float(row["profit"] or 0)
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return {
        "total_bets": len(rows), "open_bets": len(open_bets), "settled_bets": len(settled),
        "wins": len(wins), "losses": len(losses), "void": sum(row["status"] == "void" for row in settled),
        "win_rate": len(wins) / (len(wins) + len(losses)) if wins or losses else 0.0,
        "total_staked": staked, "net_profit": profit, "roi": profit / staked if staked else 0.0,
        "max_drawdown": max_drawdown,
        "average_odds": (sum(float(row["odds"]) for row in settled if row["status"] != "void") /
                         sum(row["status"] != "void" for row in settled)) if staked else 0.0,
    }
