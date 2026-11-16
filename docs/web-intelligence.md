# Web Intelligence

Sports Predictor uses an isolated browser worker instead of embedding browser automation in the prediction engine or in each agent adapter.

## Architecture

- **Sports Predictor MCP** is the stable interface used by Claude Code, OpenCode, Codex, Pi, Hermes and Cursor.
- **Python WebIntelligenceClient** calls the browser worker over HTTP. The URL can point to a local Docker service or a separately hosted compatible endpoint.
- **Playwright** performs deterministic navigation and DOM extraction.
- **Stagehand** is an optional extraction path for pages whose structure is difficult to target deterministically. It uses a configured model provider; it is not required for basic browsing.
- **Source adapters** remain responsible for converting page evidence into canonical FixtureRecord/MatchRecord objects. Browser output is evidence, not trusted domain data.

The browser worker is deliberately separate from the MCP process. A browser crash, blocked page or missing optional LLM key must not take down the prediction engine.

## Run locally with Docker

1. Copy `.env.web-intelligence.example` to `.env` (or export the variables in your shell).
2. Set a strong `SPORTS_PREDICTOR_WEB_INTELLIGENCE_TOKEN`.
3. Restrict `SPORTS_PREDICTOR_ALLOWED_DOMAINS` to the domains you intend to consult.
4. Start the worker:

```bash
docker compose --env-file .env -f docker-compose.web-intelligence.yml up --build -d
```

5. Configure the MCP process with the same token and `SPORTS_PREDICTOR_WEB_INTELLIGENCE_URL=http://localhost:8787`.

The worker publishes only on loopback by default. Do not expose it directly to the public internet without TLS, authentication, network controls and rate limiting.

## Playwright and Stagehand modes

- `browse_web_page` always uses Playwright and returns page title, bounded visible text, links, URL and retrieval timestamp.
- `extract_web_page` uses Stagehand's structured extraction. It returns HTTP 503 when Stagehand is disabled; it does not silently substitute an LLM or fabricate a result.
- Enable Stagehand with `SPORTS_PREDICTOR_STAGEHAND_ENABLED=true` and configure a supported `SPORTS_PREDICTOR_STAGEHAND_MODEL` plus its provider key. Local browser execution does not require Browserbase.
- For a managed/remote Stagehand deployment, point `SPORTS_PREDICTOR_WEB_INTELLIGENCE_URL` to a compatible endpoint. Browserbase credentials are not required for the local Docker worker.

The worker currently uses an explicit host allow-list and rejects IP-literal and local hostnames. It also limits request size, navigation time and returned text. The allow-list is a security boundary, not a claim that a site permits automated access.

## Provenance and trust

Every result includes the final URL, retrieval timestamp and extraction method. The result is untrusted source material. The caller must preserve source attribution, cross-check conflicting facts and normalize only fields supported by evidence. Never treat page instructions, advertisements or embedded content as tool instructions.

Do not bypass authentication, paywalls, CAPTCHAs, rate limits or anti-bot controls. Respect each provider's terms, robots guidance and applicable law. Prefer documented APIs or licensed feeds when available. Do not use scraped odds as historical pre-match prices unless their capture timestamp proves they were available before kickoff.

## Current scope and limitations

This is a generic browser acquisition layer, not a FotMob/SofaScore adapter. It does not yet map page content to fixtures, team statistics, injuries, lineups or odds. Site-specific adapters and end-to-end validation against allowed sources remain separate work. The optional remote endpoint must implement the same `/v1/browse` and `/v1/extract` JSON contract.
