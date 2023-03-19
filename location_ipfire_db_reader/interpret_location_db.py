import os
import struct
from dataclasses import dataclass, fields
from functools import lru_cache
from io import BufferedReader
from typing import Callable, IO, TypeVar


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


@lru_cache(maxsize=None)
def size(block: type["Block"]) -> int:
    total = 0

    for fld in fields(block):
        if fld.default.endswith("s"):
            total += int(fld.default[:-1])
        else:
            total += _reverse_sizes[fld.default]

    return total


@lru_cache(maxsize=None)
def fmt(block: type["Block"]) -> str:
    """
    > = Big Endian
    """
    return ">" + "".join(fld.default for fld in fields(block))


def as_int(nr: int | float) -> int:
    if not isinstance(nr, int):
        nr2 = int(nr)
        assert nr2 == nr, f"{nr} is not an integer."
        return nr2

    return nr


class Block:
    @classmethod
    def read(cls, fp: IO):
        n_bytes = fp.read(size(cls))
        data = struct.unpack(fmt(cls), n_bytes)
        return cls(*data)


# https:#github.com/ipfire/libloc/blob/master/src/libloc/format.h#L39
@dataclass
class loc_database_magic(Block):
    magic: str = "7s"
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
    signature1: str = f"{LOC_SIGNATURE_MAX_LENGTH}s"
    signature2: str = f"{LOC_SIGNATURE_MAX_LENGTH}s"

    # Add some padding for future extensions
    padding: str = "32s"

    @classmethod
    def read(cls, fp: IO):
        # Go back
        obj: loc_database_header_v1 = super().read(fp)  # But here we went too far
        if obj.signature1_length != LOC_SIGNATURE_MAX_LENGTH or obj.signature2_length != LOC_SIGNATURE_MAX_LENGTH:
            fp.seek(-(LOC_SIGNATURE_MAX_LENGTH * 2 + 32), os.SEEK_CUR)
            n_bytes = fp.read(obj.signature1_length)
            obj.signature1 = struct.unpack(f"{obj.signature1_length}s", n_bytes)
            n_bytes = fp.read(obj.signature2_length)
            obj.signature2 = struct.unpack(f"{obj.signature2_length}s", n_bytes)
            obj.padding = struct.unpack(cls.padding, fp.read(int(cls.padding[:-1])))
        return obj


# https:# github.com/ipfire/libloc/blob/master/src/libloc/format.h#L89
@dataclass
class loc_database_network_node_v1(Block):
    zero: int = "I"  # uint32_t
    one: int = "I"  # uint32_t

    network: int = "I"  # uint32_t


# https:# github.com/ipfire/libloc/blob/master/src/libloc/format.h#L96
@dataclass
class loc_database_network_v1(Block):
    #  The start address and prefix will be encoded in the tree

    #  The country this network is located in
    country_code: str = "2s"

    _reserve: str = "2s"

    #  ASN
    asn: int = "I"  # uint32_t

    #  Flags
    flags: int = "H"  # uint16_t

    #  Reserved
    padding: str = "2s"

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


def read_objects(fp: IO, type_: type[T], offset: int, length: int, post_processing: Callable = None) -> list[T]:
    # Offset = from start of file (os.SEEK_SET)
    count = as_int(length / size(type_))

    fp.seek(offset, os.SEEK_SET)

    result = []
    for _ in range(count):
        obj = type_.read(fp)

        if post_processing:
            post_processing(obj)

        result.append(obj)

    return result


def read_stringpool(fp: IO, offset: int, length: int) -> dict[int, bytes]:
    fp.seek(offset, os.SEEK_SET)

    output = {}
    position = 0
    for string in fp.read(length).split(b"\x00"):
        output[position] = string
        position += 1 + len(string)
    return output


def build_network_tree():
    def __loc_database_node_is_leaf(node: loc_database_network_node_v1) -> bool:
        return node.network != 0xFFFFFFFF


def bit2ip(bitstring):
    if bitstring.startswith("0" * 80 + "1" * 16):  # ipv4
        bitstring = bitstring[96:]

        part1 = bitstring[:8].ljust(8, "0")
        part2 = bitstring[8:16].ljust(8, "0")
        part3 = bitstring[16:24].ljust(8, "0")
        part4 = bitstring[24:].ljust(8, "0")

        return f"{int(part1, 2)}.{int(part2, 2)}.{int(part3, 2)}.{int(part4, 2)}/{len(bitstring)}"
    else:
        bitstring = bitstring.zfill(128)

        # Split the bitstring into 8 groups of 16 bits each
        groups = [bitstring[i : i + 16] for i in range(0, 128, 16)]

        # Convert each group to its hexadecimal equivalent
        hex_groups = [hex(int(group, 2))[2:].zfill(4) for group in groups]

        # Join the hexadecimal groups with colons to form the IPv6 address
        ipv6_address = ":".join(hex_groups)

        # Determine the CIDR notation from the length of the bitstring
        cidr = "/" + str(len(bitstring) - bitstring.find("1") - 1)

        # Add the CIDR notation to the IPv6 address and return it
        return ipv6_address + cidr


def dump_network(country, asn):
    networks = [(idx, no) for idx, no in enumerate(network_objects) if no.asn == asn and no.country_code == country]
    network_numbers = [i for i, n in networks]
    # print('networks:', networks)

    nodes = [(idx, nno) for idx, nno in enumerate(network_node_objects) if nno.network in network_numbers]
    # print('nodes:', nodes)

    for first_idx, node in nodes:
        # Doing a reverse lookup now.

        search_node = first_idx
        # print('- node:', search_node)

        found = ""
        while search_node != 0:
            idx, node = next(
                (idx, nno) for idx, nno in enumerate(network_node_objects) if search_node in (nno.zero, nno.one)
            )
            found = ("1" if search_node == node.one else "0") + found
            # print('> ', 1 if search_node == node.one else 0, f' ({idx}) > ', node)
            search_node = idx

        print(f" >> {len(found)} >> ", bit2ip(found))


if __name__ == "__main__":

    def _assign_name(obj: loc_database_country_v1 | loc_database_as_v1) -> None:
        obj.name = strings[obj.name].decode("utf8")

    location_db = r"location.db"
    with open(location_db, "rb") as fp:
        fp = BufferedReader(fp)

        magic_header = loc_database_magic.read(fp)
        assert magic_header.magic == b"LOCDBXX"
        assert magic_header.version == 1

        header = loc_database_header_v1.read(fp)

        strings = read_stringpool(fp, header.pool_offset, header.pool_length)

        as_objects = read_objects(
            fp,
            loc_database_as_v1,
            header.as_offset,
            header.as_length,
            post_processing=_assign_name,
        )
        network_node_objects = read_objects(
            fp,
            loc_database_network_node_v1,
            header.network_tree_offset,
            header.network_tree_length,
        )
        network_objects = read_objects(
            fp,
            loc_database_network_v1,
            header.network_data_offset,
            header.network_data_length,
        )

        country_objects = read_objects(
            fp,
            loc_database_country_v1,
            header.countries_offset,
            header.countries_length,
            post_processing=_assign_name,
        )

        # dump_network(b'BE', 9031)
        a = 1
