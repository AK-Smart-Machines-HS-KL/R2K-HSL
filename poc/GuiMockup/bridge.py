"""Bridge: single QObject holding all Python objects, exposed to QML via context property."""

from PySide6.QtCore import QObject, Property


class Bridge(QObject):
    """Thin wrapper exposing backend + repos as named properties to QML.

    Registered as a QML context property via setContextProperty so every
    QML file can access ``Bridge.backend``, ``Bridge.scenarioRepo``, etc.
    """
    def __init__(self, backend, batch, scenario_repo, strategy_repo, model_repo, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._batch = batch
        self._scenario_repo = scenario_repo
        self._strategy_repo = strategy_repo
        self._model_repo = model_repo

    @Property(QObject, constant=True)
    def backend(self):
        return self._backend

    @Property(QObject, constant=True)
    def batch(self):
        return self._batch

    @Property(QObject, constant=True)
    def scenarioRepo(self):
        return self._scenario_repo

    @Property(QObject, constant=True)
    def strategyRepo(self):
        return self._strategy_repo

    @Property(QObject, constant=True)
    def modelRepo(self):
        return self._model_repo