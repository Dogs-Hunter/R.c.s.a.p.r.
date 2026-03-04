from dataclasses import dataclass
from functools import lru_cache
import ipaddress
import socket
from typing import Iterable


@dataclass(frozen=True)
class LocalIpInfo:
    primary: str | None
    all: list[str]
    autodetected_primary: str | None
    autodetected_all: list[str]
    override_used: bool


def parse_override(value: str | None) -> list[str]:
    if not value:
        return []
    parts = [part.strip() for part in value.split(",")]
    return [part for part in parts if part]


def is_displayable_ipv4(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    if ip.version != 4:
        return False
    if ip.is_loopback or ip.is_unspecified:
        return False
    return ip.is_private or ip.is_link_local


def filter_displayable_ipv4(addresses: Iterable[str]) -> list[str]:
    unique: list[str] = []
    for address in addresses:
        if is_displayable_ipv4(address) and address not in unique:
            unique.append(address)
    return unique


def _route_primary_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            candidate = sock.getsockname()[0]
    except OSError:
        return None
    return candidate if is_displayable_ipv4(candidate) else None


def _hostname_ipv4s() -> list[str]:
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, family=socket.AF_INET)
    except socket.gaierror:
        return []
    return filter_displayable_ipv4([info[4][0] for info in infos])


@lru_cache(maxsize=1)
def _autodetect() -> tuple[str | None, list[str]]:
    primary = _route_primary_ip()
    all_ips = _hostname_ipv4s()
    if primary and primary not in all_ips:
        all_ips = [primary] + [ip for ip in all_ips if ip != primary]
    if not primary and all_ips:
        primary = all_ips[0]
    return primary, all_ips


def get_local_ip_info(override: str | None = None) -> LocalIpInfo:
    autodetected_primary, autodetected_all = _autodetect()
    override_list = parse_override(override)
    if override_list:
        return LocalIpInfo(
            primary=override_list[0],
            all=override_list,
            autodetected_primary=autodetected_primary,
            autodetected_all=autodetected_all,
            override_used=True,
        )
    return LocalIpInfo(
        primary=autodetected_primary,
        all=autodetected_all,
        autodetected_primary=autodetected_primary,
        autodetected_all=autodetected_all,
        override_used=False,
    )
