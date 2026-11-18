---
name: advanced-football-analysis
description: Analyze football teams and matchups using xG, xGA, xPTS, observed results, sourced context and calibrated market probabilities.
---

# Advanced football analysis

Use this workflow for match previews, advanced-statistics tables/images and conservative betting analysis.

## 1. Establish evidence
- Confirm fixture, competition, season, venue and kickoff.
- Accept screenshots, pasted tables and source pages. Ask for a clearer image only if a material value is unreadable.
- Record provider, source URL, retrieval time, sample size and metric definitions.
- Separate observed facts, model outputs, interpretation and unknowns.
- Do not mix xG/xGA/xPTS from incompatible providers or periods without warning.
- Identify whether the sample is home/away, league-only or all competitions.

## 2. Analyze each team
Use `get_sportmonks_season_teams(season_id)` to resolve Sportmonks team IDs, then `get_sportmonks_team_season_metrics(team_id, season_id)` to retrieve sourced season aggregates when the Sportmonks token and xG add-on are available. The provider method aggregates xG/xGA from completed fixtures and reads actual points/xPTS from season standings; it rejects incomplete xG coverage and ambiguous cup standings. Use the MCP tool `analyze_advanced_team_metrics` when numeric aggregates are available from other sources. Its explicit conventions are:
- Finishing: goals scored minus xG. Positive means more goals than expected; negative means fewer.
- Defensive outcomes: xGA minus goals conceded. Positive means fewer goals conceded than expected; negative means more.
- Points: actual points minus xPTS. Positive means more points than expected; negative means fewer.

Explain attacking volume from xG per match, not the finishing delta alone. Explain defensive exposure from xGA per match, not the defensive delta alone. A team can concede few goals but still allow high-quality chances.

For red/green screenshot differentials, follow the legend of that exact source. If no legend is visible, do not assume green always means positive or that a minus sign is bad. Report raw values and mark color semantics unknown.

Over/under-performance is descriptive, not proof of sustainable skill. xPTS definitions differ by provider.

## 3. Compare the matchup
- Compare home attack (xG rate and home split) against away defense (xGA rate and away split), then reverse.
- Consider pace, chance quality, finishing variance and goalkeeper evidence only when sourced.
- Include lineups, injuries, rest, travel and tactical context only when reliable evidence exists.
- State whether evidence leans open/high-scoring or closed/low-scoring, with counter-evidence.
- Never invent tactical style from a league-table row.

## 4. Probabilities before opinions
- Use the prediction engine with defensible match-level expected-goal inputs; never pass season xG totals as match xG.
- Prefer venue-adjusted and opponent-adjusted estimates. If unavailable, label the baseline provisional.
- Show supported 1X2, double chance, totals and BTTS probabilities.
- The most likely outcome is not automatically a value bet. Exact score is not a conservative market.

## 5. Betting candidates
- Present up to 3-4 candidates, not a forced quota. If evidence supports none, recommend no bet.
- For each, show model probability, decimal odds with timestamp/source, implied probability (remove margin when a complete market is available), edge, EV, confidence/data quality and principal risks.
- High hit probability can still have negative EV. Recommend a bet only when price and probability support positive EV after uncertainty and margin.
- Never invent odds. Without odds, label a probability-based lean, not a betting recommendation; no stake.
- Apply risk profile and bankroll only if supplied. Use the value engine for EV/stake.
- Conservative does not mean automatically selecting odds-on favourites.
- Explain invalidation triggers such as lineup changes, stale data, price movement or conflicting evidence.
- Recommend no bet when sample size, freshness, source quality or edge is inadequate.

## 6. Response structure
1. Fixture and data quality — competition, kickoff, source, timestamp, sample and missing inputs.
2. Team A / Team B — attack, defense, xPTS versus actual points; raw figures and deltas.
3. Matchup — attack-versus-defense, likely tempo/goal environment and counter-evidence.
4. Probabilities — supported market probabilities, model and assumptions.
5. Betting candidates — up to four ranked options; odds/EV/stake only when supported.
6. Conclusion — strongest supported view, invalidation factors or no bet.

Use concise professional Spanish when the user writes in Spanish. Use emojis sparingly as visual markers, not evidence. End with a brief reminder that betting involves risk and estimates are not guarantees.
