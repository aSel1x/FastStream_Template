"""Resolving the client IP that rate limiting and lockout are keyed on.

`request.client.host` is the TCP peer. Behind any reverse proxy — the docker-compose layout
here, an nginx sidecar, a k8s ingress, an ALB — that peer is the proxy, so every request shares
one key and five bad passwords lock out every user at once.

`X-Forwarded-For` is attacker-controlled, so it is only honoured when the peer is itself a
trusted proxy. `TRUSTED_PROXIES` is a comma-separated list of CIDRs; empty (the default) means
"nothing is in front of us" and the header is ignored entirely.
"""

import os
from ipaddress import IPv4Network, IPv6Network, ip_address, ip_network
from typing import Final

from litestar.connection import ASGIConnection
from litestar.datastructures.state import State

UNKNOWN_CLIENT: Final = 'unknown'
TRUSTED_PROXIES_VAR: Final = 'TRUSTED_PROXIES'

type Network = IPv4Network | IPv6Network


def trusted_networks() -> tuple[Network, ...]:
    raw = os.getenv(TRUSTED_PROXIES_VAR, '')
    networks: list[Network] = []
    for entry in raw.split(','):
        candidate = entry.strip()
        if not candidate:
            continue
        try:
            networks.append(ip_network(candidate, strict=False))
        except ValueError:
            continue
    return tuple(networks)


def _is_trusted(peer: str) -> bool:
    try:
        address = ip_address(peer)
    except ValueError:
        return False
    return any(address in network for network in trusted_networks())


def _first_forwarded(header: str) -> str | None:
    for entry in header.split(','):
        candidate = entry.strip()
        if candidate:
            return candidate
    return None


def client_ip[HandlerT, UserT, AuthT, StateT: State](
    connection: ASGIConnection[HandlerT, UserT, AuthT, StateT],
) -> str | None:
    """The caller's IP, or None when it cannot be established."""
    client = connection.client
    if client is None:
        return None
    peer = client.host

    if _is_trusted(peer):
        forwarded = connection.headers.get('x-forwarded-for')
        if forwarded:
            return _first_forwarded(forwarded) or peer
    return peer


def client_ip_or_unknown[HandlerT, UserT, AuthT, StateT: State](
    connection: ASGIConnection[HandlerT, UserT, AuthT, StateT],
) -> str:
    return client_ip(connection) or UNKNOWN_CLIENT
