"""Minimal SQLite paper-trading ledger; it never places real bets."""
from __future__ import annotations
import math
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PaperLedger:
    def __init__(self, database: str | Path = "sports-predictor-paper.sqlite3") -> None:
        self.database = str(database)
        with closing(self._connect()) as connection, connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS paper_bets (
                id TEXT PRIMARY KEY, event TEXT NOT NULL, selection TEXT NOT NULL,
                odds REAL NOT NULL CHECK (odds > 1), stake REAL NOT NULL CHECK (stake > 0),
                status TEXT NOT NULL CHECK (status IN ('open','won','lost','void')),
                profit REAL, created_at TEXT NOT NULL, settled_at TEXT)""")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        return connection

    def record(self, event: str, selection: str, odds: float, stake: float) -> dict[str, Any]:
        if not event.strip() or not selection.strip():
            raise ValueError("event and selection are required")
        if not math.isfinite(odds) or not math.isfinite(stake) or odds <= 1 or stake <= 0:
            raise ValueError("odds must be finite and > 1; stake must be finite and > 0")
        bet_id, created = str(uuid.uuid4()), datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO paper_bets VALUES (?, ?, ?, ?, ?, 'open', NULL, ?, NULL)",
                (bet_id, event, selection, odds, stake, created))
        return {"id": bet_id, "event": event, "selection": selection, "odds": odds,
                "stake": stake, "status": "open", "created_at": created}

    def settle(self, bet_id: str, outcome: str) -> dict[str, Any]:
        if outcome not in {"won", "lost", "void"}:
            raise ValueError("outcome must be won, lost or void")
        with closing(self._connect()) as connection, connection:
            row = connection.execute("SELECT * FROM paper_bets WHERE id = ?", (bet_id,)).fetchone()
            if row is None:
                raise ValueError("paper bet not found")
            if row["status"] != "open":
                raise ValueError("paper bet has already been settled")
            profit = (row["stake"] * (row["odds"] - 1) if outcome == "won"
                      else -row["stake"] if outcome == "lost" else 0.0)
            settled = datetime.now(timezone.utc).isoformat()
            connection.execute("UPDATE paper_bets SET status=?, profit=?, settled_at=? WHERE id=?",
                               (outcome, profit, settled, bet_id))
        return {"id": bet_id, "status": outcome, "profit": profit, "settled_at": settled}

    def list_bets(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute("SELECT * FROM paper_bets ORDER BY created_at, id").fetchall()
        return [dict(row) for row in rows]

    def summary(self) -> dict[str, Any]:
        from sports_predictor.betting.metrics import summarize_bets
        return summarize_bets(self.list_bets())
