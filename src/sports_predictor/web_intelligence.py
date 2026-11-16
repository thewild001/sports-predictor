"""HTTP client for the isolated Web Intelligence browser worker."""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class WebIntelligenceError(RuntimeError):
    """Raised when the browser worker is unavailable or rejects a request."""


class WebIntelligenceClient:
    def __init__(self, base_url: str | None = None, token: str | None = None,
                 timeout: float = 45.0) -> None:
        self.base_url = (base_url or os.getenv(
            "SPORTS_PREDICTOR_WEB_INTELLIGENCE_URL", "http://localhost:8787"
        )).rstrip("/")
        self.token = token if token is not None else os.getenv(
            "SPORTS_PREDICTOR_WEB_INTELLIGENCE_TOKEN", ""
        )
        self.timeout = timeout

    def _post(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(f"{self.base_url}{path}", data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            detail = getattr(exc, "reason", None) or str(exc)
            raise WebIntelligenceError(f"browser worker request failed: {detail}") from exc
        if not isinstance(result, dict):
            raise WebIntelligenceError("browser worker returned a non-object response")
        return result

    def browse(self, url: str, wait_until: str = "domcontentloaded") -> dict:
        """Navigate with Playwright and return bounded page text and metadata."""
        return self._post("/v1/browse", {"url": url, "wait_until": wait_until})

    def extract(self, url: str, instruction: str) -> dict:
        """Use the optional Stagehand extraction path on a page."""
        return self._post("/v1/extract", {"url": url, "instruction": instruction})
