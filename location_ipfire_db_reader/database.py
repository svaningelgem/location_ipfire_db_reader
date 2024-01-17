from __future__ import annotations

import os
import socket
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO, ClassVar, TypeVar

from .download_db import download_or_update_location_database
from .interpret_location_db import (
    Block,
    as_int,
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


@lru_cache(maxsize=5_000)
def _read_network_from_file(fp: BinaryIO, offset: int) -> loc_database_network_node_v1:
    fp.seek(offset, os.SEEK_SET)
    return loc_database_network_node_v1.read(fp)


@dataclass
class LocationDatabase:
    filename: str | Path
    _ipv4_start: ClassVar[str] = "0" * 80 + "1" * 16
    _ipv4_offset: int | None = field(init=False, default=None)
    _fp: BinaryIO | None = field(init=False, default=None)

    def __post_init__(self):
        if isinstance(self.filename, str):
            self.filename = Path(self.filename)

        self.filename = self.filename.resolve().absolute()

        download_or_update_location_database(self.filename)

        self._open_file()
        self._read_database_header()
        # self._read_countries()

    def _open_file(self):
        self._fp = open(self.filename, "rb")

    def _read_database_header(self):
        magic_header = loc_database_magic.read(self._fp)
        assert magic_header.magic == b"LOCDBXX"
        assert magic_header.version == 1
        self._header = loc_database_header_v1.read(self._fp)

    # def _read_countries(self):
    #     self._countries = self._read_objects(
    #         loc_database_country_v1,
    #         self._header.countries_offset,
    #         self._header.countries_length,
    #     )

    def _read_objects(self, type_: type[T], offset: int, length: int) -> list[T]:
        count = as_int(length / size(type_))

        self._fp.seek(offset, os.SEEK_SET)

        return [type_.read(self._fp) for _ in range(count)]

    def find_country(self, ip: str) -> str:
        # Implementation from https://github.com/ipfire/libloc/blob/master/src/database.c#L848
        node_index = 0

        bitstring = _convert_ip_to_bitstring(ip)
        node_chain = []
        for idx, bit in enumerate(bitstring):
            offset = self._header.network_tree_offset + size(loc_database_network_node_v1) * node_index
            node = _read_network_from_file(self._fp, offset)
            node_chain.append(node)

            node_index = node.zero if bit == "0" else node.one

            if node_index > 0:
                # if node_index < self._header.network_node_objects.count:  # TODO!!
                #     raise IndexError
                continue

            # Find the previous leaf here
            for previous_node in reversed(node_chain):
                if not previous_node.is_leaf:
                    continue

                network_offset = self._header.network_data_offset + previous_node.network * size(
                    loc_database_network_v1
                )
                self._fp.seek(network_offset, os.SEEK_SET)
                return loc_database_network_v1.read(self._fp).country_code.decode("utf8")

            raise ValueError("Cannot find anything anymore!")
