"""Issue #4 reported by MaurUppi.
https://github.com/svaningelgem/location_ipfire_db_reader/issues/4
"""

import re

import pytest

from location_ipfire_db_reader import LocationDatabase
from location_ipfire_db_reader.exceptions import IPAddressError, UnknownASNName


def test_failure_cant_find_asn(locdb: LocationDatabase) -> None:
    """This is a test with an ASN that has a country name, but no ASN name."""
    # http://ip-api.com/csv/201.148.95.249
    # success,Mexico,MX,CMX,Mexico City,Mexico City,01010,19.3531,-99.2091,America/Mexico_City,
    #   "Operbes, S.A. de C.V.","Operbes, S.A. de C.V","AS18734 Operbes, S.A. de C.V.",201.148.95.249

    sut = locdb["201.148.95.249"]

    assert sut.asn == 18734
    assert sut.country_code == "MX"
    assert sut.country_name == "Mexico"
    assert sut.country_continent == "NA"

    assert sut.ip == "201.148.95.249"
    assert sut.subnet_mask == 19
    assert sut.network_address == "201.148.64.0"
    assert sut.ip_with_cidr == "201.148.64.0/19"

    assert not sut.is_anonymous_proxy
    assert not sut.is_satellite_provider
    assert not sut.is_anycast
    assert not sut.is_drop

    with pytest.raises(UnknownASNName, match="Cannot find the name for the ASN with id 18734"):
        _ = sut.asn_name


def test_failure_cant_find_asn2(locdb: LocationDatabase) -> None:
    """This is a test with an ASN that has a country name, but no ASN name."""
    # http://ip-api.com/csv/202.37.126.25
    # success,New Zealand,NZ,HKB,Hawke's Bay,Napier City,4143,-39.5109,176.876,Pacific/Auckland,
    #   RUAWHARO,,,202.37.126.25

    sut = locdb["202.37.126.25"]

    assert sut.asn == 0
    assert sut.country_code == "AU"
    assert sut.country_name == "Australia"
    assert sut.country_continent == "OC"

    assert sut.ip == "202.37.126.25"
    assert sut.subnet_mask == 7
    assert sut.network_address == "202.0.0.0"
    assert sut.ip_with_cidr == "202.0.0.0/7"

    assert not sut.is_anonymous_proxy
    assert not sut.is_satellite_provider
    assert not sut.is_anycast
    assert not sut.is_drop

    with pytest.raises(UnknownASNName, match="Cannot find the name for the ASN with id 0"):
        _ = sut.asn_name


# def test_failure_cant_find_asn3(locdb: LocationDatabase) -> None:
#     """This is a test with an ASN that has a country name, but no ASN name."""
#     # http://ip-api.com/csv/88.218.67.25
#     # success,United Kingdom,GB,ENG,England,London,W1B,51.5074,-0.127758,Europe/London,
#     #   TrafficTransitSolution LLC,TrafficTransitSolution LLC,,88.218.67.25
#
#     sut = locdb["88.218.67.25"]
#
#     assert sut.asn == 0
#     assert sut.country_code == "RU"
#     assert sut.country_name == "Russian Federation"
#     assert sut.country_continent == "EU"
#
#     assert sut.ip == "88.218.67.25"
#     assert sut.subnet_mask == 23
#     assert sut.network_address == "88.218.66.0"
#     assert sut.ip_with_cidr == "88.218.66.0/23"
#
#     assert not sut.is_anonymous_proxy
#     assert not sut.is_satellite_provider
#     assert not sut.is_anycast
#     assert not sut.is_drop
#
#     with pytest.raises(UnknownASNName, match="Cannot find the name for the ASN with id 0"):
#         _ = sut.asn_name


def test_lookup_for_reserved_ip(locdb: LocationDatabase) -> None:
    """This is a test with an ASN that has a country name, but no ASN name."""
    with pytest.raises(
        IPAddressError,
        match=re.escape("No information could be found for '100.127.255.25'. Likely this is a reserved IP?"),
    ):
        _ = locdb["100.127.255.25"]


def test_lookup_for_reserved_ip_no_exceptions(locdb_noexc: LocationDatabase) -> None:
    ip = "100.127.255.25"
    sut = locdb_noexc[ip]

    assert sut.asn == 0
    assert sut.asn_name == ""
    assert sut.country_code == ""
    assert sut.country_name == ""
    assert sut.country_continent == ""

    assert sut.ip == ip
    assert sut.subnet_mask == 32
    assert sut.network_address == ip
    assert sut.ip_with_cidr == ip + "/32"

    assert not sut.is_anonymous_proxy
    assert not sut.is_satellite_provider
    assert not sut.is_anycast
    assert not sut.is_drop
