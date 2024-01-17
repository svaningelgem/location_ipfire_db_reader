"""
Issue #1 reported by MaurUppi:
https://github.com/svaningelgem/location_ipfire_db_reader/issues/1

> the lookup result is not good.
"""
import pytest

from location_ipfire_db_reader import LocationDatabase


@pytest.mark.parametrize(
    ("ip", "expected_country"),
    [
        ("8.8.8.8", "US"),
        ("1.1.1.1", "AU"),
        ("1.32.233.111", "US"),
        ("1.32.252.111", "AP"),  # Asia/Pacific?
        ("113.74.8.78", "CN"),
        ("212.107.28.52", "AP"),  # Asia/Pacific?
    ],
)
def test_basic_retrieval(locdb: LocationDatabase, ip: str, expected_country: str) -> None:
    assert locdb.find_country(ip) == expected_country
