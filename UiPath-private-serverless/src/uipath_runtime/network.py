from __future__ import annotations

import socket
import ssl
from urllib.parse import urlparse

from .exceptions import NetworkValidationError, TLSValidationError


class NetworkValidator:
    def resolve_host(self, hostname: str) -> list[str]:
        try:
            return sorted({item[4][0] for item in socket.getaddrinfo(hostname, None)})
        except socket.gaierror as exc:
            raise NetworkValidationError(f"DNS_RESOLUTION_FAILED: {hostname}") from exc

    def test_tcp_connection(self, hostname: str, port: int, timeout: int) -> None:
        try:
            with socket.create_connection((hostname, port), timeout=timeout):
                return
        except OSError as exc:
            raise NetworkValidationError(f"TCP_CONNECTION_FAILED: {hostname}:{port}") from exc

    def test_tls_connection(self, url: str, timeout: int) -> None:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            raise NetworkValidationError("DNS_RESOLUTION_FAILED: missing hostname")
        port = parsed.port or 443
        context = ssl.create_default_context()
        try:
            with socket.create_connection((hostname, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname):
                    return
        except ssl.SSLCertVerificationError as exc:
            raise TLSValidationError(f"TLS_CERTIFICATE_FAILED: {hostname}") from exc
        except OSError as exc:
            raise NetworkValidationError(f"TCP_CONNECTION_FAILED: {hostname}:{port}") from exc

    def endpoint_parts(self, url: str) -> tuple[str, int]:
        parsed = urlparse(url)
        if not parsed.hostname:
            raise NetworkValidationError("DNS_RESOLUTION_FAILED: missing hostname")
        return parsed.hostname, parsed.port or 443
