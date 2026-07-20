from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class HealthState(StrEnum):
    CONNECTED = "CONNECTED"
    RUNNING_NOT_CONFIRMED = "RUNNING_NOT_CONFIRMED"
    STOPPED = "STOPPED"
    RESTARTING = "RESTARTING"
    STARTUP_FAILED = "STARTUP_FAILED"
    NETWORK_FAILED = "NETWORK_FAILED"
    TLS_FAILED = "TLS_FAILED"
    ORCHESTRATOR_CONNECTION_FAILED = "ORCHESTRATOR_CONNECTION_FAILED"
    CONFIGURATION_DRIFT = "CONFIGURATION_DRIFT"
    IMAGE_MISSING = "IMAGE_MISSING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class AuthenticationConfig:
    type: str = "machine_key"
    machine_key_env: str = "UIPATH_MACHINE_KEY"


@dataclass(frozen=True)
class OrchestratorConfig:
    url: str
    organization: str | None = None
    tenant: str | None = None
    folder: str | None = None
    environment: str | None = None
    authentication: AuthenticationConfig = field(default_factory=AuthenticationConfig)


@dataclass(frozen=True)
class ResourceConfig:
    memory: str | None = None
    cpus: float | None = None


@dataclass(frozen=True)
class RuntimeConfig:
    image: str
    count: int = 1
    container_prefix: str = "uipath-robot"
    restart_policy: str = "unless-stopped"
    max_count: int = 100
    resources: ResourceConfig = field(default_factory=ResourceConfig)


@dataclass(frozen=True)
class DockerConfig:
    network_name: str = "uipath-runtime-network"
    dns: tuple[str, ...] = ("8.8.8.8", "1.1.1.1")


@dataclass(frozen=True)
class OfficialFeedConfig:
    enabled: bool = True
    name: str = "UiPath-Official"
    url: str = "https://pkgs.dev.azure.com/uipath/Public.Feeds/_packaging/UiPath-Official/nuget/v3/index.json"


@dataclass(frozen=True)
class PackagesConfig:
    cache_path: Path = Path("/var/lib/uipath-runtime/packages")
    nuget_config_path: Path = Path("/var/lib/uipath-runtime/nuget/NuGet.Config")
    container_cache_path: Path = Path("/application/Packages")
    container_nuget_config_path: Path = Path("/home/robotuser/.nuget/NuGet/NuGet.Config")
    official_feed: OfficialFeedConfig = field(default_factory=OfficialFeedConfig)


@dataclass(frozen=True)
class TLSConfig:
    ca_certificate: Path | None = None
    install_on_host: bool = True
    derived_image_prefix: str = "local/uipath-runtime"


@dataclass(frozen=True)
class LogsConfig:
    host_path: Path = Path("/var/log/uipath-runtime")
    retain_days: int = 30


@dataclass(frozen=True)
class HealthConfig:
    startup_timeout_seconds: int = 120
    connection_timeout_seconds: int = 30
    restart_loop_threshold: int = 3


@dataclass(frozen=True)
class AppConfig:
    version: int
    orchestrator: OrchestratorConfig
    runtime: RuntimeConfig
    docker: DockerConfig = field(default_factory=DockerConfig)
    packages: PackagesConfig = field(default_factory=PackagesConfig)
    tls: TLSConfig = field(default_factory=TLSConfig)
    logs: LogsConfig = field(default_factory=LogsConfig)
    health: HealthConfig = field(default_factory=HealthConfig)


@dataclass(frozen=True)
class SecretBundle:
    machine_key: str

    @property
    def masked_machine_key(self) -> str:
        return mask_secret(self.machine_key)


@dataclass(frozen=True)
class ImageMetadata:
    repository: str
    tag: str
    image_id: str
    digest: str | None = None
    created: str | None = None


@dataclass(frozen=True)
class CertificateMetadata:
    path: Path
    sha256: str
    fingerprint: str


@dataclass(frozen=True)
class ContainerSpec:
    name: str
    instance: str
    hostname: str
    image: str
    base_image: str
    network_name: str
    dns: tuple[str, ...]
    restart_policy: str
    orchestrator_url: str
    machine_key: str
    packages_cache_path: Path
    packages_container_path: Path
    nuget_config_path: Path
    nuget_container_path: Path
    log_path: Path
    environment_name: str | None
    ca_fingerprint: str | None
    memory: str | None = None
    cpus: float | None = None

    @property
    def labels(self) -> dict[str, str]:
        return {
            "com.uipath.runtime.managed": "true",
            "com.uipath.runtime.instance": self.instance,
            "com.uipath.runtime.environment": self.environment_name or "unknown",
            "com.uipath.runtime.config-version": "1",
            "com.uipath.runtime.base-image": self.base_image,
            "com.uipath.runtime.ca-fingerprint": self.ca_fingerprint or "none",
        }


@dataclass(frozen=True)
class ContainerStatus:
    name: str
    docker_state: str
    health: HealthState
    image: str
    message: str = ""


def mask_secret(value: str) -> str:
    if not value:
        return "****"
    return f"****{value[-4:]}" if len(value) > 4 else "****"
