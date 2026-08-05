# Session Changelog — GUI Mockup

> Cross-session continuity log. Read first after reboot.

## 2026-08-05 — Bug fixes, tests, batch, cleanup

**Done:** Fixed 4 bugs (batch launch path, xterm injection, missing @Slot, stuck Run button). Added 57 pytest-qt tests. Single-terminal batch (N runs in one shell loop). Sentinel PID lifecycle (`/tmp/ros2k_session.pid`). Merged DESIGN.md into README.md. Renamed Play→Run. Updated root .gitignore.

**Not yet done:**
- Batch second-run issue (`launch_r2k.sh` cleanup trap interferes with parent loop)
- `R2K_RUN_ID` display in GUI
- Test consolidation (57 → ~28)

**Next:** Review test cases.
