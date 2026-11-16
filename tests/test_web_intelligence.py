from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from sports_predictor.web_intelligence import WebIntelligenceClient, WebIntelligenceError


def test_browse_posts_to_worker_and_returns_payload():
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(
        {"title": "Example", "extraction_method": "playwright_dom"}
    ).encode()
    with patch("sports_predictor.web_intelligence.urlopen", return_value=response) as mocked:
        result = WebIntelligenceClient("http://worker", "secret").browse(
            "https://fotmob.com"
        )
    assert result["title"] == "Example"
    request = mocked.call_args.args[0]
    assert request.full_url == "http://worker/v1/browse"
    assert request.get_header("Authorization") == "Bearer secret"
    assert json.loads(request.data)["url"] == "https://fotmob.com"


def test_extract_uses_stagehand_endpoint():
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b'{"data":{"fields":[]}}'
    with patch("sports_predictor.web_intelligence.urlopen", return_value=response) as mocked:
        WebIntelligenceClient("http://worker").extract(
            "https://fbref.com", "Extract the team name"
        )
    assert mocked.call_args.args[0].full_url == "http://worker/v1/extract"


def test_worker_errors_are_wrapped():
    with patch("sports_predictor.web_intelligence.urlopen", side_effect=OSError("offline")):
        with pytest.raises(WebIntelligenceError, match="browser worker request failed"):
            WebIntelligenceClient("http://worker").browse("https://fotmob.com")
