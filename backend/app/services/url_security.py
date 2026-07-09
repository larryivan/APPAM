from __future__ import annotations

import ipaddress
import os
import socket
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


def validate_remote_url(url: str) -> str:
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
            for item in socket.getaddrinfo(parsed.hostname, parsed.port, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as exc:
        raise ValueError(f'Could not resolve remote download host: {parsed.hostname}') from exc
    if not addresses:
        raise ValueError(f'Could not resolve remote download host: {parsed.hostname}')
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError(f'Remote download host resolves to a non-public address: {address}')
    return parsed.geturl()


def safe_request(method: str, url: str, *, max_redirects: int = 5, **kwargs) -> requests.Response:
    current_url = validate_remote_url(url)
    kwargs.pop('allow_redirects', None)
    for _ in range(max_redirects + 1):
        response = requests.request(method, current_url, allow_redirects=False, **kwargs)
        if response.status_code not in REDIRECT_CODES:
            return response
        location = response.headers.get('Location')
        response.close()
        if not location:
            raise ValueError('Remote server returned a redirect without a Location header')
        current_url = validate_remote_url(urljoin(current_url, location))
    raise ValueError(f'Remote download exceeded {max_redirects} redirects')


def max_remote_download_bytes() -> int:
    try:
        return max(1, int(os.getenv('APPAM_MAX_REMOTE_DOWNLOAD_BYTES', str(100 * 1024**3))))
    except ValueError:
        return 100 * 1024**3
