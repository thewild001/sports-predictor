# Data ingestion and provenance

## Canonical record

Every historical match is stored as one JSON object per line (JSONL). The canonical fields are:

```json
{
  "match_id": "league-2025-26-001",
  "competition": "Example League",
  "season": "2025/26",
  "kickoff": "2026-02-10T19:00:00Z",
  "home_team": "Home FC",
  "away_team": "Away FC",
  "home_goals": 2,
  "away_goals": 1,
  "home_xg": 1.65,
  "away_xg": 0.82,
  "odds": {"home": 1.85, "draw": 3.5, "away": 4.4},
  "stats": {},
  "source": {
    "provider": "manual",
    "retrieved_at": "2026-02-11T08:00:00Z",
    "source_url": "https://example.test/match/001",
    "source_record_id": "001"
  }
}
```

Input files are JSON objects or JSON arrays; imported records are persisted as JSONL, one record per line. All timestamps must be timezone-aware ISO-8601 values. xG must be in (0, 6], scores in [0, 30], and decimal odds greater than 1. Provider, match identity, competition, season and both teams are mandatory. Unknown values must not be replaced with guesses.

## Import

```bash
sports-predictor ingest ./matches.json --provider manual
sports-predictor ingest ./fotmob-normalized-match.json --provider fotmob
```

The importer deduplicates on (match_id, provider), appends to JSONL and reports skipped duplicates. It does not silently update existing rows; correct or supersede a record explicitly in a future version.

## FotMob boundary

FotMob does not expose a stable public API contract for this project to rely on. The current `FotMobPayloadAdapter` is a normalizer for a saved, explicitly mapped FotMob payload envelope; it does **not** fetch pages, scrape undocumented endpoints or bypass access controls. Keep the original page URL, retrieval time and upstream match identifier. A future fetch adapter must be added only after its access method, terms and schema stability are reviewed.

## Data quality checklist

- Verify fixture identity and competition/season.
- Keep source URL, provider, retrieval timestamp and upstream record ID.
- Distinguish event kickoff time from retrieval time.
- Avoid mixing xG from different providers without documenting the definition.
- Reject incomplete/contradictory records and investigate duplicate fixtures.
- Retain the raw source artifact separately when permitted by its terms.


## Fixture catalogue

Competition discovery uses a separate JSONL catalogue because a fixture can exist before any xG or result data is available. A fixture record requires source attribution and a timezone-aware kickoff:

```json
{
  "fixture_id": "provider-fixture-001",
  "competition_id": "laliga",
  "competition_name": "LaLiga",
  "country": "Spain",
  "season": "2026/27",
  "matchday": "13",
  "kickoff": "2026-11-20T20:00:00+01:00",
  "home_team": "Real Madrid",
  "away_team": "Sevilla",
  "status": "scheduled",
  "source": {
    "provider": "manual",
    "retrieved_at": "2026-11-16T10:00:00Z",
    "source_url": "https://example.test/fixture/provider-fixture-001",
    "source_record_id": "provider-fixture-001"
  }
}
```

Import a JSON array or an object containing a `fixtures` array with the MCP tool `ingest_fixture_file`. Each record must contain its own `source` metadata. The catalogue deduplicates on `(fixture_id, provider)`; queries collapse multiple provider observations to the latest retrieved record per fixture.

Set `SPORTS_PREDICTOR_FIXTURES` to change the JSONL catalogue location. The default is `~/.sports-predictor/fixtures.jsonl`.

The discovery API currently reads imported records only. It does not fetch FotMob or any other provider automatically, and an empty catalogue must never be presented as an empty real-world competition schedule.
