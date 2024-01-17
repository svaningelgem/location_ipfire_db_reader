from pathlib import Path

import pytest
from pytest import TempPathFactory

from location_ipfire_db_reader import LocationDatabase


@pytest.fixture(scope="session")
def locdb(tmp_path_factory: TempPathFactory) -> LocationDatabase:
    test_location = Path(__file__).parent / "resources/location.db"
    test_location.parent.mkdir(parents=True, exist_ok=True)
    return LocationDatabase(test_location)
