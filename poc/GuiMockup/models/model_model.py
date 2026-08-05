"""Model repository: discovers available Ollama models from the local server.

Discovery (DESIGN.md §9): HTTP GET `http://127.0.0.1:11434/api/tags` at
startup; on failure fall back to `qwen2.5-coder:3b` and mark the server as
unreachable. Loaded lazily / anticipated by the previous step.
"""

from PySide6.QtCore import Property, QObject, Signal, Slot

import requests

_OLLAMA_URL = "http://127.0.0.1:11434/api/tags"
_FALLBACK = "qwen2.5-coder:3b"
_TIMEOUT_S = 2.0


class ModelModel(QObject):
    loaded = Signal()
    reachabilityChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[dict] = []
        self._reachable = True
        self.discover()

    # -- discovery ---------------------------------------------------------
    def discover(self) -> None:
        try:
            resp = requests.get(_OLLAMA_URL, timeout=_TIMEOUT_S)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            self._items = [{"name": m["name"], "label": m["name"]} for m in models]
            self._reachable = bool(models)
        except Exception:
            self._items = [{"name": _FALLBACK, "label": _FALLBACK}]
            self._reachable = False
        self.loaded.emit()
        self.reachabilityChanged.emit()

    # -- QML API -----------------------------------------------------------
    @Property(bool)
    def is_loaded(self) -> bool:
        return len(self._items) > 0

    @Slot(result=list)
    def names(self) -> list:
        return self._items

    @Slot()
    def refresh(self) -> None:
        self.discover()