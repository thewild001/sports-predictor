"""Tests for provider-neutral competition and fixture discovery."""
import json

import pytest

from sports_predictor.data.fixtures import FixtureRecord, FixtureStore, ingest_fixture_file
from sports_predictor.data.models import DataSource


def fixture(**overrides):
    values = {
        "fixture_id": "fixture-001",
        "competition_id": "laliga",
        "competition_name": "LaLiga",
        "season": "2026/27",
        "kickoff": "2026-11-20T20:00:00+01:00",
        "home_team": "Real Madrid",
        "away_team": "Sevilla",
        "source": {
            "provider": "manual",
            "retrieved_at": "2026-11-16T10:00:00+01:00",
            "source_url": "https://example.test/fixture-001",
            "source_record_id": "fixture-001",
        },
        "status": "scheduled",
        "country": "Spain",
        "matchday": "13",
    }
    values.update(overrides)
    return values


def test_fixture_rejects_naive_kickoff():
    with pytest.raises(ValueError, match="timezone"):
        FixtureRecord.from_dict(fixture(kickoff="2026-11-20T20:00:00"))


def test_import_search_and_filter_fixtures(tmp_path):
    source = tmp_path / "fixtures.json"
    source.write_text(json.dumps({"fixtures": [fixture(), fixture(
        fixture_id="fixture-002", home_team="Barcelona", away_team="Valencia",
        kickoff="2026-11-21T18:00:00+01:00",
    )]}), encoding="utf-8")
    store = FixtureStore(tmp_path / "fixtures.jsonl")

    assert ingest_fixture_file(source, store) == {"added": 2, "skipped_duplicates": 0}
    assert ingest_fixture_file(source, store) == {"added": 0, "skipped_duplicates": 2}

    competitions = store.search_competitions(query="liga", season="2026/27")
    assert len(competitions) == 1
    assert competitions[0]["fixture_count"] == 2

    matches = store.list_fixtures("laliga", date_from="2026-11-21", date_to="2026-11-21")
    assert len(matches) == 1
    assert matches[0]["fixture_id"] == "fixture-002"


def test_fixture_lookup_returns_latest_provider_observation(tmp_path):
    store = FixtureStore(tmp_path / "fixtures.jsonl")
    first = FixtureRecord.from_dict(fixture())
    second = FixtureRecord(
        fixture_id=first.fixture_id,
        competition_id=first.competition_id,
        competition_name=first.competition_name,
        season=first.season,
        kickoff=first.kickoff,
        home_team=first.home_team,
        away_team=first.away_team,
        source=DataSource.from_dict({
            "provider": "fotmob",
            "retrieved_at": "2026-11-16T11:00:00+01:00",
        }),
        status="live",
    )
    store.append([first, second])
    assert store.get_fixture("fixture-001")["status"] == "live"


def test_fixture_query_validates_limit_and_date_order(tmp_path):
    store = FixtureStore(tmp_path / "fixtures.jsonl")
    with pytest.raises(ValueError, match="limit"):
        store.list_fixtures("laliga", limit=101)
    with pytest.raises(ValueError, match="date_from"):
        store.list_fixtures("laliga", date_from="2026-11-22", date_to="2026-11-21")
