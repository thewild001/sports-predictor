# Sports Predictor

**Agente de análisis deportivo y decisión de apuestas**, inicialmente especializado en fútbol.

Sports Predictor transforma estadísticas trazables en probabilidades, evalúa cuotas y permite medir decisiones en paper trading. El núcleo estadístico es independiente de las fuentes de datos y del agente de IA que lo utilice.

> **Estado: MVP ampliado.** Hay catálogo local, sincronización opcional de fixtures con Sportmonks, agregación de xG/xGA y xPTS por equipo/temporada, ingesta histórica, backtesting, MCP y paper trading. FotMob no se consulta automáticamente; la calibración sigue siendo in-sample y los seis clientes requieren validación real.

## Capacidades

- Modelo Poisson independiente para 1X2, ambos marcan, líneas de goles y marcadores probables.
- Análisis avanzado xG/xGA/xPTS con diferenciales explícitos y Skill especializada para matchup y mercados.
- Ingesta desde archivos JSON (objeto o lista) y almacenamiento histórico JSONL, con proveedor, URL de origen, ID upstream y timestamp de recuperación.
- Adaptador de normalización para payloads FotMob previamente guardados y mapeados; no scrapea endpoints no documentados.
- Backtesting con log loss, Brier score y accuracy para 1X2, BTTS y Over 1.5/2.5/3.5.
- Desglose de resultados por mercado y competición.
- Temperature scaling por competición/mercado con al menos diez observaciones.
- Evaluación de cuotas: probabilidad implícita, cuota justa, edge y valor esperado.
- Stake orientativo mediante Kelly fraccional con límites por perfil y bankroll.
- SQLite para paper trading, con ROI, win rate, beneficio neto y drawdown.
- Dashboard HTML autocontenido, sin servicios externos.
- CLI y servidor MCP local mediante stdio.

## Requisitos e instalación

Python 3.11 o superior.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev,mcp]"
```

El núcleo no requiere dependencias externas. Para instalar solo la CLI/núcleo: `pip install -e .`. Para MCP: `pip install -e ".[mcp]"`.

## Predicción

```bash
sports-predictor predict --home "Real Madrid" --away "Sevilla" --home-xg 1.8 --away-xg 0.9
sports-predictor evaluate --probability 0.60 --odds 2.0 --bankroll 1000 --profile balanced
```

Los xG del ejemplo son ilustrativos, no estadísticas reales. El modelo requiere xG suministrados por el usuario o por un proveedor integrado.

## Ingesta de datos

```bash
sports-predictor ingest ./matches.json --provider manual
sports-predictor ingest ./fotmob-normalized-match.json --provider fotmob
sports-predictor backtest --database sports-predictor-matches.jsonl
sports-predictor backtest --database sports-predictor-matches.jsonl --calibrate
```

Cada registro requiere fuente, timestamp de recuperación, competición, temporada, kickoff, equipos, goles y xG. Los timestamps deben incluir zona horaria. El almacén deduplica por `(match_id, provider)` y no sobrescribe silenciosamente registros existentes.

**FotMob:** el adaptador solo normaliza payloads previamente mapeados. FotMob ha solicitado que no se automatice el acceso sin autorización previa. Para fixtures en vivo se incorpora Sportmonks API v3 como proveedor opcional. Consulta [Data ingestion](docs/data-ingestion.md) y [Sportmonks provider](docs/sportmonks.md).

## Descubrimiento de competiciones y partidos

El catálogo de fixtures permite descubrir competiciones/temporadas y consultar sus partidos por rango de fechas y estado. La capa es independiente del proveedor y conserva proveedor, URL, ID upstream y timestamp de recuperación.

Los fixtures se importan desde JSON mediante `ingest_fixture_file` o se sincronizan desde Sportmonks mediante `sync_sportmonks_fixtures` (token y cobertura requeridos). Consulta [Competition discovery](docs/competition-discovery.md) y [Sportmonks provider](docs/sportmonks.md).

La ruta del catálogo se configura con `SPORTS_PREDICTOR_FIXTURES` y por defecto es `~/.sports-predictor/fixtures.jsonl`. Un catálogo vacío significa que no hay registros importados, no que la competición carezca de partidos reales.

## Backtesting y calibración

El informe incluye 1X2, BTTS y Over 1.5/2.5/3.5, agrupados por mercado y competición/mercado. La simulación de valor utiliza cuotas 1X2 aportadas y una unidad plana por selección.

La calibración actual se ajusta y evalúa sobre el mismo dataset cuando se activa `--calibrate`; por tanto, es **in-sample** y optimista. Para medir capacidad predictiva real hay que separar cronológicamente entrenamiento, validación y test final. Consulta [Backtesting](docs/backtesting.md).

## Paper trading y dashboard

El servidor MCP permite registrar y liquidar apuestas simuladas. No ejecuta apuestas reales ni requiere credenciales de casas de apuestas.

```bash
sports-predictor paper-summary
sports-predictor dashboard --output sports-predictor-dashboard.html
```

La base SQLite se guarda por defecto en `~/.sports-predictor/paper-trading.sqlite3`. Cambia la ruta con `SPORTS_PREDICTOR_LEDGER`. El dashboard muestra apuestas, win rate, ROI, beneficio neto, drawdown y abiertas.

## Servidor MCP

Ejecuta `sports-predictor-mcp` mediante transporte stdio. Herramientas expuestas:

| Herramienta | Propósito |
|---|---|
| `search_competitions` | Buscar competiciones y temporadas disponibles en el catálogo |
| `get_competition_fixtures` | Consultar partidos por competición, fecha y estado |
| `get_fixture_details` | Consultar el registro y procedencia de un fixture |
| `ingest_fixture_file` | Importar fixtures desde JSON al catálogo local |
| `analyze_advanced_team_metrics` | Diferenciales xG, xGA y xPTS con convenciones explícitas |
| `sync_sportmonks_fixtures` | Sincronizar fixtures desde Sportmonks API v3 |
| `get_sportmonks_season_teams` | Resolver IDs y nombres de equipos por temporada |
| `get_sportmonks_team_season_metrics` | Obtener xG/xGA/xPTS y diferenciales por equipo/temporada |
| `predict_football_match` | Predicción 1X2, BTTS, goles y marcadores |
| `evaluate_betting_value` | EV, cuota justa y stake limitado |
| `ingest_match_file` | Ingesta local con procedencia |
| `backtest_historical_matches` | Evaluación histórica y calibración |
| `record_paper_bet` | Registrar apuesta simulada |
| `settle_paper_bet` | Liquidar apuesta simulada |
| `paper_trading_summary` | Métricas del portafolio simulado |
| `export_paper_dashboard` | Exportar informe HTML |

Variables: `SPORTS_PREDICTOR_LEDGER`, `SPORTS_PREDICTOR_DATASET`, `SPORTS_PREDICTOR_FIXTURES` y `SPORTS_PREDICTOR_SPORTMONKS_TOKEN`.

## Integración con agentes

Se incluyen ejemplos de configuración y Skills para:

- Claude Code
- OpenCode
- Cursor
- Codex
- Pi
- Hermes

Consulta [Agent adapters](adapters/README.md), [Agent integration](docs/agent-integration.md) y la Skill [Advanced football analysis](skills/advanced-football-analysis/SKILL.md). Los ejemplos no sobrescriben configuraciones del usuario. La CI valida el protocolo MCP, pero **ninguno de los seis clientes debe considerarse verificado hasta ejecutar el smoke test en una instalación real**.

```bash
python scripts/agent_smoke.py --client all
```

## Tests y CI

```bash
pytest -q
ruff check src tests scripts
```

GitHub Actions ejecuta tests y lint en Python 3.11 y 3.12.

## Limitaciones conocidas

1. El modelo Poisson independiente es una línea base; no modela dependencia entre goles, alineaciones, lesiones ni contexto táctico.
2. El proveedor Sportmonks sincroniza fixtures y métricas de temporada, pero requiere token, cobertura y el complemento xG; no aporta todavía cuotas, alineaciones ni lesiones.
3. No hay entrenamiento con históricos ni calibración fuera de muestra automatizada.
4. La simulación ROI usa una unidad plana y cuotas aportadas; no ajusta margen de mercado ni mide closing-line value.
5. Las configuraciones de agentes requieren validación en las versiones instaladas por el usuario.
6. Los resultados son estimaciones, no garantías de rentabilidad. Si los datos son insuficientes o no hay valor, la decisión correcta es no apostar.

## Licencia

MIT.

## Web Intelligence

Sports Predictor incorpora un worker de navegador aislado en Docker. Playwright realiza navegación determinista y extracción del DOM; Stagehand es opcional para extracción estructurada asistida por un modelo. El proceso MCP se comunica con el worker por HTTP autenticado y puede apuntar a un endpoint remoto compatible.

```bash
cp .env.web-intelligence.example .env
# Configura SPORTS_PREDICTOR_WEB_INTELLIGENCE_TOKEN y dominios permitidos.
docker compose --env-file .env -f docker-compose.web-intelligence.yml up --build -d
```

Nuevas herramientas MCP: `browse_web_page` y `extract_web_page`. La segunda requiere habilitar Stagehand y configurar un modelo. El worker aplica allow-list de dominios, límites de tamaño/tiempo y publica en loopback por defecto.

Esta capacidad recupera evidencia web, pero **no es todavía un adaptador específico de FotMob/SofaScore ni convierte automáticamente páginas en estadísticas canónicas**. Consulta [Web Intelligence](docs/web-intelligence.md) antes de habilitarla.


## Advanced football analysis

La Skill [advanced-football-analysis](skills/advanced-football-analysis/SKILL.md) guía el análisis individual de ambos equipos, el cruce xG/xGA, xPTS frente a puntos reales y la evaluación de hasta cuatro mercados. Puede trabajar con capturas aportadas por el usuario o datos recuperados de fuentes. La herramienta MCP `analyze_advanced_team_metrics` calcula diferenciales reproducibles: goles−xG, xGA−goles recibidos y puntos−xPTS. `sync_sportmonks_fixtures` sincroniza fixtures de un rango de fechas cuando existe token y cobertura.

El agente no fuerza cuatro apuestas: exige cuotas trazables para calcular EV y stake, distingue probabilidad alta de valor esperado y recomienda no apostar cuando no existe evidencia o ventaja suficiente. Los colores de una tabla solo se interpretan si se conoce su leyenda. Consulta [Advanced football analysis](docs/advanced-football-analysis.md).
