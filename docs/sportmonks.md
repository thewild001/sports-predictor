# Sportmonks provider

Sports Predictor includes an optional fixture-acquisition adapter for the documented Sportmonks Football API v3. It writes into the existing fixture catalogue; the prediction engine and other providers remain independent.

## Setup

1. Create an API token in [MySportmonks](https://my.sportmonks.com/).
2. Store it in the environment variable `SPORTS_PREDICTOR_SPORTMONKS_TOKEN`. Do not commit it, put it in a URL, or expose it to an agent's client-side configuration.
3. Install Sports Predictor with the MCP extra and restart the MCP server.

The adapter sends the token in the `Authorization` request header. It requests UTC kickoff values and follows the API's pagination metadata.

## MCP tool

`sync_sportmonks_fixtures(date_from, date_to)` fetches fixtures for an inclusive date range and appends them to `SPORTS_PREDICTOR_FIXTURES`. Use ISO dates (`YYYY-MM-DD`).

1. `search_competitions` to discover competition IDs and seasons now present in the local catalogue.
2. `get_competition_fixtures` to retrieve upcoming or historical fixtures for the selected competition.

The provider ID is the upstream Sportmonks league ID. Season is preserved separately. Every stored record contains the provider, upstream fixture ID, retrieval timestamp and a source URL without credentials. Duplicate observations from the same provider are skipped by the existing append-only store.

## Team season metrics

First call `get_sportmonks_season_teams(season_id)` to resolve the provider's numeric team IDs. Then use `get_sportmonks_team_season_metrics(team_id, season_id)` to retrieve completed-season metrics for one Sportmonks team ID. The adapter:

1. Reads the season boundaries from `GET /seasons/{season_id}`.
2. Retrieves that season's fixtures by league and date range with participants, final scores and `xGFixture`.
3. Aggregates xG for the selected team and xGA as the opponents' xG.
4. Reads actual points and xPTS from `GET /standings/seasons/{season_id}`, using expected-points type ID 7939.
5. Returns totals, per-match rates, home/away splits for match-derived metrics, provenance and the existing deterministic differential analysis.

Expected metric type IDs are xG=5304 and xPTS=7939. xPTS is only available at season/standing level in this integration, so no home/away xPTS split is reported. Cup seasons or grouped competitions that return multiple standing rows for the same team are rejected rather than silently combining stages. Incomplete xG coverage also fails closed: no misleading partial season aggregate is returned.

## Scope and limits

- Fixture synchronization and team season metrics are supported. This does not yet retrieve lineups, injuries or odds.
- Sportmonks coverage depends on the API subscription and competition. HTTP 403 generally means the token/plan cannot access the requested feed; 429 means rate limits have been reached.
- Sportmonks requires an xG Basic or xG Advanced add-on for xG values. Expected-points type 7939 must also be present in the season standings response. Never assume coverage for every competition.
- The adapter uses only the documented API v3 fixture range endpoint. It does not scrape the Sportmonks website or use undocumented endpoints.
- A successful fixture sync does not imply that statistical coverage is available for those matches.

See the official [xG endpoint](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/expected-xg), [team statistics guide](https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/statistics/team-statistics), [standings endpoint](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/standings/get-standings-by-season-id), and [expected type reference](https://docs.sportmonks.com/v3/definitions/types/expected). Also see the [official authentication guide](https://docs.sportmonks.com/v3/welcome/authentication), [fixtures reference](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/fixtures), and [expected data documentation](https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/expected).
