---
name: betting-value
description: Evaluate football odds against model probabilities and recommend no bet when edge is insufficient.
---

# Betting value assessment

1. Confirm market selection and decimal odds timestamp/source.
2. Obtain the selection probability from the prediction engine.
3. Call `evaluate_betting_value`; do not substitute bookmaker implied probability for model probability.
4. Explain probability edge, fair odds, expected value and risk.
5. Apply the configured minimum edge and bankroll constraints.
6. Recommend no bet if expected value is insufficient, inputs are stale or the market is not comparable.
7. Never describe a positive model edge as guaranteed profit.
