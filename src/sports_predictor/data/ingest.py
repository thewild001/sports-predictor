"""File-based match ingestion with explicit provider selection."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from sports_predictor.data.providers.manual import ManualJSONProvider
from sports_predictor.data.providers.fotmob import FotMobPayloadAdapter
from sports_predictor.data.store import MatchStore

PROVIDERS = {"manual": ManualJSONProvider, "fotmob": FotMobPayloadAdapter}


def ingest_file(path: str | Path, store: MatchStore, provider: str = "manual") -> dict[str, int]:
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider '{provider}'; choose one of: {', '.join(PROVIDERS)}")
    payload: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    adapter = PROVIDERS[provider]()
    if isinstance(payload, list):
        records = []
        for row in payload:
            records.extend(adapter.normalize(row))
    elif isinstance(payload, dict):
        records = adapter.normalize(payload)
    else:
        raise ValueError("input JSON must contain an object or a list of objects")
    return store.append(records)
