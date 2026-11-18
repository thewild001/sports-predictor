# Competition and fixture discovery

Sports Predictor separates fixture discovery from match prediction. The catalogue can identify competitions, seasons and scheduled matches even when no xG, odds or team statistics have been imported.

## MCP workflow

1. `search_competitions(query, season?, country?)` returns matching competition IDs and seasons represented in the local catalogue.
2. `get_competition_fixtures(competition_id, date_from?, date_to?, status?, limit?)` returns fixtures ordered by kickoff. Dates use `YYYY-MM-DD`; limit is capped at 100.
3. `get_fixture_details(fixture_id)` returns the latest stored source observation.
4. `ingest_fixture_file(file_path, provider?)` imports a JSON array or an object with a `fixtures` array.
5. `sync_sportmonks_fixtures(date_from, date_to)` fetches a date range from Sportmonks API v3 when `SPORTS_PREDICTOR_SPORTMONKS_TOKEN` is configured.

The fixture catalogue location is configured through `SPORTS_PREDICTOR_FIXTURES` (default `~/.sports-predictor/fixtures.jsonl`).

## Query semantics

- Resolve a competition first and use its exact `competition_id` for fixture retrieval.
- A competition is identified by `competition_id` plus `season`.
- Date filters are inclusive and use the kickoff's local calendar date.
- Fixture statuses: `scheduled`, `live`, `finished`, `postponed`, `cancelled`, `abandoned`, `unknown`.
- Repeated observations from different providers are collapsed to the most recently retrieved observation for fixture listing and detail lookup.
- The catalogue is append-only and deduplicates observations by `(fixture_id, provider)`; it does not silently overwrite prior source records.

## Provider boundary

This release does not contain a live fixture provider. Fixtures must be imported by a process or user that has obtained them through a permitted source. FotMob remains a normalization target for explicitly mapped payloads, not an active live connector. Do not claim that no real-world fixtures exist merely because a competition query returns no records.

A later provider adapter should implement the same canonical fixture contract and be reviewed for access conditions, rate limits, source attribution, timestamp quality and schema stability before being enabled.
