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
