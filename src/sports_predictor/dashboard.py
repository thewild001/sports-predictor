"""Export a self-contained HTML dashboard for the paper-trading ledger."""
from __future__ import annotations
import html
import json
from pathlib import Path
from typing import Any
from sports_predictor.betting.metrics import summarize_bets


def render_dashboard(rows: list[dict[str, Any]]) -> str:
    metrics = summarize_bets(rows)
    table_rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in (
            row["event"], row["selection"], row["odds"], row["stake"], row["status"],
            row["profit"] if row["profit"] is not None else "—")) + "</tr>"
        for row in rows
    )
    cards = "".join(
        f"<article><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></article>"
        for label, value in [
            ("Apuestas", str(metrics["total_bets"])), ("Win rate", f'{metrics["win_rate"]:.1%}'),
            ("Beneficio neto", f'{metrics["net_profit"]:.2f}'),
            ("ROI", f'{metrics["roi"]:.1%}'), ("Drawdown máximo", f'{metrics["max_drawdown"]:.2f}'),
            ("Abiertas", str(metrics["open_bets"])),
        ])
    payload = json.dumps(metrics, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sports Predictor · Paper Trading</title>
<style>
:root{{color-scheme:dark;--bg:#0b1220;--panel:#121d30;--muted:#9aabc2;--line:#26364e;--ink:#edf3fb;--accent:#78dcca}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px system-ui,sans-serif}}
main{{max-width:1100px;margin:48px auto;padding:0 22px}}h1{{font-size:30px;margin-bottom:6px}}p{{color:var(--muted)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:28px 0}}
article,section{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}}
article span{{display:block;color:var(--muted);font-size:13px}}article strong{{display:block;font-size:25px;margin-top:8px}}
section{{overflow:auto}}table{{width:100%;border-collapse:collapse;white-space:nowrap}}th,td{{padding:12px;text-align:left;border-bottom:1px solid var(--line)}}th{{color:var(--muted);font-weight:600}}
small{{color:var(--muted)}}@media(max-width:600px){{main{{margin:24px auto}}h1{{font-size:24px}}}}
</style></head><body><main><h1>Sports Predictor</h1><p>Paper trading · métricas de seguimiento · sin ejecución de apuestas reales</p>
<div class="grid">{cards}</div><section><h2>Historial</h2><table><thead><tr><th>Evento</th><th>Selección</th><th>Cuota</th><th>Stake</th><th>Estado</th><th>Beneficio</th></tr></thead>
<tbody>{table_rows or '<tr><td colspan="6">Todavía no hay apuestas registradas.</td></tr>'}</tbody></table></section>
<p><small>Métricas calculadas sobre apuestas liquidadas. ROI = beneficio neto / importe apostado; drawdown calculado sobre la curva acumulada desde cero.</small></p>
<script type="application/json" id="metrics">{html.escape(payload)}</script></main></body></html>"""


def export_dashboard(rows: list[dict[str, Any]], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_dashboard(rows), encoding="utf-8")
    return path
