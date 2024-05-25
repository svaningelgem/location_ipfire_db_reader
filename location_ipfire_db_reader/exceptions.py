from dataclasses import dataclass

__all__ = ["LocationIPFireDBReaderException", "UnknownASNName", "IPAddressError"]


class LocationIPFireDBReaderException(Exception): ...


@dataclass(frozen=True)
class UnknownASNName(LocationIPFireDBReaderException):
    asn: int

    def __str__(self) -> str:
        return f"Cannot find the name for the ASN with id {self.asn}"


@dataclass(frozen=True)
class IPAddressError(LocationIPFireDBReaderException):
    ip: str

    def __str__(self) -> str:
        return (
            f"No information could be found for '{self.ip}'. Likely this is a reserved IP?\n"
            "more information about reserved ips can be found here: https://en.wikipedia.org/wiki/Reserved_IP_addresses)\n"
        )
