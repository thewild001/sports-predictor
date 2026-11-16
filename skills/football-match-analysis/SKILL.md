---
name: football-match-analysis
description: Analyze a football match using sourced data and transparent uncertainty.
---

# Football match analysis

1. Establish fixture identity, competition, kickoff and data freshness.
2. Inventory available statistics and label each as observed, inferred or missing.
3. Compare recent form only when sample size and time window are explicit.
4. Check home/away splits, expected goals, shots, possession and relevant lineup context only when sourced.
5. Call `predict_football_match` with explicit xG inputs; never invent xG.
6. Present 1X2, goals, BTTS and top scorelines with limitations.
7. State what additional evidence could materially change the forecast.
