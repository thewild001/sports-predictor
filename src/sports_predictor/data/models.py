"""Validated match observations with explicit data provenance."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
import math
from datetime import datetime
from typing import Any


def _aware_datetime(value: str | datetime, field_name: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone")
    return parsed


@dataclass(frozen=True)
class DataSource:
    provider: str
    retrieved_at: datetime
    source_url: str | None = None
    source_record_id: str | None = None

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("source.provider is required")
        object.__setattr__(self, "retrieved_at", _aware_datetime(self.retrieved_at, "retrieved_at"))

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "DataSource":
        return cls(provider=str(raw["provider"]), retrieved_at=_aware_datetime(raw["retrieved_at"], "retrieved_at"),
                   source_url=raw.get("source_url"), source_record_id=raw.get("source_record_id"))


@dataclass(frozen=True)
class MatchRecord:
    match_id: str
    competition: str
    season: str
    kickoff: datetime
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    home_xg: float
    away_xg: float
    source: DataSource
    odds: dict[str, float] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("match_id", "competition", "season", "home_team", "away_team"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if self.home_team.casefold() == self.away_team.casefold():
            raise ValueError("home_team and away_team must be different")
        object.__setattr__(self, "kickoff", _aware_datetime(self.kickoff, "kickoff"))
        for name in ("home_goals", "away_goals"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 30:
                raise ValueError(f"{name} must be an integer between 0 and 30")
        for name in ("home_xg", "away_xg"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= 6:
                raise ValueError(f"{name} must be in the interval (0, 6]")
        for market, price in self.odds.items():
            if market not in {"home", "draw", "away"}:
                raise ValueError(f"unsupported odds market: {market}")
            if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 1:
                raise ValueError(f"odds for {market} must be greater than 1")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "MatchRecord":
        return cls(
            match_id=str(raw["match_id"]), competition=str(raw["competition"]), season=str(raw["season"]),
            kickoff=_aware_datetime(raw["kickoff"], "kickoff"), home_team=str(raw["home_team"]),
            away_team=str(raw["away_team"]), home_goals=int(raw["home_goals"]),
            away_goals=int(raw["away_goals"]), home_xg=float(raw["home_xg"]),
            away_xg=float(raw["away_xg"]), source=DataSource.from_dict(raw["source"]),
            odds={key: float(value) for key, value in raw.get("odds", {}).items()},
            stats=dict(raw.get("stats", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["kickoff"] = self.kickoff.isoformat()
        result["source"]["retrieved_at"] = self.source.retrieved_at.isoformat()
        return result
