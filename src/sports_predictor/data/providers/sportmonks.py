"""Optional Sportmonks Football API v3 fixture acquisition adapter.

The adapter only fetches source-attributed fixtures. It does not infer missing
participants, competition names, seasons, or kickoff timestamps.
"""
from __future__ import annotations

import json
import math
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



    def fetch_season_teams(self, season_id: int) -> list[dict[str, Any]]:
        """Return provider team IDs and names for a season, following pagination."""
        if isinstance(season_id, bool) or not isinstance(season_id, int) or season_id < 1:
            raise ValueError("season_id must be a positive integer")
        teams: dict[str, dict[str, Any]] = {}
        page = 1
        while page <= 1000:
            payload = self._get(
                f"teams/seasons/{season_id}",
                {"per_page": "50", "page": str(page)},
            )
            rows = payload.get("data")
            if not isinstance(rows, list):
                raise SportmonksError("Sportmonks teams response is missing a data array")
            for row in rows:
                if not isinstance(row, dict) or row.get("id") is None or not row.get("name"):
                    raise SportmonksError("Sportmonks teams response contains an invalid team")
                teams[str(row["id"])] = {
                    "team_id": int(row["id"]),
                    "name": str(row["name"]),
                    "short_code": row.get("short_code"),
                    "country_id": row.get("country_id"),
                }
            pagination = (payload.get("meta") or {}).get("pagination") or {}
            if not pagination.get("has_more") or not rows:
                return sorted(teams.values(), key=lambda team: team["name"].casefold())
            page += 1
        raise SportmonksError("Sportmonks team pagination exceeded the 1000-page safety limit")

    @staticmethod
    def _score_by_participant(raw: dict[str, Any]) -> dict[str, int]:
        scores = raw.get("scores")
        if not isinstance(scores, list):
            raise ValueError("completed fixture is missing scores")
        current = [
            item for item in scores
            if isinstance(item, dict)
            and str(item.get("description", "")).upper() in {"CURRENT", "FT", "FULL_TIME"}
        ]
        result: dict[str, int] = {}
        for item in current:
            participant_id = item.get("participant_id")
            score = item.get("score") or {}
            goals = score.get("goals") if isinstance(score, dict) else None
            if participant_id is None or isinstance(goals, bool) or not isinstance(goals, int):
                continue
            result[str(participant_id)] = goals
        if len(result) != 2:
            raise ValueError("fixture does not contain one final score for each participant")
        return result

    @staticmethod
    def _expected_by_participant(raw: dict[str, Any]) -> dict[str, float]:
        expected = raw.get("expected")
        if not isinstance(expected, list):
            raise ValueError("fixture is missing xG expected values")
        result: dict[str, float] = {}
        for item in expected:
            if not isinstance(item, dict) or str(item.get("type_id")) != "5304":
                continue
            participant_id = item.get("participant_id")
            data = item.get("data") or {}
            value = data.get("value") if isinstance(data, dict) else None
            if participant_id is None or isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if not math.isfinite(float(value)) or float(value) < 0:
                raise ValueError("fixture contains an invalid xG value")
            key = str(participant_id)
            if key in result:
                raise ValueError("fixture contains duplicate xG values for one participant")
            result[key] = float(value)
        if len(result) != 2:
            raise ValueError("fixture does not contain xG values for both participants")
        return result

    @staticmethod
    def _standing_xpts(row: dict[str, Any]) -> float:
        details = row.get("details")
        if not isinstance(details, list):
            raise ValueError("standing row is missing details required for xPTS")
        matches = [
            detail for detail in details
            if isinstance(detail, dict) and str(detail.get("type_id")) == "7939"
        ]
        if len(matches) != 1:
            raise ValueError("standing row must contain exactly one xPTS detail (type_id 7939)")
        value = matches[0].get("value")
        if isinstance(value, dict):
            value = value.get("value", value.get("total"))
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("standing xPTS value is not numeric")
        if not math.isfinite(float(value)) or float(value) < 0:
            raise ValueError("standing xPTS value is invalid")
        return float(value)

    def fetch_team_season_metrics(self, team_id: int, season_id: int) -> dict[str, Any]:
        """Aggregate a team's completed-season xG/xGA and reconcile standings xPTS.

        The API season and standings endpoints are authoritative for season boundaries
        and points. Fixture xG is aggregated only when both participants have values.
        """
        if isinstance(team_id, bool) or not isinstance(team_id, int) or team_id < 1:
            raise ValueError("team_id must be a positive integer")
        if isinstance(season_id, bool) or not isinstance(season_id, int) or season_id < 1:
            raise ValueError("season_id must be a positive integer")

        retrieved_at = datetime.now(timezone.utc)
        season_response = self._get(f"seasons/{season_id}", {})
        season = season_response.get("data")
        if not isinstance(season, dict):
            raise SportmonksError("Sportmonks season response is missing data")
        start = season.get("starting_at")
        end = season.get("ending_at")
        if not isinstance(start, str) or not isinstance(end, str):
            raise SportmonksError("Sportmonks season response is missing starting_at/ending_at")
        league_id = season.get("league_id")
        if league_id is None:
            raise SportmonksError("Sportmonks season response is missing league_id")
        start_date = date.fromisoformat(start[:10])
        end_date = date.fromisoformat(end[:10])
        if start_date > end_date:
            raise SportmonksError("Sportmonks season date range is invalid")

        fixture_rows: list[dict[str, Any]] = []
        page = 1
        while page <= 1000:
            path = f"fixtures/between/{start_date.isoformat()}/{end_date.isoformat()}"
            params = {
                "timezone": "UTC",
                "per_page": "50",
                "page": str(page),
                "include": "participants;scores;state;xGFixture",
                "filters": f"fixtureLeagues:{league_id}",
            }
            payload = self._get(path, params)
            rows = payload.get("data")
            if not isinstance(rows, list):
                raise SportmonksError("Sportmonks season fixture response is missing a data array")
            fixture_rows.extend(row for row in rows if isinstance(row, dict))
            pagination = (payload.get("meta") or {}).get("pagination") or {}
            if not pagination.get("has_more") or not rows:
                break
            page += 1
        else:
            raise SportmonksError("Sportmonks pagination exceeded the 1000-page safety limit")

        season_fixtures = [
            row for row in fixture_rows
            if str(row.get("season_id")) == str(season_id)
            and str(row.get("league_id")) == str(season.get("league_id"))
        ]
        unique_fixtures = {str(row.get("id")): row for row in season_fixtures if row.get("id") is not None}
        selected: list[dict[str, Any]] = []
        for row in unique_fixtures.values():
            participants = row.get("participants")
            if not isinstance(participants, list):
                continue
            if any(
                isinstance(participant, dict) and str(participant.get("id")) == str(team_id)
                for participant in participants
            ):
                if self._status(row) == "finished":
                    selected.append(row)

        if not selected:
            raise SportmonksError("No completed fixtures found for this team and season")

        standings_response = self._get(
            f"standings/seasons/{season_id}",
            {"include": "participant;details"},
        )
        standings = standings_response.get("data")
        if not isinstance(standings, list):
            raise SportmonksError("Sportmonks standings response is missing a data array")
        team_rows = [
            row for row in standings
            if isinstance(row, dict) and str(row.get("participant_id")) == str(team_id)
        ]
        if len(team_rows) != 1:
            raise SportmonksError(
                "Expected exactly one standings row for this team; cup/group formats may need stage selection"
            )
        standing = team_rows[0]
        points = standing.get("points")
        if isinstance(points, bool) or not isinstance(points, (int, float)) or points < 0:
            raise SportmonksError("Sportmonks standings row is missing valid actual points")
        try:
            xpts = self._standing_xpts(standing)
        except ValueError as exc:
            raise SportmonksError(str(exc)) from exc

        totals = {
            "xg": 0.0, "goals_scored": 0.0, "xga": 0.0, "goals_conceded": 0.0,
            "home_xg": 0.0, "away_xg": 0.0, "home_xga": 0.0, "away_xga": 0.0,
            "home_goals_scored": 0.0, "away_goals_scored": 0.0,
            "home_goals_conceded": 0.0, "away_goals_conceded": 0.0,
            "home_points": 0.0, "away_points": 0.0,
        }
        missing_xg: list[str] = []
        for row in selected:
            participants = row["participants"]
            team = next(
                item for item in participants
                if isinstance(item, dict) and str(item.get("id")) == str(team_id)
            )
            opponent = next(
                item for item in participants
                if isinstance(item, dict) and str(item.get("id")) != str(team_id)
            )
            try:
                scores = self._score_by_participant(row)
                expected = self._expected_by_participant(row)
            except ValueError as exc:
                if "xG" in str(exc):
                    missing_xg.append(str(row.get("id")))
                    continue
                raise SportmonksError(f"Invalid completed fixture {row.get('id')}: {exc}") from exc

            team_key, opponent_key = str(team_id), str(opponent["id"])
            if team_key not in scores or opponent_key not in scores:
                raise SportmonksError(f"Fixture {row.get('id')} scores do not match participant IDs")
            team_goals, opponent_goals = scores[team_key], scores[opponent_key]
            team_xg, opponent_xg = expected[team_key], expected[opponent_key]
            location = str((team.get("meta") or {}).get("location", "")).lower()
            if location not in {"home", "away"}:
                raise SportmonksError(f"Fixture {row.get('id')} has no home/away metadata for the team")

            totals["xg"] += team_xg
            totals["goals_scored"] += team_goals
            totals["xga"] += opponent_xg
            totals["goals_conceded"] += opponent_goals
            totals[f"{location}_xg"] += team_xg
            totals[f"{location}_xga"] += opponent_xg
            totals[f"{location}_goals_scored"] += team_goals
            totals[f"{location}_goals_conceded"] += opponent_goals
            totals[f"{location}_points"] += 3 if team_goals > opponent_goals else 1 if team_goals == opponent_goals else 0

        if missing_xg:
            raise SportmonksError(
                f"xG coverage incomplete for {len(missing_xg)} of {len(selected)} completed fixtures; "
                "no season aggregate was returned"
            )
        matches = len(selected)
        match_points = totals["home_points"] + totals["away_points"]
        try:
            from sports_predictor.analysis.team_metrics import analyze_team_metrics
            analysis = analyze_team_metrics(
                str((standing.get("participant") or {}).get("name") or f"Team {team_id}"),
                matches=matches,
                xg=totals["xg"],
                goals_scored=totals["goals_scored"],
                xga=totals["xga"],
                goals_conceded=totals["goals_conceded"],
                xpts=xpts,
                points=float(points),
            )
        except ValueError as exc:
            raise SportmonksError(f"Cannot analyze Sportmonks team metrics: {exc}") from exc

        return {
            "provider": self.provider_name,
            "team_id": team_id,
            "team": analysis["team"],
            "competition_id": str(season.get("league_id")),
            "season_id": season_id,
            "season": season.get("name"),
            "matches": matches,
            "match_points_from_results": match_points,
            "standing_points_adjustment": float(points) - match_points,
            "totals": {
                "xg": totals["xg"], "goals_scored": totals["goals_scored"],
                "xga": totals["xga"], "goals_conceded": totals["goals_conceded"],
                "xpts": xpts, "points": float(points),
            },
            "per_match": analysis["per_match"],
            "home_away": {
                "home_matches": sum(
                    1 for row in selected
                    if any(isinstance(p, dict) and str(p.get("id")) == str(team_id)
                           and str((p.get("meta") or {}).get("location", "")).lower() == "home"
                           for p in row.get("participants", []))
                ),
                "away_matches": sum(
                    1 for row in selected
                    if any(isinstance(p, dict) and str(p.get("id")) == str(team_id)
                           and str((p.get("meta") or {}).get("location", "")).lower() == "away"
                           for p in row.get("participants", []))
                ),
                **{key: value for key, value in totals.items() if key.startswith(("home_", "away_"))},
            },
            "differentials": analysis["differentials"],
            "assessment": analysis["assessment"],
            "limitations": analysis["limitations"] + [
                "xPTS is a season-level standings value and is not split home/away.",
                "Only completed fixtures with xG for both participants are included.",
            ],
            "source": {
                "provider": self.provider_name,
                "retrieved_at": retrieved_at.isoformat(),
                "season_url": f"{self.base_url}/seasons/{season_id}",
                "fixtures_url": f"{self.base_url}/fixtures/between/{start_date}/{end_date}",
                "standings_url": f"{self.base_url}/standings/seasons/{season_id}",
                "expected_goals_type_id": 5304,
                "expected_points_type_id": 7939,
            },
        }

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
