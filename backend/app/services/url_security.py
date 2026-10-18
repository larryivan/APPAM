from __future__ import annotations

import ipaddress
import os
import socket
import threading
from contextlib import contextmanager
from urllib.parse import urljoin, urlparse

import requests


TRUE_VALUES = {'1', 'true', 'yes', 'on'}
REDIRECT_CODES = {301, 302, 303, 307, 308}


def _hostname_allowed(hostname: str) -> bool:
    allowlist = {
        item.strip().lower()
        for item in os.getenv('APPAM_REMOTE_DOWNLOAD_HOSTS', '').split(',')
        if item.strip()
    }
    if not allowlist:
        return True
    hostname = hostname.lower()
    return any(hostname == allowed or hostname.endswith(f'.{allowed}') for allowed in allowlist)


# --- DNS pinning -----------------------------------------------------------
#
# Validating a URL resolves its hostname once, but the HTTP/FTP client resolves
# it again when it opens the socket. A hostname under attacker control with a
# short TTL can answer with a public address for the check and a loopback or
# private address for the connection. Pinning the addresses that passed
# validation, for the duration of the connect, removes that window.
#
# The pin is thread-local and per-hostname, and `socket.getaddrinfo` behaves
# exactly as before for every thread and host that is not currently pinned.

_pin_state = threading.local()
_real_getaddrinfo = socket.getaddrinfo


class PinnedAddressError(ValueError):
    """A host resolved to an address that did not pass validation."""


def _guarded_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):  # noqa: A002
    results = _real_getaddrinfo(host, port, family, type, proto, flags)
    pin = getattr(_pin_state, 'pin', None)
    if not pin:
        return results
    pinned_host, allowed = pin
    if str(host).lower() != pinned_host:
        return results
    filtered = [item for item in results if item[4][0] in allowed]
    if not filtered:
        raise PinnedAddressError(
            f'Remote download host {host} resolved to an address that failed validation; '
            'refusing to connect.'
        )
    return filtered


if socket.getaddrinfo is not _guarded_getaddrinfo:  # pragma: no branch
    socket.getaddrinfo = _guarded_getaddrinfo


@contextmanager
def pinned_addresses(hostname: str, addresses):
    """Restrict name resolution for `hostname` to `addresses` in this thread."""
    previous = getattr(_pin_state, 'pin', None)
    _pin_state.pin = (str(hostname).lower(), frozenset(addresses))
    try:
        yield
    finally:
        _pin_state.pin = previous


def resolve_and_validate(url: str) -> tuple[str, str, frozenset[str]]:
    """Validate a remote URL and return it with the addresses it may use."""
    parsed = urlparse(str(url or '').strip())
    allowed_schemes = {'http', 'https'}
    if os.getenv('APPAM_ALLOW_FTP_DOWNLOADS', 'false').strip().lower() in TRUE_VALUES:
        allowed_schemes.add('ftp')
    if parsed.scheme.lower() not in allowed_schemes:
        raise ValueError(f'Remote downloads require one of: {", ".join(sorted(allowed_schemes))}')
    if not parsed.hostname:
        raise ValueError('Remote download URL is missing a hostname')
    if parsed.username or parsed.password:
        raise ValueError('Credentials in remote download URLs are not allowed')
    if not _hostname_allowed(parsed.hostname):
        raise ValueError(f'Remote download host is not allowlisted: {parsed.hostname}')

    try:
        addresses = {
            item[4][0]
            for item in _real_getaddrinfo(parsed.hostname, parsed.port, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as exc:
        raise ValueError(f'Could not resolve remote download host: {parsed.hostname}') from exc
    if not addresses:
        raise ValueError(f'Could not resolve remote download host: {parsed.hostname}')
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError(f'Remote download host resolves to a non-public address: {address}')
    return parsed.geturl(), parsed.hostname, frozenset(addresses)


def validate_remote_url(url: str) -> str:
    return resolve_and_validate(url)[0]


def safe_request(method: str, url: str, *, max_redirects: int = 5, **kwargs) -> requests.Response:
    current_url, hostname, addresses = resolve_and_validate(url)
    kwargs.pop('allow_redirects', None)
    for _ in range(max_redirects + 1):
        with pinned_addresses(hostname, addresses):
            response = requests.request(method, current_url, allow_redirects=False, **kwargs)
        if response.status_code not in REDIRECT_CODES:
            return response
        location = response.headers.get('Location')
        response.close()
        if not location:
            raise ValueError('Remote server returned a redirect without a Location header')
        current_url, hostname, addresses = resolve_and_validate(urljoin(current_url, location))
    raise ValueError(f'Remote download exceeded {max_redirects} redirects')


def max_remote_download_bytes() -> int:
    try:
        return max(1, int(os.getenv('APPAM_MAX_REMOTE_DOWNLOAD_BYTES', str(100 * 1024**3))))
    except ValueError:
        return 100 * 1024**3
