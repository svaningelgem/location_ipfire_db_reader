from location_ipfire_db_reader import LocationDatabase
from location_ipfire_db_reader.database_reader import _convert_ip_to_bitstring


def test_bitstrings() -> None:
    assert _convert_ip_to_bitstring(134744072) == _convert_ip_to_bitstring("8.8.8.8")


def test_all_countries(locdb: LocationDatabase) -> None:
    _ = next(locdb.all_countries())  # Shouldn't fail


def test_all_autonomous_systems(locdb: LocationDatabase) -> None:
    _ = next(locdb.all_autonomous_systems())  # Shouldn't fail


def test_all_network_data(locdb: LocationDatabase) -> None:
    _ = next(locdb.all_network_data())  # Shouldn't fail


def test_all_network_nodes(locdb: LocationDatabase) -> None:
    _ = next(locdb.all_network_nodes())  # Shouldn't fail
