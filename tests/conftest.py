"""Shared pytest fixtures for test suite."""

import pytest


@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project directory with subdirs."""
    (tmp_path / "proceeds").mkdir()
    (tmp_path / "results").mkdir()
    (tmp_path / "state").mkdir()
    (tmp_path / "output").mkdir()
    return tmp_path
