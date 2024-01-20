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


def test_getitem(locdb: LocationDatabase) -> None:
    sut = locdb["5.39.209.157"]

    assert sut.asn == 198871
    assert sut.asn_name == "Diputacion Provincial de Castellon"
    assert sut.country_code == "ES"
    assert sut.country_name == "Spain"
    assert sut.country_continent == "EU"

    assert sut.ip == "5.39.209.157"
    assert sut.subnet_mask == 24
    assert sut.network_address == "5.39.209.0"
    assert sut.ip_with_cidr == "5.39.209.0/24"

    assert not sut.is_anonymous_proxy
    assert not sut.is_satellite_provider
    assert not sut.is_anycast
    assert not sut.is_drop


def test_getitem_failure(locdb: LocationDatabase) -> None:
    with pytest.raises(ValueError, match="Cannot find anything anymore!"):
        locdb["255.255.255.255"]


def test_ip_information_failure(locdb: LocationDatabase) -> None:
    sut = locdb["5.39.209.157"]
    # Ok, we've got to fake it...
    fake_asn = 0xffffff
    sut._network_info.asn = fake_asn
    with pytest.raises(ValueError, match=f"Can't find asn object with id {fake_asn}!"):
        sut.asn_name
