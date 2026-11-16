# Agent integration

Sports Predictor exposes one local stdio MCP server. Keep calculation, validation and persistence in the Python package; client adapters should only configure the transport and provide agent instructions.

## Install and run

```bash
pip install -e ".[mcp]"
sports-predictor-mcp
```

The process communicates over stdio. Do not print logs or banners to stdout; reserve stdout for MCP protocol messages.

## Tool surface

- `search_competitions`
- `get_competition_fixtures`
- `get_fixture_details`
- `ingest_fixture_file`
- `predict_football_match`
- `evaluate_betting_value`
- `ingest_match_file`
- `backtest_historical_matches`
- `record_paper_bet`
- `settle_paper_bet`
- `paper_trading_summary`
- `export_paper_dashboard`

The historical dataset, paper ledger and fixture catalogue paths can be overridden with `SPORTS_PREDICTOR_DATASET`, `SPORTS_PREDICTOR_LEDGER` and `SPORTS_PREDICTOR_FIXTURES`.

## Competition discovery workflow

1. Import source-attributed fixture JSON using `ingest_fixture_file`. The path must be readable by the MCP server process.
2. Call `search_competitions` to resolve the exact competition ID and season.
3. Call `get_competition_fixtures` with that ID and optional ISO dates (`YYYY-MM-DD`).
4. Call `get_fixture_details` to inspect the latest stored observation and provenance.

This is a local catalogue, not a live schedule feed. A missing fixture is not evidence that no real-world fixture exists. See [Competition discovery](competition-discovery.md).

## Client configuration

Use the examples in `adapters/`. Claude Code, OpenCode, Cursor, Codex, Pi and Hermes use different configuration locations and sometimes different MCP config formats. Merge the matching snippet into the existing client configuration; never overwrite a user's whole settings file.

## Verification

1. Run `pytest -q` to execute the MCP stdio handshake smoke test.
2. Run `python scripts/agent_smoke.py --client all` to discover installed clients and invoke supported native MCP list commands.
3. In each client, verify that the server connects and that the expected tool names appear.
4. Call `predict_football_match` once with test inputs and inspect the returned JSON.

The CI protocol test validates the MCP server, not every host application's implementation. Client support remains provisional until step 3 has been performed on a real installed version.
