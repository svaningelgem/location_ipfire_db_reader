from __future__ import annotations

from dataclasses import dataclass

from .database_reader import DatabaseReader
from .ip_information import IpInformation

__all__ = ["LocationDatabase"]


@dataclass
class LocationDatabase(DatabaseReader):
    def __getitem__(self, ip: str) -> IpInformation:
        return IpInformation(self, ip, *self._find_network_information(ip))

    def find_country(self, ip: str) -> str:
        return self._find_network_information(ip)[0].country_code
