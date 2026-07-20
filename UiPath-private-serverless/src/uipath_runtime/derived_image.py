from __future__ import annotations

import hashlib
from pathlib import Path

from .exceptions import RuntimeProvisionerError
from .models import CertificateMetadata


DOCKERFILE_VERSION = "v1"


class DerivedImageManager:
    def determine_image_tag(self, prefix: str, base_image: str, base_image_id: str, cert: CertificateMetadata) -> str:
        source = f"{base_image_id}|{cert.sha256}|{DOCKERFILE_VERSION}".encode("utf-8")
        suffix = hashlib.sha256(source).hexdigest()[:8]
        base_tag = base_image.split(":", 1)[1].replace("/", "-")
        return f"{prefix}:{base_tag}-ca-{suffix}"

    def write_build_context(self, build_dir: Path, base_image: str, cert: CertificateMetadata) -> Path:
        build_dir.mkdir(parents=True, exist_ok=True)
        cert_target = build_dir / "company-root-ca.crt"
        cert_target.write_bytes(cert.path.read_bytes())
        dockerfile = build_dir / "Dockerfile"
        dockerfile.write_text(
            "ARG UIPATH_BASE_IMAGE\n"
            "FROM ${UIPATH_BASE_IMAGE}\n"
            "USER root\n"
            "COPY company-root-ca.crt /usr/local/share/ca-certificates/uipath-onprem-ca.crt\n"
            "RUN update-ca-certificates\n"
            "USER 1000\n",
            encoding="utf-8",
        )
        return dockerfile

    def ensure_ca_image(self, docker_manager, base_image: str, base_image_id: str, cert: CertificateMetadata, prefix: str) -> str:
        tag = self.determine_image_tag(prefix, base_image, base_image_id, cert)
        if docker_manager.image_exists(tag):
            return tag
        build_dir = Path("/var/lib/uipath-runtime/ca-image")
        self.write_build_context(build_dir, base_image, cert)
        if not docker_manager.build_image(build_dir, tag, {"UIPATH_BASE_IMAGE": base_image}):
            raise RuntimeProvisionerError(f"Failed to build derived CA image: {tag}")
        return tag
