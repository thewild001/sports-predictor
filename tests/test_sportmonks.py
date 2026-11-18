from datetime import datetime, timezone

import pytest

from sports_predictor.data.providers.sportmonks import (
    SportmonksClient,
    SportmonksError,
)


def fixture_payload(fixture_id=123):
    return {
        "id": fixture_id,
        "league_id": 8,
        "season_id": 2026,
        "starting_at": "2026-11-20 19:00:00",
        "state": {"short_code": "NS"},
        "league": {"id": 8, "name": "Premier League", "country": {"name": "England"}},
        "season": {"id": 2026, "name": "2026/27"},
        "round": {"name": "Matchweek 12"},
        "venue": {"name": "Example Stadium"},
        "participants": [
            {"id": 1, "name": "Home FC", "meta": {"location": "home"}},
            {"id": 2, "name": "Away FC", "meta": {"location": "away"}},
        ],
    }


def test_fetch_fixtures_normalizes_records_and_uses_header_auth():
    calls = []

    def requester(url, headers, timeout):
        calls.append((url, headers, timeout))
        return {
            "data": [fixture_payload()],
            "meta": {"pagination": {"has_more": False}},
        }

    client = SportmonksClient("secret-token", requester=requester)
    records = client.fetch_fixtures("2026-11-20", "2026-11-21")

    assert len(records) == 1
    fixture = records[0]
    assert fixture.fixture_id == "123"
    assert fixture.competition_id == "8"
    assert fixture.competition_name == "Premier League"
    assert fixture.season == "2026/27"
    assert fixture.home_team == "Home FC"
    assert fixture.away_team == "Away FC"
    assert fixture.kickoff == datetime(2026, 11, 20, 19, 0, tzinfo=timezone.utc)
    assert fixture.status == "scheduled"
    assert fixture.source.provider == "sportmonks"
    assert fixture.source.source_record_id == "123"
    assert "secret-token" not in fixture.source.source_url
    assert calls[0][1]["Authorization"] == "secret-token"
    assert "api_token" not in calls[0][0]


def test_fetch_fixtures_follows_pagination():
    pages = iter([
        {"data": [fixture_payload(1)], "meta": {"pagination": {"has_more": True}}},
        {"data": [fixture_payload(2)], "meta": {"pagination": {"has_more": False}}},
    ])
    calls = []

    def requester(url, headers, timeout):
        calls.append(url)
        return next(pages)

    records = SportmonksClient("token", requester=requester).fetch_fixtures(
        "2026-11-20", "2026-11-20"
    )

    assert [item.fixture_id for item in records] == ["1", "2"]
    assert "page=1" in calls[0]
    assert "page=2" in calls[1]


def test_normalizer_rejects_missing_participants():
    raw = fixture_payload()
    raw.pop("participants")
    with pytest.raises(ValueError, match="participants"):
        SportmonksClient.normalize_fixture(
            raw,
            retrieved_at=datetime.now(timezone.utc),
            source_url="https://api.sportmonks.com/v3/football/fixtures",
        )


def test_date_range_must_be_valid_and_ordered():
    client = SportmonksClient("token", requester=lambda *_: {})
    with pytest.raises(ValueError):
        client.fetch_fixtures("2026-11-22", "2026-11-20")
    with pytest.raises(ValueError):
        client.fetch_fixtures("not-a-date", "2026-11-20")


def test_api_errors_are_not_allowed_to_leak_tokens():
    def requester(*_):
        raise SportmonksError("Sportmonks returned HTTP 403")

    client = SportmonksClient("super-secret", requester=requester)
    with pytest.raises(SportmonksError, match="403") as error:
        client.fetch_fixtures("2026-11-20", "2026-11-20")
    assert "super-secret" not in str(error.value)



def season_fixture(fixture_id, home_id, away_id, home_xg, away_xg, home_goals, away_goals):
    return {
        "id": fixture_id,
        "season_id": 2026,
        "league_id": 8,
        "state": {"short_code": "FT"},
        "participants": [
            {"id": home_id, "name": f"Team {home_id}", "meta": {"location": "home"}},
            {"id": away_id, "name": f"Team {away_id}", "meta": {"location": "away"}},
        ],
        "scores": [
            {"participant_id": home_id, "description": "CURRENT", "score": {"goals": home_goals}},
            {"participant_id": away_id, "description": "CURRENT", "score": {"goals": away_goals}},
        ],
        "expected": [
            {"participant_id": home_id, "type_id": 5304, "data": {"value": home_xg}},
            {"participant_id": away_id, "type_id": 5304, "data": {"value": away_xg}},
        ],
    }


def test_fetch_team_season_metrics_aggregates_xg_xga_and_xpts():
    home = season_fixture(100, 10, 20, 1.8, 0.7, 2, 0)
    away = season_fixture(101, 30, 10, 0.9, 1.4, 1, 1)

    def requester(url, headers, timeout):
        if "/seasons/2026?" in url:
            return {"data": {"id": 2026, "league_id": 8, "name": "2026/27",
                             "starting_at": "2026-08-01", "ending_at": "2027-05-31"}}
        if "/fixtures/between/" in url:
            return {"data": [home, away], "meta": {"pagination": {"has_more": False}}}
        if "/standings/seasons/2026?" in url:
            return {"data": [{
                "participant_id": 10, "points": 4,
                "participant": {"name": "Team 10"},
                "details": [{"type_id": 7939, "value": {"value": 3.2}}],
            }]}
        raise AssertionError(url)

    result = SportmonksClient("token", requester=requester).fetch_team_season_metrics(10, 2026)
    assert result["matches"] == 2
    assert result["totals"] == {
        "xg": 3.2, "goals_scored": 3.0, "xga": 1.6, "goals_conceded": 1.0,
        "xpts": 3.2, "points": 4.0,
    }
    assert result["home_away"]["home_matches"] == 1
    assert result["home_away"]["away_matches"] == 1
    assert result["home_away"]["home_xg"] == 1.8
    assert result["home_away"]["away_xg"] == 1.4
    assert result["differentials"]["finishing_goals_minus_xg"] == pytest.approx(-0.2)


def test_fetch_team_season_metrics_rejects_missing_xg_coverage():
    fixture = season_fixture(100, 10, 20, 1.8, 0.7, 2, 0)
    fixture["expected"] = [
        {"participant_id": 10, "type_id": 5304, "data": {"value": 1.8}}
    ]

    def requester(url, headers, timeout):
        if "/seasons/2026?" in url:
            return {"data": {"id": 2026, "league_id": 8, "name": "2026/27",
                             "starting_at": "2026-08-01", "ending_at": "2027-05-31"}}
        if "/fixtures/between/" in url:
            return {"data": [fixture], "meta": {"pagination": {"has_more": False}}}
        if "/standings/seasons/2026?" in url:
            return {"data": [{"participant_id": 10, "points": 3,
                              "details": [{"type_id": 7939, "value": 2.4}]}]}
        raise AssertionError(url)

    with pytest.raises(SportmonksError, match="xG coverage incomplete"):
        SportmonksClient("token", requester=requester).fetch_team_season_metrics(10, 2026)


def test_fetch_team_season_metrics_rejects_ambiguous_cup_standings():
    fixture = season_fixture(100, 10, 20, 1.8, 0.7, 2, 0)

    def requester(url, headers, timeout):
        if "/seasons/2026?" in url:
            return {"data": {"id": 2026, "league_id": 8, "name": "Cup",
                             "starting_at": "2026-08-01", "ending_at": "2027-05-31"}}
        if "/fixtures/between/" in url:
            return {"data": [fixture], "meta": {"pagination": {"has_more": False}}}
        if "/standings/seasons/2026?" in url:
            row = {"participant_id": 10, "points": 4,
                   "details": [{"type_id": 7939, "value": 3.2}]}
            return {"data": [row, row]}
        raise AssertionError(url)

    with pytest.raises(SportmonksError, match="exactly one standings row"):
        SportmonksClient("token", requester=requester).fetch_team_season_metrics(10, 2026)



def test_fetch_season_teams_returns_ids_and_follows_pagination():
    pages = iter([
        {"data": [{"id": 20, "name": "Away FC", "short_code": "AWY"}],
         "meta": {"pagination": {"has_more": True}}},
        {"data": [{"id": 10, "name": "Home FC", "short_code": "HME"}],
         "meta": {"pagination": {"has_more": False}}},
    ])
    calls = []

    def requester(url, headers, timeout):
        calls.append(url)
        return next(pages)

    teams = SportmonksClient("token", requester=requester).fetch_season_teams(2026)
    assert [team["team_id"] for team in teams] == [10, 20]
    assert [team["name"] for team in teams] == ["Home FC", "Away FC"]
    assert "page=1" in calls[0]
    assert "page=2" in calls[1]
