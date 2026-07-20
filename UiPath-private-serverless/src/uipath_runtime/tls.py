from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization

from .exceptions import InvalidCertificateError
from .models import CertificateMetadata


class CertificateManager:
    def validate_certificate(self, certificate: Path) -> CertificateMetadata:
        if not certificate.exists():
            raise InvalidCertificateError(f"Configured CA certificate does not exist. Path: {certificate}")
        if not certificate.is_file():
            raise InvalidCertificateError(f"Configured CA certificate is not a regular file. Path: {certificate}")
        data = certificate.read_bytes()
        certs = _load_pem_certificates(data, certificate)
        sha256 = hashlib.sha256(data).hexdigest()
        first = certs[0]
        fingerprint = first.fingerprint(hashes.SHA256()).hex(":").upper()
        return CertificateMetadata(path=certificate, sha256=sha256, fingerprint=f"SHA256:{fingerprint}")

    def install_host_certificate(self, metadata: CertificateMetadata) -> None:
        target = Path("/usr/local/share/ca-certificates/uipath-onprem-ca.crt")
        target.parent.mkdir(parents=True, exist_ok=True)
        source_bytes = metadata.path.read_bytes()
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != metadata.sha256:
            shutil.copyfile(metadata.path, target)
        subprocess.run(["update-ca-certificates"], check=True)


def _load_pem_certificates(data: bytes, path: Path) -> list[x509.Certificate]:
    certs: list[x509.Certificate] = []
    marker = b"-----END CERTIFICATE-----"
    for chunk in data.split(marker):
        if b"-----BEGIN CERTIFICATE-----" not in chunk:
            continue
        pem = chunk + marker + b"\n"
        try:
            certs.append(x509.load_pem_x509_certificate(pem))
        except ValueError as exc:
            raise InvalidCertificateError(f"Configured CA certificate is not a valid PEM certificate. Path: {path}") from exc
    if not certs:
        raise InvalidCertificateError(f"Configured CA certificate is not a valid PEM certificate. Path: {path}")
    for cert in certs:
        cert.public_bytes(serialization.Encoding.PEM)
    return certs
