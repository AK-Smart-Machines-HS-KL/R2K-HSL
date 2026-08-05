"""Scenario repository: discovers scenario files from `core/src/scenario/`.

Discovery rules (DESIGN.md §9):
- packages: `scenario/<name>/scenario.json` take priority
- flat:      `scenario/<name>.json`, skipped if a package of the same name exists
- label:     from the package's analysis.md H1, else the filename humanized
"""

from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot


class ScenarioModel(QObject):
    """QObject exposing the discovered scenario list to QML."""

    loaded = Signal()

    def __init__(self, repo_root: Path, parent=None) -> None:
        super().__init__(parent)
        self._scenario_dir = repo_root / "core" / "src" / "scenario"
        self._items: list[dict] = []
        self.discover()

    # -- discovery ---------------------------------------------------------
    def discover(self) -> None:
        items: list[dict] = []
        if not self._scenario_dir.is_dir():
            self._items = items
            self.loaded.emit()
            return

        seen = {
            p.name
            for p in sorted(self._scenario_dir.iterdir())
            if p.is_dir() and (p / "scenario.json").exists()
        }
        for name in sorted(seen):
            items.append(self._entry(name))

        for f in sorted(self._scenario_dir.glob("*.json")):
            if f.stem not in seen:
                items.append(self._entry(f.stem))

        self._items = items
        self.loaded.emit()

    def _entry(self, name: str) -> dict:
        label = name.replace("_", " ").title()
        analysis = self._scenario_dir / name / "analysis.md"
        if analysis.is_file():
            for line in analysis.read_text(errors="ignore").splitlines():
                line = line.strip()
                if line.startswith("# ") and not line.startswith("##"):
                    label = line[2:].strip()
                    break
        return {"name": name, "label": label}

    # -- QML API -----------------------------------------------------------
    @Property(bool)
    def is_loaded(self) -> bool:
        return len(self._items) > 0

    @Slot(result=list)
    def names(self) -> list:
        """Return the list of {name, label} dicts (QVariant conversions)."""
        return self._items

    @Slot()
    def refresh(self) -> None:
        self.discover()