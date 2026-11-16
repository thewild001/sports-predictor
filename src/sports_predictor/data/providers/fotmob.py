"""FotMob payload normalizer.

This adapter intentionally does not scrape undocumented endpoints or bypass access
controls. It accepts a saved FotMob match payload only when the caller maps its
fields to the explicit canonical mapping below; the original payload is retained
in stats for auditability.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from sports_predictor.data.models import DataSource, MatchRecord


class FotMobPayloadAdapter:
    provider_name = "fotmob"

    def normalize(self, payload: dict[str, Any]) -> list[MatchRecord]:
        """Normalize the adapter's documented envelope, not arbitrary FotMob JSON.

        Required envelope keys: match_id, competition, season, kickoff, home_team,
        away_team, home_goals, away_goals, home_xg, away_xg. Optional stats/odds.
        This deliberate boundary avoids guessing changing upstream response shapes.
        """
        required = {"match_id", "competition", "season", "kickoff", "home_team", "away_team",
                    "home_goals", "away_goals", "home_xg", "away_xg"}
        missing = sorted(required - payload.keys())
        if missing:
            raise ValueError("FotMob adapter envelope missing fields: " + ", ".join(missing))
        retrieved = payload.get("retrieved_at") or datetime.now(timezone.utc).isoformat()
        record = MatchRecord(
            match_id=str(payload["match_id"]), competition=str(payload["competition"]),
            season=str(payload["season"]), kickoff=datetime.fromisoformat(
                str(payload["kickoff"]).replace("Z", "+00:00")),
            home_team=str(payload["home_team"]), away_team=str(payload["away_team"]),
            home_goals=int(payload["home_goals"]), away_goals=int(payload["away_goals"]),
            home_xg=float(payload["home_xg"]), away_xg=float(payload["away_xg"]),
            odds={key: float(value) for key, value in payload.get("odds", {}).items()},
            stats=dict(payload.get("stats", {})),
            source=DataSource("fotmob", datetime.fromisoformat(str(retrieved).replace("Z", "+00:00")),
                              payload.get("source_url"), str(payload["match_id"])),
        )
        return [record]
