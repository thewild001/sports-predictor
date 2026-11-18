# Sportmonks provider

Sports Predictor includes an optional fixture-acquisition adapter for the documented Sportmonks Football API v3. It writes into the existing fixture catalogue; the prediction engine and other providers remain independent.

## Setup

1. Create an API token in [MySportmonks](https://my.sportmonks.com/).
2. Store it in the environment variable `SPORTS_PREDICTOR_SPORTMONKS_TOKEN`. Do not commit it, put it in a URL, or expose it to an agent's client-side configuration.
3. Install Sports Predictor with the MCP extra and restart the MCP server.

The adapter sends the token in the `Authorization` request header. It requests UTC kickoff values and follows the API's pagination metadata.

## MCP tool

`sync_sportmonks_fixtures(date_from, date_to)` fetches fixtures for an inclusive date range and appends them to `SPORTS_PREDICTOR_FIXTURES`. Use ISO dates (`YYYY-MM-DD`). Then call:

1. `search_competitions` to discover competition IDs and seasons now present in the local catalogue.
2. `get_competition_fixtures` to retrieve upcoming or historical fixtures for the selected competition.

The provider ID is the upstream Sportmonks league ID. Season is preserved separately. Every stored record contains the provider, upstream fixture ID, retrieval timestamp and a source URL without credentials. Duplicate observations from the same provider are skipped by the existing append-only store.

## Scope and limits

- This first integration synchronizes fixtures only. It does not yet retrieve standings, team season statistics, xG/xGA/xPTS aggregates, lineups, injuries or odds.
- Sportmonks coverage depends on the API subscription and competition. HTTP 403 generally means the token/plan cannot access the requested feed; 429 means rate limits have been reached.
- Sportmonks documents xG data as a paid add-on, and its expected-points table is available through standings details. Do not assume those feeds are included in a basic plan or covered for every competition.
- The adapter uses only the documented API v3 fixture range endpoint. It does not scrape the Sportmonks website or use undocumented endpoints.
- A successful fixture sync does not imply that statistical coverage is available for those matches.

See the [official authentication guide](https://docs.sportmonks.com/v3/welcome/authentication), [fixtures reference](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/fixtures), and [expected data documentation](https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/expected).
