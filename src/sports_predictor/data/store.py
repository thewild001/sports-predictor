"""Append-only JSONL storage with duplicate detection by match and source."""
from __future__ import annotations
import json
from pathlib import Path
from sports_predictor.data.models import MatchRecord


class MatchStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def list(self) -> list[MatchRecord]:
        if not self.path.exists():
            return []
        records = []
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                records.append(MatchRecord.from_dict(json.loads(line)))
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"invalid dataset record at line {line_number}: {exc}") from exc
        return records

    def append(self, records: list[MatchRecord]) -> dict[str, int]:
        existing = self.list()
        keys = {(record.match_id, record.source.provider) for record in existing}
        added = skipped = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            for record in records:
                key = (record.match_id, record.source.provider)
                if key in keys:
                    skipped += 1
                    continue
                stream.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
                keys.add(key)
                added += 1
        return {"added": added, "skipped_duplicates": skipped}
