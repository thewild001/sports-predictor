---
name: competition-discovery
description: Discover available football competitions and retrieve fixtures by competition, season, date range, and status through Sports Predictor MCP.
---

# Competition discovery

Use Sports Predictor MCP for competition and fixture discovery. Do not invent schedules or infer that an empty local catalogue means a competition has no upcoming matches.

## Workflow

1. Call `search_competitions` with the user's competition name or a short query. Include the season or country only when known or requested.
2. If multiple competitions or seasons match, ask the user to disambiguate before selecting one.
3. Call `get_competition_fixtures` using the exact `competition_id` returned by discovery. Pass date bounds when the user specifies a period; otherwise retrieve the next available catalogue entries.
4. Present kickoff timestamps with their timezone, status, matchday, and source provenance where available.
5. If no fixtures are returned, explain that the current Sports Predictor fixture catalogue has no matching records. Do not claim that the competition has no scheduled fixtures in the real world.
6. For match analysis, obtain or request the required statistics and odds. Fixture discovery alone does not provide xG, injuries, lineups, or betting prices.

## Data integrity

- Treat fixture IDs, competition IDs, season labels, and timestamps as source data.
- Distinguish kickoff time from source retrieval time.
- Never fabricate live data, odds, injuries, or team statistics.
- When source freshness is relevant, report the provider and retrieval timestamp.
- Do not claim FotMob is connected live; the current project supports normalized/imported fixture data only.
