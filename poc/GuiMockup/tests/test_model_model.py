"""Tests for ModelModel — Ollama HTTP discovery + fallback."""

from unittest.mock import patch, MagicMock

import pytest

from models.model_model import ModelModel, _FALLBACK


@pytest.fixture
def model():
    return ModelModel(parent=None)


@pytest.fixture
def model_with_mock():
    """Model with mocked HTTP — no real Ollama call."""
    with patch("models.model_model.requests") as mock_requests:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "models": [
                {"name": "qwen2.5-coder:3b"},
                {"name": "llama3:8b"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_resp
        m = ModelModel(parent=None)
        yield m, mock_requests


class TestDiscover:
    def test_mocked_discover(self, model_with_mock):
        model, mock_req = model_with_mock
        names = [m["name"] for m in model.names()]
        assert "qwen2.5-coder:3b" in names
        assert "llama3:8b" in names
        mock_req.get.assert_called_once()

    def test_fallback_on_connection_error(self):
        with patch("models.model_model.requests") as mock_requests:
            mock_requests.get.side_effect = ConnectionError("refused")
            model = ModelModel(parent=None)
            names = [m["name"] for m in model.names()]
            assert names == [_FALLBACK]
            assert model._reachable is False

    def test_fallback_on_timeout(self):
        with patch("models.model_model.requests") as mock_requests:
            mock_requests.get.side_effect = Exception("timeout")
            model = ModelModel(parent=None)
            names = [m["name"] for m in model.names()]
            assert names == [_FALLBACK]
            assert model._reachable is False

    def test_fallback_on_empty_models(self):
        with patch("models.model_model.requests") as mock_requests:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"models": []}
            mock_resp.raise_for_status = MagicMock()
            mock_requests.get.return_value = mock_resp
            model = ModelModel(parent=None)
            # Empty models list means reachable=False, items=empty (not fallback)
            assert model._reachable is False
            assert len(model.names()) == 0

    def test_reachable_on_success(self, model_with_mock):
        model, _ = model_with_mock
        assert model._reachable is True


class TestIsLoaded:
    def test_always_loaded(self):
        """ModelModel always has at least the fallback."""
        with patch("models.model_model.requests") as mock_requests:
            mock_requests.get.side_effect = ConnectionError("refused")
            model = ModelModel(parent=None)
            assert model.is_loaded is True


class TestRefresh:
    def test_refresh_rescans(self):
        with patch("models.model_model.requests") as mock_requests:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"models": [{"name": "v1"}]}
            mock_resp.raise_for_status = MagicMock()
            mock_requests.get.return_value = mock_resp
            model = ModelModel(parent=None)
            assert len(model.names()) == 1

            mock_resp.json.return_value = {"models": [{"name": "v1"}, {"name": "v2"}]}
            model.refresh()
            assert len(model.names()) == 2
