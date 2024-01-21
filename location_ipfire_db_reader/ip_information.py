from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from functools import cached_property
from typing import BinaryIO, Callable, TypeVar

from .database_reader import DatabaseReader, is_ipv4
from .interpret_location_db import (
    Block,
    as_int,
    loc_database_as_v1,
    loc_database_country_v1,
    loc_database_network_v1,
    size,
)

T = TypeVar("T", bound=Block)


@dataclass
class IpInformation:
    _db: DatabaseReader
    ip: str
    _network_info: loc_database_network_v1
    _subnet_mask: int

    @cached_property
    def country_code(self) -> str:
        return self._network_info.country_code

    @cached_property
    def asn(self) -> int:
        return self._network_info.asn

    @cached_property
    def is_anonymous_proxy(self) -> bool:
        return self._network_info.is_anonymous_proxy

    @cached_property
    def is_satellite_provider(self) -> bool:
        return self._network_info.is_satellite_provider

    @cached_property
    def is_anycast(self) -> bool:
        return self._network_info.is_anycast

    @cached_property
    def is_drop(self) -> bool:
        return self._network_info.is_drop

    @cached_property
    def _fp(self) -> BinaryIO:
        return self._db.fp

    def _read_string(self, position: int) -> str:
        self._fp.seek(position, os.SEEK_SET)
        data: bytes = b""
        while (null_pos := data.find(b"\x00")) == -1:
            data += self._fp.read(500)
        return data[:null_pos].decode("utf8")

    def _find_object(self, start_offset: int, max_size: int, obj_to_read: type[T], predicate: Callable[[T], int]) -> T:
        # Implementation from https://github.com/ipfire/libloc/blob/master/src/database.c#L760
        object_size = size(obj_to_read)
        lo = 0
        hi = as_int(max_size / object_size) - 1

        while lo <= hi:
            mid = (lo + hi) // 2
            self._fp.seek(start_offset + mid * object_size)
            obj = obj_to_read.read(self._fp)

            pred = predicate(obj)
            if pred == 0:
                return obj

            if pred < 0:
                lo = mid + 1
            else:
                hi = mid - 1

        raise ValueError(f"Can't find asn object with id {self.asn}!")

    @cached_property
    def asn_name(self) -> str:
        def cmp(obj: loc_database_as_v1) -> int:
            if obj.number == self.asn:
                return 0
            if obj.number < self.asn:
                return -1
            return 1

        obj = self._find_object(
            start_offset=self._db.header.as_offset,
            max_size=self._db.header.as_length,
            obj_to_read=loc_database_as_v1,
            predicate=cmp,
        )

        return self._read_string(self._db.header.pool_offset + obj.name)

    @cached_property
    def _country_info(self) -> loc_database_country_v1:
        def cmp(obj: loc_database_country_v1) -> int:
            if obj.code == self.country_code:
                return 0
            if obj.code < self.country_code:
                return -1
            return 1

        return self._find_object(
            start_offset=self._db.header.countries_offset,
            max_size=self._db.header.countries_length,
            obj_to_read=loc_database_country_v1,
            predicate=cmp,
        )

    @cached_property
    def country_name(self) -> str:
        return self._read_string(self._db.header.pool_offset + self._country_info.name)

    @cached_property
    def country_continent(self) -> str:
        return self._country_info.continent_code

    @cached_property
    def is_ipv4(self) -> bool:
        return is_ipv4(self.ip)

    @cached_property
    def network_address(self) -> str:
        class_to_use = ipaddress.IPv4Network if self.is_ipv4 else ipaddress.IPv6Network

        network = class_to_use(f"{self.ip}/{self.subnet_mask}", strict=False)
        return network.network_address.compressed

    @cached_property
    def subnet_mask(self) -> int:
        return self._subnet_mask - 96 if self.is_ipv4 else self._subnet_mask

    @cached_property
    def ip_with_cidr(self) -> str:
        return f"{self.network_address}/{self.subnet_mask}"
