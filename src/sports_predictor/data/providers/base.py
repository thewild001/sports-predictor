"""Provider interface for match-data adapters."""
from __future__ import annotations
from typing import Any, Protocol
from sports_predictor.data.models import MatchRecord


class MatchDataProvider(Protocol):
    provider_name: str

    def normalize(self, payload: dict[str, Any]) -> list[MatchRecord]:
        """Convert provider payload into validated canonical match records."""
        ...
