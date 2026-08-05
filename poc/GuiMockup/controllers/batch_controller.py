"""BatchController: passes batch launches to LauncherController.

Exposed to QML as `batch`. Launched from the BatchPopup.
"""

from PySide6.QtCore import QObject, Signal, Slot


class BatchController(QObject):
    """Delegates to LauncherController.launch_batch() for single-terminal execution."""
    batchFinished = Signal(int)

    def __init__(self, launcher, parent=None) -> None:
        super().__init__(parent)
        self._launcher = launcher

    @Slot(int)
    def launch_batch(self, count: int) -> None:
        self._launcher.launch_batch(count)
