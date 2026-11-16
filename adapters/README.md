# Agent adapters

The shared interface is the local stdio MCP server `sports-predictor-mcp`; all business logic remains in `src/sports_predictor`. Agent-specific configuration is kept as examples and must not overwrite a user's existing config.

| Agent | Project configuration | Setup / verification |
|---|---|---|
| Claude Code | `.mcp.json` | `claude mcp add --transport stdio --scope project sports-predictor -- sports-predictor-mcp`; verify with `claude mcp list` |
| OpenCode | `opencode.json` | `opencode mcp list` |
| Cursor | `.cursor/mcp.json` | Restart Cursor and inspect MCP tools in Agent settings |
| Codex | `.codex/config.toml` | `codex mcp add sports-predictor -- sports-predictor-mcp`; verify with `codex mcp list` |
| Pi | `.pi/mcp.json` | `pi mcp list --json` |
| Hermes | `~/.hermes/config.yaml` | Add under `mcp_servers`, restart/reload and inspect MCP tools |

Configuration examples live in each subdirectory. They are snippets, not installer-managed user files. Merge them into existing configuration; never replace the whole file. The executable must be installed in the environment inherited by the agent.

## Validation levels

- **Protocol smoke test:** automated stdio handshake, tool discovery and prediction call in CI.
- **Client discovery check:** `python scripts/agent_smoke.py --client all` checks installed clients and runs native discovery commands where supported.
- **Human acceptance:** confirm that the server and expected tools are visible in each client's own MCP UI/session. Cursor and Hermes require this manual confirmation in the current harness.

The protocol test does not prove all six clients work. Mark a client as verified only after its native discovery check succeeds in a real installed client version.
