# Backtesting and calibration

## Run

```bash
sports-predictor backtest --database sports-predictor-matches.jsonl
sports-predictor backtest --database sports-predictor-matches.jsonl --calibrate
sports-predictor backtest --database sports-predictor-matches.jsonl --minimum-edge 0.03
```

The engine reports log loss, normalized multiclass/binary Brier score and accuracy for 1X2, BTTS, Over 1.5, Over 2.5 and Over 3.5. Results are grouped by market and by competition/market. The simple value simulation uses supplied 1X2 decimal odds, selects at most one qualifying outcome per match and stakes one unit.

## Calibration

Temperature scaling is fitted independently for each competition/market group with at least ten labeled samples. This is a diagnostic baseline, not a substitute for a robust calibration study.

**Important:** the `--calibrate` option currently fits and evaluates on the same supplied dataset. Its scores are in-sample and optimistic; do not use them as evidence of future performance. For a valid experiment, split data chronologically: fit model/calibration on earlier seasons, tune on a later validation period, then report once on a final untouched test period.

## Interpretation

- Lower log loss and Brier score are better.
- Accuracy alone ignores probability quality and should not be the main optimization target.
- ROI is highly sensitive to sample size, odds quality, market margin and selection rules.
- Report confidence intervals and sample size before comparing strategies.
- Avoid leakage: features and odds must be captured before kickoff, not reconstructed from post-match sources.
- Backtesting is not a guarantee of future returns. Paper trading should follow historical validation.
