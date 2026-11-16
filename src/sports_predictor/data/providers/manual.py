"""Provider for user-supplied canonical JSON records."""
from __future__ import annotations
from typing import Any
from sports_predictor.data.models import MatchRecord


class ManualJSONProvider:
    provider_name = "manual"

    def normalize(self, payload: dict[str, Any]) -> list[MatchRecord]:
        rows = payload.get("matches", [payload])
        if not isinstance(rows, list):
            raise ValueError("payload.matches must be a list")
        records = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("each match must be a JSON object")
            records.append(MatchRecord.from_dict(row))
        return records
