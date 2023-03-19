import os
import socket
from dataclasses import dataclass
from typing import ClassVar, TypeVar

from .decompress_db import decompress_xz_file
from .download_db import download_latest_location_database
from .interpret_location_db import (
    Block,
    as_int,
    loc_database_country_v1,
    loc_database_header_v1,
    loc_database_magic,
    loc_database_network_node_v1,
    loc_database_network_v1,
    size,
)

__all__ = ["LocationDatabase"]
T = TypeVar("T", bound=Block)


def _convert_ip_to_bitstring(ip: str | int) -> str:
    # TODO: maybe better to change this into an integer & do integer comparisons?
    #  --> going to keep it as is now as it's easier to debug.
    if isinstance(ip, int):
        return bin(ip)[2:]  # strip 0b

    if all(c in ("0", "1") for c in ip):
        # Already a bitstring
        return ip

    ip = ip.split("/")[0]  # Remove CIDR
    is_ipv6 = ":" in ip

    if is_ipv6:  # ipv6?
        binary_address = socket.inet_pton(socket.AF_INET6, ip)
    else:  # ipv4
        binary_address = socket.inet_pton(socket.AF_INET, ip)

    final = "".join(f"{byte:08b}" for byte in binary_address)
    if not is_ipv6:
        final = LocationDatabase._ipv4_start + final

    return final


@dataclass
class LocationDatabase:
    filename: str | os.PathLike
    _ipv4_start: ClassVar[str] = "0" * 80 + "1" * 16

    def __post_init__(self):
        self._fp = open(self.filename, "rb")

        magic_header = loc_database_magic.read(self._fp)
        assert magic_header.magic == b"LOCDBXX"
        assert magic_header.version == 1

        self._header = loc_database_header_v1.read(self._fp)
        self._countries = self._read_objects(
            loc_database_country_v1,
            self._header.countries_offset,
            self._header.countries_length,
        )
        self._ipv4_offset = None

    @classmethod
    def download(cls, into: str | os.PathLike):
        if download_latest_location_database(into):
            decompress_xz_file(into)

    def _read_objects(self, type_: type[T], offset: int, length: int) -> list[T]:
        count = as_int(length / size(type_))

        self._fp.seek(offset, os.SEEK_SET)

        return [type_.read(self._fp) for _ in range(count)]

    def find_country(self, ip: str) -> str:
        # TODO: int not really correct I think, removing support for it for now
        offset = self._header.network_tree_offset

        bitstring = _convert_ip_to_bitstring(ip)

        is_ipv4 = bitstring.startswith(self._ipv4_start)
        if is_ipv4 and self._ipv4_offset is not None:
            offset = self._ipv4_offset
            bitstring = bitstring[len(self._ipv4_start) :]

        for idx, c in enumerate(bitstring):
            self._fp.seek(offset, os.SEEK_SET)
            node = loc_database_network_node_v1.read(self._fp)

            if node.network != 0xFFFFFFFF:  # Found one.
                network_offset = self._header.network_data_offset + node.network * size(loc_database_network_v1)
                self._fp.seek(network_offset, os.SEEK_SET)
                network_data = loc_database_network_v1.read(self._fp)
                return network_data.country_code.decode("utf8")

            if is_ipv4 and self._ipv4_offset is None and idx == len(self._ipv4_start):
                self._ipv4_offset = offset

            choose_node = node.zero if c == "0" else node.one
            offset = self._header.network_tree_offset + size(loc_database_network_node_v1) * choose_node


if __name__ == "__main__":
    db = LocationDatabase("location.db")
    assert db.find_country("213.219.175.246") == "BE"
    assert db.find_country("213.219.175.246") == "BE"
    print(db.find_country("8.8.8.8"))
