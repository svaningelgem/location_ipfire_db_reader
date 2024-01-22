import pytest

from location_ipfire_db_reader import LocationDatabase
from location_ipfire_db_reader.exceptions import IPAddressError, UnknownASNName


def test_failure_cant_find_asn(locdb: LocationDatabase) -> None:
    """This is a test with an ASN that has a country name, but no ASN name."""

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
        sut.asn_name


def test_lookup_for_reserved_ip(locdb: LocationDatabase) -> None:
    """This is a test with an ASN that has a country name, but no ASN name."""
    with pytest.raises(IPAddressError, match="No information could be found for '100.127.255.25'. Likely this is a reserved IP?"):
        locdb["100.127.255.25"]
