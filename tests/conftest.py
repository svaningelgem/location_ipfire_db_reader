from pathlib import Path

import pytest

from location_ipfire_db_reader import LocationDatabase


@pytest.fixture(scope="session")
def locdb_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    test_location = Path(__file__).parent / "resources/location.db"
    test_location.parent.mkdir(parents=True, exist_ok=True)
    return test_location


@pytest.fixture(scope="session")
def locdb(locdb_path: Path) -> LocationDatabase:
    return LocationDatabase(locdb_path)


@pytest.fixture(scope="session")
def locdb_noexc(locdb_path: Path) -> LocationDatabase:
    return LocationDatabase(locdb_path, raise_exceptions=False)
