from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path
from typing import BinaryIO, TypeVar

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

__all__ = ["DatabaseReader", "is_ipv4"]

T = TypeVar("T", bound=Block)
_ipv4_start: str = "0" * 80 + "1" * 16
subnet_mask = int


def is_ipv4(ip: str) -> bool:
    return _convert_ip_to_bitstring(ip).startswith(_ipv4_start)


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
        final = _ipv4_start + final

    return final


@lru_cache(maxsize=5_000)
def _read_network_from_file(fp: BinaryIO, offset: int) -> loc_database_network_node_v1:
    fp.seek(offset, os.SEEK_SET)
    return loc_database_network_node_v1.read(fp)


@dataclass
class DatabaseReader:
    filename: str | Path

    def __post_init__(self):
        if isinstance(self.filename, str):
            self.filename = Path(self.filename)

        self.filename = self.filename.resolve().absolute()

        # self._read_countries()

    @cached_property
    def fp(self) -> BinaryIO:
        download_or_update_location_database(self.filename)
        return open(self.filename, "rb")

    @cached_property
    def header(self) -> loc_database_header_v1:
        self.fp.seek(0, os.SEEK_SET)

        magic_header = loc_database_magic.read(self.fp)
        assert magic_header.magic == b"LOCDBXX"
        assert magic_header.version == 1

        return loc_database_header_v1.read(self.fp)

    # def _read_countries(self):
    #     self._countries = self._read_objects(
    #         loc_database_country_v1,
    #         self._header.countries_offset,
    #         self._header.countries_length,
    #     )

    def _read_objects(self, type_: type[T], offset: int, length: int) -> list[T]:
        count = as_int(length / size(type_))

        self.fp.seek(offset, os.SEEK_SET)

        return [type_.read(self.fp) for _ in range(count)]

    def _find_network_information(self, ip: str) -> tuple[loc_database_network_v1, subnet_mask]:
        # Implementation from https://github.com/ipfire/libloc/blob/master/src/database.c#L848
        node_index = 0

        bitstring = _convert_ip_to_bitstring(ip)
        node_chain = []
        for idx, bit in enumerate(bitstring):
            offset = self.header.network_tree_offset + size(loc_database_network_node_v1) * node_index
            node = _read_network_from_file(self.fp, offset)
            node_chain.append(node)

            node_index = node.zero if bit == "0" else node.one

            if node_index > 0:
                # if node_index < self._header.network_node_objects.count:  # TODO!!
                #     raise IndexError
                continue

            # Find the previous leaf here
            while node_chain:
                previous_node = node_chain.pop()
                if not previous_node.is_leaf:
                    continue

                network_offset = self.header.network_data_offset + previous_node.network * size(loc_database_network_v1)
                self.fp.seek(network_offset, os.SEEK_SET)
                return loc_database_network_v1.read(self.fp), len(node_chain)

            raise ValueError("Cannot find anything anymore!")
