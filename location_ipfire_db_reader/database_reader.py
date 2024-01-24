from __future__ import annotations

import os
import socket
import typing
from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path
from typing import BinaryIO, TypeVar

from .download_db import download_or_update_location_database
from .exceptions import IPAddressError
from .interpret_location_db import (
    Block,
    as_int,
    loc_database_as_v1,
    loc_database_country_v1,
    loc_database_header_v1,
    loc_database_magic,
    loc_database_network_node_v1,
    loc_database_network_v1,
    size,
)

if typing.TYPE_CHECKING:
    from collections.abc import Iterator


__all__ = ["DatabaseReader", "is_ipv4"]

T = TypeVar("T", bound=Block)
_ipv4_start: str = "0" * 80 + "1" * 16
subnet_mask = int


def is_ipv4(ip: str) -> bool:
    return _convert_ip_to_bitstring(ip).startswith(_ipv4_start)


def _convert_ip_to_bitstring(ip: str | int) -> str:
    if isinstance(ip, int):
        ip = bin(ip)[2:]  # strip 0b
        if len(ip) <= 32:  # IPv4
            ip = _ipv4_start + f"{ip:>032}"
        return ip

    if all(c in ("0", "1") for c in ip):
        # Already a bitstring
        return ip

    ip = ip.split("/")[0]  # Remove CIDR
    is_ipv6 = ":" in ip

    binary_address = socket.inet_pton(socket.AF_INET6 if is_ipv6 else socket.AF_INET, ip)

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
    raise_exceptions: bool = True

    def __post_init__(self) -> None:
        self.filename = Path(self.filename).resolve().absolute()

    @cached_property
    def fp(self) -> BinaryIO:
        download_or_update_location_database(self.filename)
        return self.filename.open("rb")

    @cached_property
    def header(self) -> loc_database_header_v1:
        self.fp.seek(0, os.SEEK_SET)

        magic_header = loc_database_magic.read(self.fp)
        assert magic_header.magic == b"LOCDBXX"
        assert magic_header.version == 1

        return loc_database_header_v1.read(self.fp)

    def all_countries(self) -> Iterator[loc_database_country_v1]:
        yield from self._read_objects(
            loc_database_country_v1,
            self.header.countries_offset,
            self.header.countries_length,
        )

    def all_autonomous_systems(self) -> Iterator[loc_database_as_v1]:
        yield from self._read_objects(
            loc_database_as_v1,
            self.header.as_offset,
            self.header.as_length,
        )

    all_ass = all_autonomous_systems

    def all_network_data(self) -> Iterator[loc_database_network_v1]:
        yield from self._read_objects(
            loc_database_network_v1,
            self.header.network_data_offset,
            self.header.network_data_length,
        )

    def all_network_nodes(self) -> Iterator[loc_database_network_node_v1]:
        yield from self._read_objects(
            loc_database_network_node_v1,
            self.header.network_tree_offset,
            self.header.network_tree_length,
        )

    def _read_objects(self, type_: type[T], offset: int, length: int) -> Iterator[T]:
        count = as_int(length / size(type_))

        self.fp.seek(offset, os.SEEK_SET)

        for _ in range(count):
            yield type_.read(self.fp)

    def _find_network_information(self, ip: str) -> tuple[loc_database_network_v1, subnet_mask]:
        # Implementation from https://github.com/ipfire/libloc/blob/master/src/database.c#L848
        node_index = 0

        node_chain = []
        for bit in _convert_ip_to_bitstring(ip):
            offset = self.header.network_tree_offset + size(loc_database_network_node_v1) * node_index
            node = _read_network_from_file(self.fp, offset)
            node_chain.append(node)

            node_index = node.zero if bit == "0" else node.one

            if node_index > 0:
                continue

            # Find the previous leaf here
            while node_chain:
                previous_node = node_chain.pop()
                if not previous_node.is_leaf:
                    continue

                network_offset = self.header.network_data_offset + previous_node.network * size(loc_database_network_v1)
                self.fp.seek(network_offset, os.SEEK_SET)
                return loc_database_network_v1.read(self.fp), len(node_chain)

            raise IPAddressError(ip)
