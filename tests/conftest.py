import pytest
from pathlib import Path


@pytest.fixture
def data_dir(tmp_path):
    """Create a temporary data directory with subdirs."""
    (tmp_path / "proceeds").mkdir()
    (tmp_path / "results").mkdir()
    (tmp_path / "state").mkdir()
    return tmp_path
