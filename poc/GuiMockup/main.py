#!/usr/bin/env python3
"""ROS2K GUI Launcher — entry point.

Uses QQmlEngine + QQuickView (not QQmlApplicationEngine) because PySide6
6.11.1's QQmlApplicationEngine has two bugs:
  1. qmlRegisterSingletonInstance breaks QQuickItem.data property resolution
  2. setContextProperty makes properties invisible to QML

QQmlEngine + QQuickView with setContextProperty avoids both issues.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtGui import QGuiApplication, QColor
from PySide6.QtQml import QQmlEngine
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QUrl, QSize

from bridge import Bridge
from controllers.batch_controller import BatchController
from controllers.launcher_controller import LauncherController
from models.model_model import ModelModel
from models.scenario_model import ScenarioModel
from models.strategy_model import StrategyModel

APP_DIR = Path(__file__).resolve().parent          # poc/GuiMockup/
REPO_ROOT = APP_DIR.parents[1].resolve()           # R2K-HSL/
TITLE = "ROS2K Launcher"
WIDTH, HEIGHT = 520, 460


def main() -> int:
    os.environ.setdefault(
        "QT_QUICK_CONTROLS_CONF",
        str(APP_DIR / "Theme" / "qtquickcontrols2.conf"),
    )

    app = QGuiApplication(sys.argv)
    app.setApplicationName("ROS2K Launcher")

    # --- QML engine + Python objects ---
    engine = QQmlEngine()
    engine.addImportPath(str(APP_DIR))

    scenario_repo = ScenarioModel(REPO_ROOT)
    strategy_repo = StrategyModel(REPO_ROOT)
    model_repo = ModelModel()
    launcher = LauncherController(REPO_ROOT, scenario_repo, strategy_repo, model_repo)
    batch = BatchController(launcher)
    bridge = Bridge(launcher, batch, scenario_repo, strategy_repo, model_repo)

    # Expose Bridge via context property (avoids PySide6 6.11.1
    # qmlRegisterSingletonInstance bug that breaks QQuickItem.data).
    engine.rootContext().setContextProperty("Bridge", bridge)

    # --- QQuickView (renders QML Item tree inside a native window) ---
    view = QQuickView(engine, None)
    qml_path = APP_DIR / "window" / "MainWindow.qml"
    if not qml_path.exists():
        print(f"ERROR: {qml_path} not found", file=sys.stderr)
        return 1

    view.setSource(QUrl.fromLocalFile(str(qml_path)))
    view.setTitle(TITLE)
    view.setColor(QColor("#1e1e1e"))
    view.resize(WIDTH, HEIGHT)
    view.setMinimumSize(QSize(480, 400))
    view.show()

    if not view.rootObject():
        # QQuickView does not report errors via rootObjects — check contentItem
        print("ERROR: failed to load QML root", file=sys.stderr)
        return 1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
