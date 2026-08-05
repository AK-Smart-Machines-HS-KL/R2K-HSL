"""Strategy repository: discovers mode fragments from
`core/src/strategy/fragments/rules_*.txt`.

See DESIGN.md §5 "Mode fragment filtering":
- include mode fragments (8): 3vs3, 2vs2, 1vs1, 3vs1, 2vs1, 1vs0, 0vs1, recover
- exclude static + game-phase: rules_core, rules_ball_out, rules_goal_kick,
  rules_corner_kick_in, rules_kickoff
- mode name = filename minus `rules_` prefix and `.txt` suffix
- strategy CLI arg = `strat_<mode>`
"""

from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

# Static + game-phase rules to EXCLUDE from the strategy choice strip.
_EXCLUDE = {
    "rules_core.txt",
    "rules_ball_out.txt",
    "rules_goal_kick.txt",
    "rules_corner_kick_in.txt",
    "rules_kickoff.txt",
}

# Explicit allow-list of modes we present; anything else in rules_*.txt is ignored.
_INCLUDE_MODES = {"3vs3", "2vs2", "1vs1", "3vs1", "2vs1", "1vs0", "0vs1", "recover"}


class StrategyModel(QObject):
    """QObject exposing the discovered strategy/mode list to QML."""

    loaded = Signal()

    def __init__(self, repo_root: Path, parent=None) -> None:
        super().__init__(parent)
        self._fragments_dir = repo_root / "core" / "src" / "strategy" / "fragments"
        self._items: list[dict] = []
        self.discover()

    # -- discovery ---------------------------------------------------------
    def discover(self) -> None:
        items: list[dict] = []
        if self._fragments_dir.is_dir():
            for f in sorted(self._fragments_dir.glob("rules_*.txt")):
                if f.name in _EXCLUDE:
                    continue
                mode = f.name[len("rules_"):-len(".txt")]
                if mode in _INCLUDE_MODES:
                    items.append({"name": mode, "label": mode.upper()})
        self._items = items
        self.loaded.emit()

    # -- QML API -----------------------------------------------------------
    @Property(bool)
    def is_loaded(self) -> bool:
        return len(self._items) > 0

    @Slot(result=list)
    def names(self) -> list:
        """Return the list of {name, label} dicts."""
        return self._items

    @Slot()
    def refresh(self) -> None:
        self.discover()