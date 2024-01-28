from __future__ import annotations

import os
import struct
from dataclasses import dataclass, fields
from functools import cache
from typing import IO, TypeVar

T = TypeVar("T", bound="Block")

# https://docs.python.org/3/library/struct.html#format-characters
_sizes: dict[int, tuple[str]] = {
    1: tuple("cbB?"),
    2: tuple("hHe"),
    4: tuple("iIlLf"),
    8: tuple("qQd"),
}
_reverse_sizes = {k: size for size, keys in _sizes.items() for k in keys}

LOC_SIGNATURE_MAX_LENGTH = 2048

LOC_NETWORK_FLAG_ANONYMOUS_PROXY = 1 << 0  # A1
LOC_NETWORK_FLAG_SATELLITE_PROVIDER = 1 << 1  # A2
LOC_NETWORK_FLAG_ANYCAST = 1 << 2  # A3
LOC_NETWORK_FLAG_DROP = 1 << 3  # XD


@cache
def size(block: type[Block]) -> int:
    total = 0

    for fld in fields(block):
        if fld.default.endswith("s"):
            total += int(fld.default[:-1])
        else:
            total += _reverse_sizes[fld.default]

    return total


@cache
def fmt(block: type[Block]) -> str:
    """> = Big Endian"""
    return ">" + "".join(fld.default for fld in fields(block))


def as_int(nr: int | float | str) -> int:
    if not isinstance(nr, int):
        return int(float(nr))

    return nr


class Block:
    @classmethod
    def read(cls, fp: IO) -> Block:
        n_bytes = fp.read(size(cls))
        data = list(struct.unpack(fmt(cls), n_bytes))

        # Convert bytes into string
        for idx, (field, value) in enumerate(zip(cls.__dataclass_fields__.values(), data)):  # type: tuple[int, tuple["Field", object]]
            if field.type == "str":
                data[idx] = value.decode("utf8")

        return cls(*data)


# https:#github.com/ipfire/libloc/blob/master/src/libloc/format.h#L39
@dataclass
class loc_database_magic(Block):
    magic: bytes = "7s"
    version: int = "B"


# https:#github.com/ipfire/libloc/blob/master/src/libloc/format.h#L46
@dataclass
class loc_database_header_v1(Block):
    # UNIX timestamp when the database was created
    created_at: int = "Q"  # uint64_t

    # Vendor who created the database
    vendor: int = "I"  # uint32_t

    # Description of the database
    description: int = "I"  # uint32_t

    # License of the database
    license: int = "I"  # uint32_t

    # Tells us where the ASes start
    as_offset: int = "I"  # uint32_t
    as_length: int = "I"  # uint32_t

    # Tells us where the networks start
    network_data_offset: int = "I"  # uint32_t
    network_data_length: int = "I"  # uint32_t

    # Tells us where the network nodes start
    network_tree_offset: int = "I"  # uint32_t
    network_tree_length: int = "I"  # uint32_t

    # Tells us where the countries start
    countries_offset: int = "I"  # uint32_t
    countries_length: int = "I"  # uint32_t

    # Tells us where the pool starts
    pool_offset: int = "I"  # uint32_t
    pool_length: int = "I"  # uint32_t

    # Signatures
    signature1_length: int = "H"  # uint16_t
    signature2_length: int = "H"  # uint16_t
    signature1: bytes = f"{LOC_SIGNATURE_MAX_LENGTH}s"
    signature2: bytes = f"{LOC_SIGNATURE_MAX_LENGTH}s"

    # Add some padding for future extensions
    _padding: bytes = "32s"

    @classmethod
    def read(cls, fp: IO) -> loc_database_header_v1:
        # Go back
        obj: loc_database_header_v1 = super().read(fp)  # But here we went too far
        if obj.signature1_length != LOC_SIGNATURE_MAX_LENGTH or obj.signature2_length != LOC_SIGNATURE_MAX_LENGTH:
            fp.seek(-(LOC_SIGNATURE_MAX_LENGTH * 2 + 32), os.SEEK_CUR)
            n_bytes = fp.read(obj.signature1_length)
            obj.signature1 = struct.unpack(f"{obj.signature1_length}s", n_bytes)
            n_bytes = fp.read(obj.signature2_length)
            obj.signature2 = struct.unpack(f"{obj.signature2_length}s", n_bytes)
            obj._padding = struct.unpack(cls._padding, fp.read(int(cls._padding[:-1])))
        return obj


# https:# github.com/ipfire/libloc/blob/master/src/libloc/format.h#L89
@dataclass
class loc_database_network_node_v1(Block):
    zero: int = "I"  # uint32_t
    one: int = "I"  # uint32_t

    network: int = "I"  # uint32_t

    @property
    def is_leaf(self) -> bool:
        # https://github.com/ipfire/libloc/blob/master/src/database.c#L844
        return self.network != 0xFFFFFFFF


# https:# github.com/ipfire/libloc/blob/master/src/libloc/format.h#L96
@dataclass
class loc_database_network_v1(Block):
    #  The start address and prefix will be encoded in the tree

    #  The country this network is located in
    country_code: str = "2s"

    _reserve: bytes = "2s"

    #  ASN
    asn: int = "I"  # uint32_t

    #  Flags
    flags: int = "H"  # uint16_t

    #  Reserved
    _padding: bytes = "2s"

    @property
    def is_anonymous_proxy(self) -> bool:
        return bool(self.flags & LOC_NETWORK_FLAG_ANONYMOUS_PROXY)

    @property
    def is_satellite_provider(self) -> bool:
        return bool(self.flags & LOC_NETWORK_FLAG_SATELLITE_PROVIDER)

    @property
    def is_anycast(self) -> bool:
        return bool(self.flags & LOC_NETWORK_FLAG_ANYCAST)

    @property
    def is_drop(self) -> bool:
        return bool(self.flags & LOC_NETWORK_FLAG_DROP)


# https:# github.com/ipfire/libloc/blob/master/src/libloc/format.h#L112
@dataclass
class loc_database_as_v1(Block):
    #  The AS number
    number: int = "I"  # uint32_t

    #  Name
    name: int = "I"  # uint32_t


# https:# github.com/ipfire/libloc/blob/master/src/libloc/format.h#L120
@dataclass
class loc_database_country_v1(Block):
    code: str = "2s"
    continent_code: str = "2s"

    #  Name in the string pool
    name: int = "I"  # uint32_t
