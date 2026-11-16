# Sports Predictor

**Agente de análisis deportivo y decisión de apuestas**, inicialmente especializado en fútbol.

Sports Predictor transforma estadísticas trazables en probabilidades, evalúa cuotas y permite medir decisiones en paper trading. El núcleo estadístico es independiente de las fuentes de datos y del agente de IA que lo utilice.

> **Estado: MVP ampliado.** Hay ingesta JSON con procedencia, backtesting por mercado/competición, calibración experimental, MCP, adaptadores de configuración y un dashboard HTML de paper trading. Todavía no hay descarga automática de FotMob, calibración fuera de muestra ni validación de los seis clientes en instalaciones reales.

## Capacidades

- Modelo Poisson independiente para 1X2, ambos marcan, líneas de goles y marcadores probables.
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

**FotMob:** el adaptador actual normaliza un sobre de datos previamente mapeado; no realiza peticiones automáticas ni depende de endpoints internos no documentados. Revisa [Data ingestion](docs/data-ingestion.md) antes de conectar una fuente real.

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
| `predict_football_match` | Predicción 1X2, BTTS, goles y marcadores |
| `evaluate_betting_value` | EV, cuota justa y stake limitado |
| `ingest_match_file` | Ingesta local con procedencia |
| `backtest_historical_matches` | Evaluación histórica y calibración |
| `record_paper_bet` | Registrar apuesta simulada |
| `settle_paper_bet` | Liquidar apuesta simulada |
| `paper_trading_summary` | Métricas del portafolio simulado |
| `export_paper_dashboard` | Exportar informe HTML |

Variables: `SPORTS_PREDICTOR_LEDGER` y `SPORTS_PREDICTOR_DATASET`.

## Integración con agentes

Se incluyen ejemplos de configuración y Skills para:

- Claude Code
- OpenCode
- Cursor
- Codex
- Pi
- Hermes

Consulta [Agent adapters](adapters/README.md) y [Agent integration](docs/agent-integration.md). Los ejemplos no sobrescriben configuraciones del usuario. La CI valida el protocolo MCP, pero **ninguno de los seis clientes debe considerarse verificado hasta ejecutar el smoke test en una instalación real**.

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
2. No existe todavía un fetcher FotMob ni integración de cuotas en vivo.
3. No hay entrenamiento con históricos ni calibración fuera de muestra automatizada.
4. La simulación ROI usa una unidad plana y cuotas aportadas; no ajusta margen de mercado ni mide closing-line value.
5. Las configuraciones de agentes requieren validación en las versiones instaladas por el usuario.
6. Los resultados son estimaciones, no garantías de rentabilidad. Si los datos son insuficientes o no hay valor, la decisión correcta es no apostar.

## Licencia

MIT.
