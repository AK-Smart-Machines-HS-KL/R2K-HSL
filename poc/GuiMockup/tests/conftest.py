"""Shared fixtures for GuiMockup tests."""

import sys
from pathlib import Path

import pytest

# Add parent dir to path so we can import the GuiMockup package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def repo_root(tmp_path):
    """Create a minimal repo structure for testing."""
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "launch_r2k.sh").write_text("#!/bin/bash\necho ok\n")
    return tmp_path


@pytest.fixture
def scenario_dir(repo_root):
    """Create a scenario directory with test data."""
    d = repo_root / "core" / "src" / "scenario"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def fragments_dir(repo_root):
    """Create a strategy fragments directory with test data."""
    d = repo_root / "core" / "src" / "strategy" / "fragments"
    d.mkdir(parents=True)
    return d
