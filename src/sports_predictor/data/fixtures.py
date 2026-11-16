"""Competition and fixture discovery records with explicit source provenance."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sports_predictor.data.models import DataSource


def _aware_datetime(value: str | datetime, field_name: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone")
    return parsed


@dataclass(frozen=True)
class FixtureRecord:
    """A scheduled or completed fixture, independent of any data provider."""

    fixture_id: str
    competition_id: str
    competition_name: str
    season: str
    kickoff: datetime
    home_team: str
    away_team: str
    source: DataSource
    status: str = "scheduled"
    country: str | None = None
    matchday: str | None = None
    venue: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "fixture_id", "competition_id", "competition_name", "season",
            "home_team", "away_team",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if self.home_team.casefold() == self.away_team.casefold():
            raise ValueError("home_team and away_team must be different")
        object.__setattr__(self, "kickoff", _aware_datetime(self.kickoff, "kickoff"))
        if self.status not in {
            "scheduled", "live", "finished", "postponed", "cancelled", "abandoned", "unknown"
        }:
            raise ValueError("unsupported fixture status")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "FixtureRecord":
        return cls(
            fixture_id=str(raw["fixture_id"]),
            competition_id=str(raw["competition_id"]),
            competition_name=str(raw["competition_name"]),
            season=str(raw["season"]),
            kickoff=_aware_datetime(raw["kickoff"], "kickoff"),
            home_team=str(raw["home_team"]),
            away_team=str(raw["away_team"]),
            source=DataSource.from_dict(raw["source"]),
            status=str(raw.get("status", "scheduled")).lower(),
            country=raw.get("country"),
            matchday=str(raw["matchday"]) if raw.get("matchday") is not None else None,
            venue=raw.get("venue"),
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["kickoff"] = self.kickoff.isoformat()
        result["source"]["retrieved_at"] = self.source.retrieved_at.isoformat()
        return result


class FixtureStore:
    """Append-only JSONL fixture catalogue, deduplicated by fixture and provider."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def list(self) -> list[FixtureRecord]:
        if not self.path.exists():
            return []
        records: list[FixtureRecord] = []
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                records.append(FixtureRecord.from_dict(json.loads(line)))
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"invalid fixture record at line {line_number}: {exc}") from exc
        return records

    def append(self, records: list[FixtureRecord]) -> dict[str, int]:
        existing = self.list()
        keys = {(item.fixture_id, item.source.provider) for item in existing}
        added = skipped = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            for item in records:
                key = (item.fixture_id, item.source.provider)
                if key in keys:
                    skipped += 1
                    continue
                stream.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")
                keys.add(key)
                added += 1
        return {"added": added, "skipped_duplicates": skipped}

    def search_competitions(
        self, query: str = "", season: str | None = None, country: str | None = None
    ) -> list[dict[str, Any]]:
        competitions: dict[tuple[str, str], dict[str, Any]] = {}
        needle = query.casefold().strip()
        for fixture in self.list():
            if season and fixture.season.casefold() != season.casefold():
                continue
            if country and (fixture.country or "").casefold() != country.casefold():
                continue
            if needle and needle not in fixture.competition_name.casefold() and needle not in fixture.competition_id.casefold():
                continue
            key = (fixture.competition_id, fixture.season)
            item = competitions.setdefault(key, {
                "competition_id": fixture.competition_id,
                "competition_name": fixture.competition_name,
                "country": fixture.country,
                "season": fixture.season,
                "_fixture_ids": set(),
            })
            item["_fixture_ids"].add(fixture.fixture_id)
        results = []
        for item in competitions.values():
            results.append({
                key: value for key, value in item.items() if key != "_fixture_ids"
            } | {"fixture_count": len(item["_fixture_ids"])})
        return sorted(
            results,
            key=lambda item: (item["competition_name"].casefold(), item["season"]),
        )

    def list_fixtures(
        self,
        competition_id: str,
        date_from: str | None = None,
        date_to: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if not competition_id.strip():
            raise ValueError("competition_id is required")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        start = date.fromisoformat(date_from) if date_from else None
        end = date.fromisoformat(date_to) if date_to else None
        if start and end and start > end:
            raise ValueError("date_from must be on or before date_to")
        if status and status not in {
            "scheduled", "live", "finished", "postponed", "cancelled", "abandoned", "unknown"
        }:
            raise ValueError("unsupported fixture status")
        latest: dict[str, FixtureRecord] = {}
        for item in self.list():
            current = latest.get(item.fixture_id)
            if current is None or item.source.retrieved_at > current.source.retrieved_at:
                latest[item.fixture_id] = item
        fixtures = [
            item for item in latest.values()
            if item.competition_id.casefold() == competition_id.casefold()
            and (start is None or item.kickoff.date() >= start)
            and (end is None or item.kickoff.date() <= end)
            and (status is None or item.status == status)
        ]
        fixtures.sort(key=lambda item: item.kickoff)
        return [item.to_dict() for item in fixtures[:limit]]

    def get_fixture(self, fixture_id: str) -> dict[str, Any] | None:
        matches = [item for item in self.list() if item.fixture_id == fixture_id]
        if not matches:
            return None
        matches.sort(key=lambda item: item.source.retrieved_at, reverse=True)
        return matches[0].to_dict()


def ingest_fixture_file(file_path: str | Path, store: FixtureStore, provider: str | None = None) -> dict[str, int]:
    """Import a JSON array or an object containing a fixtures array."""
    raw = json.loads(Path(file_path).read_text(encoding="utf-8"))
    items = raw.get("fixtures") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("fixture input must be a JSON array or an object with a fixtures array")
    records = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each fixture must be a JSON object")
        record = FixtureRecord.from_dict(item)
        if provider and record.source.provider != provider:
            raise ValueError("fixture source.provider does not match the requested provider")
        records.append(record)
    return store.append(records)
