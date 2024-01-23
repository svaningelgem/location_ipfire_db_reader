from pathlib import Path

import pytest
from pytest import TempPathFactory

from location_ipfire_db_reader import LocationDatabase


@pytest.fixture(scope="session")
def locdb_path(tmp_path_factory: TempPathFactory) -> Path:
    test_location = Path(__file__).parent / "resources/location.db"
    test_location.parent.mkdir(parents=True, exist_ok=True)
    return test_location


@pytest.fixture(scope="session")
def locdb(locdb_path: Path) -> LocationDatabase:
    yield LocationDatabase(locdb_path)


@pytest.fixture(scope="session")
def locdb_noexc(locdb_path: Path) -> LocationDatabase:
    yield LocationDatabase(locdb_path, raise_exceptions=False)
