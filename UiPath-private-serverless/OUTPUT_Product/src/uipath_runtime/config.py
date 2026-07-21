from __future__ import annotations

import ipaddress
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from .exceptions import InvalidConfigurationError
from .models import (
    AppConfig,
    ActiveJobProbeConfig,
    AuthenticationConfig,
    AutoscalingConfig,
    DigitalOceanConfig,
    DockerConfig,
    HealthConfig,
    LogsConfig,
    OfficialFeedConfig,
    OrchestratorConfig,
    PackagesConfig,
    ResourceConfig,
    RuntimeConfig,
    ScalingConfig,
    SecretBundle,
    TLSConfig,
)

DEFAULT_CONFIG_PATH = Path("/etc/uipath-runtime/config.yaml")
SECRET_FILE_PATH = Path("/etc/uipath-runtime/secrets.env")
ALLOWED_TOP_LEVEL = {
    "version",
    "orchestrator",
    "runtime",
    "docker",
    "packages",
    "tls",
    "logs",
    "health",
    "scaling",
    "autoscaling",
}


def load_config(path: Path = DEFAULT_CONFIG_PATH, *, count_override: int | None = None) -> AppConfig:
    if not path.exists():
        raise InvalidConfigurationError(f"Configuration file does not exist: {path}")
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise InvalidConfigurationError("Configuration root must be a mapping")
    unknown = sorted(set(raw) - ALLOWED_TOP_LEVEL)
    if unknown:
        raise InvalidConfigurationError(f"Unknown configuration fields: {', '.join(unknown)}")

    orchestrator_raw = _required_map(raw, "orchestrator")
    runtime_raw = _required_map(raw, "runtime")
    docker_raw = raw.get("docker") or {}
    packages_raw = raw.get("packages") or {}
    tls_raw = raw.get("tls") or {}
    logs_raw = raw.get("logs") or {}
    health_raw = raw.get("health") or {}
    scaling_raw = raw.get("scaling") or {}
    active_job_probe_raw = scaling_raw.get("active_job_probe") or {}
    autoscaling_raw = raw.get("autoscaling") or {}
    digitalocean_raw = autoscaling_raw.get("digitalocean") or {}

    auth_raw = orchestrator_raw.get("authentication") or {}
    auth = AuthenticationConfig(
        type=str(auth_raw.get("type", "machine_key")),
        machine_key_env=str(auth_raw.get("machine_key_env", "UIPATH_MACHINE_KEY")),
    )

    runtime = RuntimeConfig(
        image=_required_str(runtime_raw, "image"),
        count=int(count_override if count_override is not None else runtime_raw.get("count", 1)),
        container_prefix=_required_str(runtime_raw, "container_prefix"),
        restart_policy=str(runtime_raw.get("restart_policy", "unless-stopped")),
        max_count=int(runtime_raw.get("max_count", 100)),
        resources=ResourceConfig(
            memory=(runtime_raw.get("resources") or {}).get("memory"),
            cpus=(runtime_raw.get("resources") or {}).get("cpus"),
        ),
    )

    config = AppConfig(
        version=int(raw.get("version", 1)),
        orchestrator=OrchestratorConfig(
            url=_required_str(orchestrator_raw, "url"),
            organization=orchestrator_raw.get("organization"),
            tenant=orchestrator_raw.get("tenant"),
            folder=orchestrator_raw.get("folder"),
            environment=orchestrator_raw.get("environment"),
            authentication=auth,
        ),
        runtime=runtime,
        docker=DockerConfig(
            network_name=str(docker_raw.get("network_name", "uipath-runtime-network")),
            dns=tuple(str(item) for item in docker_raw.get("dns", ["8.8.8.8", "1.1.1.1"])),
        ),
        packages=PackagesConfig(
            cache_path=Path(packages_raw.get("cache_path", "/var/lib/uipath-runtime/packages")),
            nuget_config_path=Path(packages_raw.get("nuget_config_path", "/var/lib/uipath-runtime/nuget/NuGet.Config")),
            container_cache_path=Path(packages_raw.get("container_cache_path", "/application/Packages")),
            container_nuget_config_path=Path(
                packages_raw.get("container_nuget_config_path", "/home/robotuser/.nuget/NuGet/NuGet.Config")
            ),
            official_feed=OfficialFeedConfig(
                enabled=bool((packages_raw.get("official_feed") or {}).get("enabled", True)),
                name=str((packages_raw.get("official_feed") or {}).get("name", "UiPath-Official")),
                url=str(
                    (packages_raw.get("official_feed") or {}).get(
                        "url",
                        "https://pkgs.dev.azure.com/uipath/Public.Feeds/_packaging/UiPath-Official/nuget/v3/index.json",
                    )
                ),
            ),
        ),
        tls=TLSConfig(
            ca_certificate=_optional_path(tls_raw.get("ca_certificate")),
            install_on_host=bool(tls_raw.get("install_on_host", True)),
            derived_image_prefix=str(tls_raw.get("derived_image_prefix", "local/uipath-runtime")),
        ),
        logs=LogsConfig(
            host_path=Path(logs_raw.get("host_path", "/var/log/uipath-runtime")),
            retain_days=int(logs_raw.get("retain_days", 30)),
        ),
        health=HealthConfig(
            startup_timeout_seconds=int(health_raw.get("startup_timeout_seconds", 120)),
            connection_timeout_seconds=int(health_raw.get("connection_timeout_seconds", 30)),
            restart_loop_threshold=int(health_raw.get("restart_loop_threshold", 3)),
        ),
        scaling=ScalingConfig(
            minimum_count=int(scaling_raw.get("minimum_count", 1)),
            burst_max_count=int(scaling_raw.get("burst_max_count", runtime.max_count)),
            idle_minutes_before_stop=int(scaling_raw.get("idle_minutes_before_stop", 30)),
            poll_interval_seconds=int(scaling_raw.get("poll_interval_seconds", 60)),
            state_path=Path(scaling_raw.get("state_path", "/var/lib/uipath-runtime/scaling-state.json")),
            active_job_probe=ActiveJobProbeConfig(
                command=tuple(
                    str(item)
                    for item in active_job_probe_raw.get(
                        "command",
                        [
                            "/bin/sh",
                            "-lc",
                            "pgrep -af '[U]iPath.Executor|[U]iPath.Robot.Executor' >/dev/null",
                        ],
                    )
                )
            ),
        ),
        autoscaling=AutoscalingConfig(
            enabled=_bool(autoscaling_raw.get("enabled", False)),
            provider=str(autoscaling_raw.get("provider", "digitalocean")),
            min_vms=int(autoscaling_raw.get("min_vms", 1)),
            max_vms=int(autoscaling_raw.get("max_vms", 1)),
            scale_up_active_ratio=float(autoscaling_raw.get("scale_up_active_ratio", 0.8)),
            scale_down_active_ratio=float(autoscaling_raw.get("scale_down_active_ratio", 0.1)),
            scale_down_idle_minutes=int(autoscaling_raw.get("scale_down_idle_minutes", 30)),
            protected_vm_names=tuple(str(item) for item in autoscaling_raw.get("protected_vm_names", [])),
            digitalocean=DigitalOceanConfig(
                token_env=str(digitalocean_raw.get("token_env", "DIGITALOCEAN_TOKEN")),
                region=str(digitalocean_raw.get("region", "nyc1")),
                size=str(digitalocean_raw.get("size", "s-2vcpu-2gb")),
                image=str(digitalocean_raw.get("image", "ubuntu-24-04-x64")),
                ssh_keys=tuple(str(item) for item in digitalocean_raw.get("ssh_keys", [])),
                tags=tuple(str(item) for item in digitalocean_raw.get("tags", ["uipath-runtime"])),
                name_prefix=str(digitalocean_raw.get("name_prefix", "uipath-runtime-worker")),
                user_data_path=_optional_path(digitalocean_raw.get("user_data_path")),
            ),
        ),
    )
    validate_config(config)
    return config


def validate_config(config: AppConfig) -> None:
    parsed = urlparse(config.orchestrator.url)
    if parsed.scheme != "https":
        raise InvalidConfigurationError("orchestrator.url must use HTTPS for MVP 1")
    if not parsed.hostname:
        raise InvalidConfigurationError("orchestrator.url must include a hostname")
    if config.orchestrator.authentication.type != "machine_key":
        raise InvalidConfigurationError(
            f"Unsupported authentication type: {config.orchestrator.authentication.type}"
        )
    if config.runtime.count < 1:
        raise InvalidConfigurationError("runtime.count must be at least 1")
    if config.runtime.count > config.runtime.max_count:
        raise InvalidConfigurationError(
            f"runtime.count {config.runtime.count} exceeds maximum {config.runtime.max_count}"
        )
    if config.scaling.minimum_count < 0:
        raise InvalidConfigurationError("scaling.minimum_count must be at least 0")
    if config.scaling.burst_max_count < config.scaling.minimum_count:
        raise InvalidConfigurationError("scaling.burst_max_count must be greater than or equal to scaling.minimum_count")
    if config.runtime.count > config.scaling.burst_max_count:
        raise InvalidConfigurationError(
            f"runtime.count {config.runtime.count} exceeds scaling.burst_max_count {config.scaling.burst_max_count}"
        )
    if config.scaling.idle_minutes_before_stop < 1:
        raise InvalidConfigurationError("scaling.idle_minutes_before_stop must be at least 1")
    if config.scaling.poll_interval_seconds < 1:
        raise InvalidConfigurationError("scaling.poll_interval_seconds must be at least 1")
    if not config.scaling.active_job_probe.command:
        raise InvalidConfigurationError("scaling.active_job_probe.command must not be empty")
    if config.autoscaling.provider != "digitalocean":
        raise InvalidConfigurationError(f"Unsupported autoscaling provider: {config.autoscaling.provider}")
    if config.autoscaling.min_vms < 1:
        raise InvalidConfigurationError("autoscaling.min_vms must be at least 1")
    if config.autoscaling.max_vms < config.autoscaling.min_vms:
        raise InvalidConfigurationError("autoscaling.max_vms must be greater than or equal to autoscaling.min_vms")
    for name, value in [
        ("autoscaling.scale_up_active_ratio", config.autoscaling.scale_up_active_ratio),
        ("autoscaling.scale_down_active_ratio", config.autoscaling.scale_down_active_ratio),
    ]:
        if value < 0 or value > 1:
            raise InvalidConfigurationError(f"{name} must be between 0 and 1")
    if config.autoscaling.scale_down_idle_minutes < 1:
        raise InvalidConfigurationError("autoscaling.scale_down_idle_minutes must be at least 1")
    if not config.autoscaling.digitalocean.token_env:
        raise InvalidConfigurationError("autoscaling.digitalocean.token_env is required")
    if not config.autoscaling.digitalocean.region:
        raise InvalidConfigurationError("autoscaling.digitalocean.region is required")
    if not config.autoscaling.digitalocean.size:
        raise InvalidConfigurationError("autoscaling.digitalocean.size is required")
    if not config.autoscaling.digitalocean.image:
        raise InvalidConfigurationError("autoscaling.digitalocean.image is required")
    if not config.autoscaling.digitalocean.name_prefix:
        raise InvalidConfigurationError("autoscaling.digitalocean.name_prefix is required")
    if config.autoscaling.digitalocean.user_data_path is not None and not config.autoscaling.digitalocean.user_data_path.is_absolute():
        raise InvalidConfigurationError(
            f"autoscaling.digitalocean.user_data_path must be absolute: {config.autoscaling.digitalocean.user_data_path}"
        )
    if ":" not in config.runtime.image or config.runtime.image.endswith(":latest"):
        raise InvalidConfigurationError("runtime.image must contain an explicit non-latest tag")
    if not config.runtime.container_prefix:
        raise InvalidConfigurationError("runtime.container_prefix is required")
    if not config.docker.network_name:
        raise InvalidConfigurationError("docker.network_name is required")
    for dns in config.docker.dns:
        try:
            ipaddress.ip_address(dns)
        except ValueError as exc:
            raise InvalidConfigurationError(f"Invalid DNS address: {dns}") from exc
    for path in [
        config.packages.cache_path,
        config.packages.nuget_config_path,
        config.packages.container_cache_path,
        config.packages.container_nuget_config_path,
        config.logs.host_path,
        config.scaling.state_path,
    ]:
        if not path.is_absolute():
            raise InvalidConfigurationError(f"Path must be absolute: {path}")
    if config.tls.ca_certificate is not None and not config.tls.ca_certificate.is_absolute():
        raise InvalidConfigurationError(f"CA certificate path must be absolute: {config.tls.ca_certificate}")


def resolve_secrets(config: AppConfig, *, env: dict[str, str] | None = None, secret_file: Path = SECRET_FILE_PATH) -> SecretBundle:
    env = env if env is not None else os.environ
    key_name = config.orchestrator.authentication.machine_key_env
    machine_key = env.get(key_name)
    if not machine_key and secret_file.exists():
        machine_key = _read_secret_file(secret_file).get(key_name)
    if not machine_key:
        raise InvalidConfigurationError(f"Machine key not found in environment variable {key_name}")
    return SecretBundle(machine_key=machine_key)


def _read_secret_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _required_map(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise InvalidConfigurationError(f"{key} section is required")
    return value


def _required_str(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if value is None or str(value).strip() == "":
        raise InvalidConfigurationError(f"{key} is required")
    return str(value)


def _optional_path(value: Any) -> Path | None:
    if value in (None, ""):
        return None
    return Path(str(value))


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
