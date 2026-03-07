"""Issue #1 reported by MaurUppi.
https://github.com/svaningelgem/location_ipfire_db_reader/issues/1
"""

import pytest

from location_ipfire_db_reader import LocationDatabase


@pytest.mark.parametrize(
    ("ip", "expected_country"),
    [
        ("8.8.8.8", "US"),          # Google Public DNS — ultra-stable
        ("1.1.1.1", "AU"),          # Cloudflare DNS — ultra-stable
        ("113.74.8.78", "CN"),      # China Telecom /10 block — large, stable
        ("212.107.28.52", "AP"),    # Asia/Pacific region
    ],
)
def test_basic_retrieval(locdb: LocationDatabase, ip: str, expected_country: str) -> None:
    assert locdb.find_country(ip) == expected_country


@pytest.mark.parametrize(
    "ip",
    [
        "1.32.233.111",  # From issue #1; was US, reassigned to AP — country may shift again
        "1.32.252.111",  # From issue #1; small block that may be re-assigned
    ],
)
def test_country_lookup_returns_result(locdb: LocationDatabase, ip: str) -> None:
    """Verify issue #1 IPs return a valid country code rather than crashing."""
    result = locdb.find_country(ip)
    assert len(result) == 2 and result == result.upper()


def test_getitem(locdb: LocationDatabase) -> None:
    sut = locdb["5.39.209.157"]

    assert sut.asn == 198871
    assert sut.asn_name == "Diputacion Provincial de Castellon"
    assert sut.country_code == "ES"
    assert sut.country_name == "Spain"
    assert sut.country_continent == "EU"

    assert sut.ip == "5.39.209.157"
    assert sut.subnet_mask == 22
    assert sut.network_address == "5.39.208.0"
    assert sut.ip_with_cidr == "5.39.208.0/22"

    assert not sut.is_anonymous_proxy
    assert not sut.is_satellite_provider
    assert not sut.is_anycast
    assert not sut.is_drop
