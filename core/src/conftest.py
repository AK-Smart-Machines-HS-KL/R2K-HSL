"""Pytest config: --skip-slow flag for fast CI tier."""
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--skip-slow", action="store_true", default=False,
        help="Skip slow tests (real Gazebo matches). Run only fast unit tests.",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--skip-slow"):
        skip_slow = pytest.mark.skip(reason="--skip-slow: skipping slow tests")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)