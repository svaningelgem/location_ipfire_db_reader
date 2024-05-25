from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path

from location_ipfire_db_reader import IpInformation, LocationDatabase
from location_ipfire_db_reader.database_reader import _read_network_from_file, is_ipv4
from location_ipfire_db_reader.interpret_location_db import loc_database_network_node_v1, loc_database_network_v1, size


loc_db = LocationDatabase(Path(__file__).parent.parent / 'tests/resources/location.db', raise_exceptions=False)


data = "network,country_code,asn,asname,is_anonymous_proxy,is_satellite_provider,is_anycast,is_drop\n"


def dump(current_node: loc_database_network_node_v1, current_string: str) -> None:
    full_string = f'{current_string:<0128}'
    if is_ipv4(full_string):
        ip = ipaddress.IPv4Address(int(full_string[96:], 2))
        mask = len(current_string) - 96
    else:
        ip = ipaddress.IPv6Address(int(full_string, 2))
        mask = len(current_string)

    network_offset = loc_db.header.network_data_offset + current_node.network * size(loc_database_network_v1)
    loc_db.fp.seek(network_offset, os.SEEK_SET)
    nw = loc_database_network_v1.read(loc_db.fp)

    info = IpInformation(loc_db, str(ip), nw, mask)

    global data
    cc = "" if info.country_code == '\x00\x00' else info.country_code

    data += f'{ip}/{mask},{cc},{info.asn},"{info.asn_name}",{int(info.is_anonymous_proxy)},{int(info.is_satellite_provider)},{int(info.is_anycast)},{int(info.is_drop)}\n'


def recursive(current_node: loc_database_network_node_v1, current_string: str) -> None:
    if current_node.is_leaf:
        dump(current_node, current_string)
        return  # Nothing under this one anymore

    if current_node.one != 0:
        recursive(
            _read_network_from_file(loc_db.fp, loc_db.header.network_tree_offset + size(loc_database_network_node_v1) * current_node.one),
            current_string + "1"
        )

    if current_node.zero != 0:
        recursive(
            _read_network_from_file(loc_db.fp, loc_db.header.network_tree_offset + size(loc_database_network_node_v1) * current_node.zero),
            current_string + "0"
        )


recursive(
    _read_network_from_file(loc_db.fp, loc_db.header.network_tree_offset),
    ""
)

Path("output.csv").write_text(data)
