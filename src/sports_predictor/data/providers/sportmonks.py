"""Optional Sportmonks Football API v3 fixture acquisition adapter.

The adapter only fetches source-attributed fixtures. It does not infer missing
participants, competition names, seasons, or kickoff timestamps.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sports_predictor.data.fixtures import FixtureRecord
from sports_predictor.data.models import DataSource


class SportmonksError(RuntimeError):
    """A sanitized Sportmonks API or response error."""


Requester = Callable[[str, dict[str, str], float], dict[str, Any]]


class SportmonksClient:
    """Small stdlib-only client for Sportmonks Football API v3."""

    provider_name = "sportmonks"
    base_url = "https://api.sportmonks.com/v3/football"

    def __init__(
        self,
        api_token: str,
        *,
        timeout: float = 20.0,
        requester: Requester | None = None,
    ) -> None:
        if not isinstance(api_token, str) or not api_token.strip():
            raise ValueError("Sportmonks API token is required")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._api_token = api_token.strip()
        self.timeout = timeout
        self._requester = requester or self._request_json

    @staticmethod
    def _request_json(url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise SportmonksError(f"Sportmonks returned HTTP {exc.code}") from None
        except URLError as exc:
            raise SportmonksError(f"Sportmonks connection failed: {exc.reason}") from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SportmonksError("Sportmonks returned an invalid JSON response") from None
        if not isinstance(payload, dict):
            raise SportmonksError("Sportmonks response must be a JSON object")
        return payload

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        query = urlencode(params)
        url = f"{self.base_url}/{path.lstrip('/')}?{query}"
        # Sportmonks documents the raw token in the Authorization header.
        return self._requester(
            url,
            {"Authorization": self._api_token, "Accept": "application/json"},
            self.timeout,
        )

    @staticmethod
    def _status(raw: dict[str, Any]) -> str:
        state = raw.get("state") or {}
        code = str(state.get("short_code") or state.get("developer_name") or "").upper()
        if code in {"NS", "TBA", "NOT_STARTED", "SCHEDULED"}:
            return "scheduled"
        if code in {"LIVE", "1H", "HT", "2H", "ET", "P", "INPLAY"}:
            return "live"
        if code in {"FT", "AET", "FT_PEN", "FINISHED"}:
            return "finished"
        if code in {"PST", "POSTPONED"}:
            return "postponed"
        if code in {"CANC", "CANCELLED", "CANCELED"}:
            return "cancelled"
        if code in {"ABD", "ABANDONED"}:
            return "abandoned"
        return "unknown"

    @staticmethod
    def _kickoff(raw: dict[str, Any]) -> datetime:
        timestamp = raw.get("starting_at_timestamp")
        if timestamp is not None:
            return datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
        value = raw.get("starting_at")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("fixture is missing starting_at_timestamp/starting_at")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # Requests explicitly ask Sportmonks for UTC when no timestamp is present.
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    @classmethod
    def normalize_fixture(
        cls, raw: dict[str, Any], *, retrieved_at: datetime, source_url: str
    ) -> FixtureRecord:
        participants = raw.get("participants")
        if not isinstance(participants, list):
            raise ValueError("fixture is missing included participants")
        home = away = None
        for participant in participants:
            if not isinstance(participant, dict):
                continue
            location = str((participant.get("meta") or {}).get("location", "")).lower()
            if location == "home":
                home = participant
            elif location == "away":
                away = participant
        if not home or not away or not home.get("name") or not away.get("name"):
            raise ValueError("fixture must contain one named home and away participant")

        league = raw.get("league") or {}
        season = raw.get("season") or {}
        round_info = raw.get("round") or {}
        venue = raw.get("venue") or {}
        country_info = league.get("country") or raw.get("country") or {}
        league_id = raw.get("league_id") or league.get("id")
        season_id = raw.get("season_id") or season.get("id")
        if league_id is None or season_id is None or not league.get("name"):
            raise ValueError("fixture is missing included league/season identity")

        return FixtureRecord(
            fixture_id=str(raw.get("id", "")),
            competition_id=str(league_id),
            competition_name=str(league["name"]),
            season=str(season.get("name") or season_id),
            kickoff=cls._kickoff(raw),
            home_team=str(home["name"]),
            away_team=str(away["name"]),
            status=cls._status(raw),
            country=str(country_info["name"]) if country_info.get("name") else None,
            matchday=str(round_info["name"]) if round_info.get("name") else None,
            venue=str(venue["name"]) if venue.get("name") else None,
            source=DataSource(
                provider=cls.provider_name,
                retrieved_at=retrieved_at,
                source_url=source_url,
                source_record_id=str(raw.get("id", "")),
            ),
        )

    def fetch_fixtures(self, date_from: str, date_to: str) -> list[FixtureRecord]:
        """Fetch every fixture in an inclusive date range, following API pagination."""
        start = date.fromisoformat(date_from)
        end = date.fromisoformat(date_to)
        if start > end:
            raise ValueError("date_from must be on or before date_to")

        records: list[FixtureRecord] = []
        retrieved_at = datetime.now(timezone.utc)
        page = 1
        while page <= 1000:
            path = f"fixtures/between/{start.isoformat()}/{end.isoformat()}"
            params = {
                "timezone": "UTC",
                "per_page": "50",
                "page": str(page),
                "include": "participants;league.country;season;state;round;venue",
            }
            payload = self._get(path, params)
            rows = payload.get("data")
            if not isinstance(rows, list):
                raise SportmonksError("Sportmonks fixture response is missing a data array")
            source_url = f"{self.base_url}/{path}"
            for row in rows:
                if not isinstance(row, dict):
                    raise SportmonksError("Sportmonks fixture data contains a non-object row")
                try:
                    records.append(self.normalize_fixture(
                        row, retrieved_at=retrieved_at, source_url=source_url
                    ))
                except (KeyError, TypeError, ValueError) as exc:
                    raise SportmonksError(f"Cannot normalize Sportmonks fixture: {exc}") from exc

            pagination = (payload.get("meta") or {}).get("pagination") or {}
            if not pagination.get("has_more") or not rows:
                return records
            page += 1
        raise SportmonksError("Sportmonks pagination exceeded the 1000-page safety limit")
