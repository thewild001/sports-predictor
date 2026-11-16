"""Protocol-level MCP smoke test; client-specific GUI/CLI checks remain manual."""
import asyncio
import os
import sys

import pytest


def test_stdio_mcp_server_exposes_tools(tmp_path):
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def run():
        env = os.environ.copy()
        env["SPORTS_PREDICTOR_LEDGER"] = str(tmp_path / "paper.sqlite3")
        env["SPORTS_PREDICTOR_DATASET"] = str(tmp_path / "matches.jsonl")
        env["SPORTS_PREDICTOR_FIXTURES"] = str(tmp_path / "fixtures.jsonl")
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "sports_predictor.mcp.server"], env=env
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert {
                    "search_competitions", "get_competition_fixtures", "get_fixture_details",
                    "ingest_fixture_file", "predict_football_match", "evaluate_betting_value",
                    "record_paper_bet", "settle_paper_bet", "backtest_historical_matches",
                    "paper_trading_summary",
                } <= names
                result = await session.call_tool("search_competitions", {"query": "LaLiga"})
                assert not result.isError

    asyncio.run(run())
