# Advanced football analysis

Sports Predictor interprets xG, xGA and xPTS tables without confusing volume, outcomes and model expectations.

## Metric conventions

The deterministic helper analyze_team_metrics uses these sign conventions:

| Differential | Formula | Positive interpretation |
|---|---|---|
| Finishing | Goals scored − xG | Scored more than expected |
| Defensive outcomes | xGA − goals conceded | Conceded fewer than expected |
| Points | Actual points − xPTS | Earned more points than expected |

The helper returns totals, per-match rates and a coarse status using a configurable tolerance. It does not infer whether over-performance is repeatable.

**Provider semantics matter:** xG, xGA and xPTS models differ. Screenshot colors are interpreted only when the source legend is known. Without a legend, preserve raw signs and mark color semantics unknown.

## Matchup interpretation

Compare each team's attacking xG rate with the opponent's xGA rate, ideally using venue-specific splits and opponent-adjusted samples. These metrics describe chance volume/quality, not a complete tactical model. Team news, goalkeeper performance, rest and tactical matchups require separately sourced evidence.

## Betting decision

A market probability is not a betting recommendation. A candidate requires decimal odds, timestamp and source. Compare model probability with market implied probability (remove overround when all outcomes are available), calculate EV and account for uncertainty. High probability at a poor price can have negative expected value.

The agent may present up to four candidates, but must not force three or four picks. Without odds or trustworthy data, give probability-based leans only and no stake. If no sufficient edge exists, recommend no bet.

## MCP

The MCP tool analyze_advanced_team_metrics exposes deterministic metric arithmetic. It does not fetch data or predict match outcomes.
