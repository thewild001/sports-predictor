from datetime import datetime, timezone
import pytest
from sports_predictor.data.models import DataSource, MatchRecord
from sports_predictor.data.providers.fotmob import FotMobPayloadAdapter
from sports_predictor.data.store import MatchStore


def record(match_id="m-1"):
    return MatchRecord(
        match_id=match_id, competition="Premier League", season="2025/26",
        kickoff=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
        home_team="Home FC", away_team="Away FC", home_goals=2, away_goals=1,
        home_xg=1.7, away_xg=0.8,
        source=DataSource("fixture", datetime(2026, 1, 2, tzinfo=timezone.utc),
                          "https://example.test/match", match_id),
        odds={"home": 1.8, "draw": 3.5, "away": 4.5},
    )


def test_match_record_requires_timezone():
    with pytest.raises(ValueError, match="timezone"):
        MatchRecord("m", "League", "season", datetime(2026, 1, 1), "A", "B", 1, 0, 1.2, .8,
                    DataSource("manual", datetime.now(timezone.utc)))


def test_match_record_rejects_invalid_expected_goals():
    with pytest.raises(ValueError, match="home_xg"):
        MatchRecord("m", "League", "season", datetime.now(timezone.utc), "A", "B", 1, 0, 0, .8,
                    DataSource("manual", datetime.now(timezone.utc)))


def test_store_round_trip_and_duplicate_detection(tmp_path):
    store = MatchStore(tmp_path / "matches.jsonl")
    first = record()
    assert store.append([first]) == {"added": 1, "skipped_duplicates": 0}
    assert store.append([first]) == {"added": 0, "skipped_duplicates": 1}
    loaded = store.list()
    assert len(loaded) == 1
    assert loaded[0].source.provider == "fixture"
    assert loaded[0].kickoff == first.kickoff


def test_fotmob_adapter_requires_explicit_normalized_envelope():
    with pytest.raises(ValueError, match="missing fields"):
        FotMobPayloadAdapter().normalize({"id": "raw-upstream-shape"})


def test_fotmob_adapter_preserves_provenance():
    payload = {
        "match_id": "fm-1", "competition": "League", "season": "2025/26",
        "kickoff": "2026-01-01T15:00:00Z", "retrieved_at": "2026-01-02T12:00:00Z",
        "home_team": "Home", "away_team": "Away", "home_goals": 1, "away_goals": 0,
        "home_xg": 1.2, "away_xg": .6, "source_url": "https://www.fotmob.com/matches/example",
        "stats": {"shots": {"home": 10, "away": 4}},
    }
    result = FotMobPayloadAdapter().normalize(payload)[0]
    assert result.source.provider == "fotmob"
    assert result.source.source_url == payload["source_url"]
    assert result.stats["shots"]["home"] == 10
