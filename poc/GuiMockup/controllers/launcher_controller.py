"""LauncherController: central Qt state object exposed to QML as `backend`.

Holds every configuration property (each with a change signal), builds the
`launch_r2k.sh` argv, and spawns the subprocess via QProcess. Repos are
injected so the controller can pre-load the next step's data (lazy /
anticipated discovery).
"""

from pathlib import Path
import os
import shutil
import sys
import time

from PySide6.QtCore import QObject, Property, QProcess, Signal, Slot

_SENTINEL = Path("/tmp/ros2k_session.pid")


class LauncherController(QObject):
    # -- property change signals -------------------------------------------
    scenarioChanged = Signal()
    strategyChanged = Signal()
    modelChanged = Signal()
    relayChanged = Signal()
    explainChanged = Signal()
    headlessChanged = Signal()
    durationChanged = Signal()
    stepChanged = Signal()
    launchingChanged = Signal()
    launchFinished = Signal()

    STEP_LABELS = [
        "SCENARIO",
        "STRATEGY",
        "MODEL",
        "RELAY",
        "EXPLAIN",
        "HEADLESS",
        "DURATION",
    ]

    def __init__(self, repo_root: Path, scenario_repo=None, strategy_repo=None,
                 model_repo=None, parent=None) -> None:
        super().__init__(parent)
        self._root = repo_root
        self._scenario_repo = scenario_repo
        self._strategy_repo = strategy_repo
        self._model_repo = model_repo

        self._selected_scenario = None
        self._selected_strategy = None
        self._selected_model = None
        self._selected_relay = "only_sim_bots"
        self._explain = False
        self._headless = True
        self._duration = 60
        self._step = 0
        self._launching = False
        self._process = None
        self._terminal_pid: int | None = None

    # -- lazy / anticipated discovery --------------------------------------
    def _anticipate(self, step: int) -> None:
        """Pre-load data for a forthcoming step while the user is on `step`."""
        if step == 0 and self._strategy_repo is not None and not self._strategy_repo.is_loaded:
            self._strategy_repo.discover()
        if step >= 1 and self._model_repo is not None and not self._model_repo.is_loaded:
            self._model_repo.discover()
            if self._selected_model is None and self._model_repo.names():
                first = self._model_repo.names()[0]["name"]
                self._selected_model = first
                self.modelChanged.emit()

    # -- selection slots (set + auto-advance) -------------------------------
    @Slot(str)
    def select_scenario(self, name: str) -> None:
        if self._selected_scenario != name:
            self._selected_scenario = name
            self.scenarioChanged.emit()
        self.go_forward()

    @Slot(str)
    def select_strategy(self, name: str) -> None:
        if self._selected_strategy != name:
            self._selected_strategy = name
            self.strategyChanged.emit()
        self.go_forward()

    @Slot(str)
    def select_model(self, name: str) -> None:
        if self._selected_model != name:
            self._selected_model = name
            self.modelChanged.emit()
        self.go_forward()

    @Slot(str)
    def select_relay(self, name: str) -> None:
        if self._selected_relay != name:
            self._selected_relay = name
            self.relayChanged.emit()
        self.go_forward()

    @Slot(bool)
    def set_explain(self, on: bool) -> None:
        if on != self._explain:
            self._explain = on
            self.explainChanged.emit()
        self.go_forward()

    @Slot(bool)
    def set_headless(self, on: bool) -> None:
        if on != self._headless:
            self._headless = on
            self.headlessChanged.emit()
        self.go_forward()

    @Slot(int)
    def set_duration(self, secs: int) -> None:
        secs = max(0, int(secs))
        if secs != self._duration:
            self._duration = secs
            self.durationChanged.emit()

    # -- manual step navigation ----------------------------------------------
    @Slot()
    def go_forward(self) -> None:
        if self._step < len(self.STEP_LABELS) - 1:
            self._set_step(self._step + 1)

    @Slot()
    def go_back(self) -> None:
        if self._step > 0:
            self._set_step(self._step - 1)

    @Slot(int)
    def go_to_step(self, step: int) -> None:
        if 0 <= step < len(self.STEP_LABELS):
            self._set_step(step)

    def _set_step(self, step: int) -> None:
        self._step = step
        self._anticipate(step)
        self.stepChanged.emit()

    # -- reset ----------------------------------------------------------------
    @Slot()
    def reset(self) -> None:
        self._selected_scenario = None
        self._selected_strategy = None
        self._selected_model = None
        self._selected_relay = "only_sim_bots"
        self._explain = False
        self._headless = True
        self._duration = 60
        self.scenarioChanged.emit()
        self.strategyChanged.emit()
        self.modelChanged.emit()
        self.relayChanged.emit()
        self.explainChanged.emit()
        self.headlessChanged.emit()
        self.durationChanged.emit()
        self._set_step(0)

    # -- CLI assembly + terminal launch --------------------------------------- #

    def _build_cmd_str(self) -> str:
        """Build a single shell command string for terminal execution."""
        return f'cd "{self._root / "core"}" && {self._build_core_cmd()}'

    def _build_core_cmd(self) -> str:
        """Build the launch_r2k.sh invocation without the cd prefix."""
        args = ["bash", "launch_r2k.sh"]
        args += ["--scenario", self._selected_scenario or ""]
        args += ["--strategy", f"strat_{self._selected_strategy or ''}"]
        args += ["--model", self._selected_model or ""]
        args += ["--relay", self._selected_relay or ""]
        args += ["--explain" if self._explain else "--no-explain"]
        if self._headless:
            args += ["--headless"]
        if self._duration > 0:
            args += ["--duration", str(self._duration)]
        return " ".join(f'"{a}"' if " " in a else a for a in args)

    BATCH_COOLDOWN = 10  # seconds between batch runs

    def _build_batch_cmd_str(self, count: int) -> str:
        """Build a single shell command that runs launch_r2k.sh N times."""
        core = self._build_core_cmd()
        return (
            f'cd "{self._root / "core"}" && '
            f'for i in $(seq 1 {count}); do '
            f'{core}; '
            f'sleep {self.BATCH_COOLDOWN}; '
            f'done; tail -f /dev/null'
        )

    @staticmethod
    def _find_terminal() -> list | None:
        """Detect available terminal emulator."""
        for term, args_fn in [
            ("gnome-terminal", lambda cmd: ["gnome-terminal", "--", "bash", "-c",
                f'echo $$ > {_SENTINEL}; {cmd}; tail -f /dev/null']),
            ("xterm", lambda cmd: ["xterm", "-e", f'bash -c "echo $$ > {_SENTINEL}; {cmd}; tail -f /dev/null"']),
            ("konsole", lambda cmd: ["konsole", "-e", "bash", "-c",
                f'echo $$ > {_SENTINEL}; {cmd}; tail -f /dev/null']),
        ]:
            if shutil.which(term):
                return args_fn
        return None

    def _read_sentinel_pid(self) -> int | None:
        """Read the PID written by the terminal's bash process."""
        try:
            return int(_SENTINEL.read_text().strip())
        except (FileNotFoundError, ValueError):
            return None

    def _sentinel_alive(self) -> bool:
        """Check if the previous terminal session is still running."""
        try:
            pid = int(_SENTINEL.read_text().strip())
            os.kill(pid, 0)
            return True
        except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
            return False

    @Slot()
    def launch(self) -> None:
        if self._sentinel_alive():
            return
        if not (self._selected_scenario and self._selected_strategy
                and self._selected_model):
            print("ERROR: Cannot launch — scenario, strategy, and model must "
                  "all be selected.", file=sys.stderr)
            return

        cmd_str = self._build_cmd_str()
        term_fn = self._find_terminal()
        if term_fn is None:
            print("ERROR: No terminal emulator found "
                  "(tried gnome-terminal, xterm, konsole)", file=sys.stderr)
            return

        try:
            _SENTINEL.unlink(missing_ok=True)
        except OSError:
            pass

        self._launching = True
        self.launchingChanged.emit()

        proc_args = term_fn(cmd_str)
        proc = QProcess(self)
        proc.setProgram(proc_args[0])
        proc.setArguments(proc_args[1:])
        proc.start()
        self._process = proc

        time.sleep(0.1)
        self._terminal_pid = self._read_sentinel_pid()

    @Slot(int)
    def launch_batch(self, count: int) -> None:
        """Open one terminal and run launch_r2k.sh N times sequentially."""
        if self._sentinel_alive():
            return
        if not (self._selected_scenario and self._selected_strategy
                and self._selected_model):
            print("ERROR: Cannot launch — scenario, strategy, and model must "
                  "all be selected.", file=sys.stderr)
            return

        cmd_str = self._build_batch_cmd_str(count)
        term_fn = self._find_terminal()
        if term_fn is None:
            print("ERROR: No terminal emulator found "
                  "(tried gnome-terminal, xterm, konsole)", file=sys.stderr)
            return

        try:
            _SENTINEL.unlink(missing_ok=True)
        except OSError:
            pass

        proc_args = term_fn(cmd_str)
        proc = QProcess(self)
        proc.setProgram(proc_args[0])
        proc.setArguments(proc_args[1:])
        proc.start()
        self._process = proc

        time.sleep(0.1)
        self._terminal_pid = self._read_sentinel_pid()

    def _finish_launching(self) -> None:
        self._launching = False
        self.launchingChanged.emit()
        self._process = None
        self.launchFinished.emit()

    # -- QML property accessors ----------------------------------------------- #

    @Property(str, notify=scenarioChanged)
    def selected_scenario(self) -> str:
        return self._selected_scenario or ""

    @Property(str, notify=strategyChanged)
    def selected_strategy(self) -> str:
        return self._selected_strategy or ""

    @Property(str, notify=modelChanged)
    def selected_model(self) -> str:
        return self._selected_model or ""

    @Property(str, notify=relayChanged)
    def selected_relay(self) -> str:
        return self._selected_relay or ""

    @Property(bool, notify=explainChanged)
    def explain_enabled(self) -> bool:
        return self._explain

    @Property(bool, notify=headlessChanged)
    def headless_enabled(self) -> bool:
        return self._headless

    @Property(int, notify=durationChanged)
    def duration_seconds(self) -> int:
        return self._duration

    @Property(int, notify=stepChanged)
    def current_step(self) -> int:
        return self._step

    @Property(bool, notify=launchingChanged)
    def is_launching(self) -> bool:
        return self._launching

    @Property(int, constant=True)
    def step_count(self) -> int:
        return len(self.STEP_LABELS)