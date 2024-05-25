from __future__ import annotations

from .database_reader import DatabaseReader
from .exceptions import IPAddressError
from .interpret_location_db import loc_database_network_v1
from .ip_information import IpInformation

__all__ = ["LocationDatabase"]


class LocationDatabase(DatabaseReader):
    def __getitem__(self, ip: str) -> IpInformation:
        """Retrieve information about 1 IP address."""
        try:
            network_info, subnet_mask = self._find_network_information(ip)
        except IPAddressError:
            if self.raise_exceptions:
                raise
            network_info = loc_database_network_v1(country_code="", _reserve=b"", asn=0, flags=0, _padding=b"")
            subnet_mask = 128

        return IpInformation(self, ip, network_info, subnet_mask)

    def find_country(self, ip: str) -> str:
        """Convience method to quickly find the country code."""
        return self[ip].country_code
