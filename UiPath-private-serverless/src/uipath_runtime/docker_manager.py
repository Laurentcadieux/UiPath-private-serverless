from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .exceptions import DockerUnavailableError, ImageNotFoundError
from .models import ContainerSpec, ContainerStatus, HealthState, ImageMetadata

MANAGED_LABEL = "com.uipath.runtime.managed"


class DockerManager:
    def __init__(self):
        try:
            import docker  # type: ignore
        except ModuleNotFoundError as exc:
            raise DockerUnavailableError("Python Docker SDK is not installed. Install docker>=7.") from exc
        try:
            self.client = docker.from_env()
            self.client.ping()
        except Exception as exc:  # pragma: no cover - depends on host daemon
            raise DockerUnavailableError("Docker Engine is unavailable.") from exc

    def image_exists(self, image: str) -> bool:
        try:
            self.client.images.get(image)
            return True
        except Exception:
            return False

    def load_image_archive(self, archive: Path) -> None:
        if not archive.exists():
            raise ImageNotFoundError(f"Image archive does not exist: {archive}")
        subprocess.run(["docker", "load", "--input", str(archive)], check=True)

    def image_metadata(self, image: str) -> ImageMetadata:
        try:
            img = self.client.images.get(image)
        except Exception as exc:
            raise ImageNotFoundError(
                f"UiPath Robot image is not available locally. Required image: {image}. "
                "Load the image before running init: docker load --input /path/to/uipath-robot-image.tar"
            ) from exc
        attrs = img.attrs
        repo, tag = split_image(image)
        digests = attrs.get("RepoDigests") or []
        return ImageMetadata(
            repository=repo,
            tag=tag,
            image_id=attrs.get("Id", ""),
            digest=digests[0] if digests else None,
            created=attrs.get("Created"),
        )

    def ensure_network(self, name: str) -> None:
        existing = self.client.networks.list(names=[name])
        if existing:
            attrs = existing[0].attrs
            driver = attrs.get("Driver") or attrs.get("Options", {}).get("com.docker.network.driver")
            if driver and driver != "bridge":
                raise DockerUnavailableError(f"Docker network {name} exists but is not a bridge network.")
            return
        self.client.networks.create(name, driver="bridge")

    def build_image(self, build_dir: Path, tag: str, buildargs: dict[str, str]) -> bool:
        try:
            self.client.images.build(path=str(build_dir), tag=tag, buildargs=buildargs, rm=True)
            return True
        except Exception:
            return False

    def list_managed_containers(self) -> list[Any]:
        return self.client.containers.list(all=True, filters={"label": f"{MANAGED_LABEL}=true"})

    def get_container(self, name: str):
        try:
            return self.client.containers.get(name)
        except Exception:
            return None

    def exec_in_container(self, name: str, command: tuple[str, ...]) -> tuple[int, str]:
        container = self.get_container(name)
        if container is None:
            return 127, "container not found"
        result = container.exec_run(list(command), stdout=True, stderr=True)
        output = result.output
        if isinstance(output, bytes):
            output_text = output.decode("utf-8", errors="replace")
        else:
            output_text = str(output)
        return int(result.exit_code), output_text

    def stop_container(self, name: str, *, timeout: int = 30) -> None:
        container = self.get_container(name)
        if container is not None:
            container.stop(timeout=timeout)

    def ensure_container(self, spec: ContainerSpec, *, recreate: bool = False) -> tuple[str, ContainerStatus]:
        existing = self.get_container(spec.name)
        if existing:
            drift = detect_drift(existing.attrs, spec)
            if drift and not recreate:
                return "drifted", ContainerStatus(spec.name, existing.status, HealthState.CONFIGURATION_DRIFT, spec.image, ", ".join(drift))
            if drift and recreate:
                existing.remove(force=True)
                existing = None
            elif existing.status != "running":
                existing.start()
                return "started", ContainerStatus(spec.name, "running", HealthState.RUNNING_NOT_CONFIRMED, spec.image)
            else:
                return "unchanged", ContainerStatus(spec.name, "running", HealthState.RUNNING_NOT_CONFIRMED, spec.image)

        mounts = {
            str(spec.packages_cache_path): {"bind": str(spec.packages_container_path), "mode": "rw"},
            str(spec.nuget_config_path): {"bind": str(spec.nuget_container_path), "mode": "ro"},
            str(spec.log_path): {"bind": "/home/robotuser/.local/share/UiPath/Logs", "mode": "rw"},
        }
        environment = {
            "LICENSE_AGREEMENT": "accept",
            "ORCHESTRATOR_URL": spec.orchestrator_url,
            "MACHINE_KEY": spec.machine_key,
        }
        host_config: dict[str, Any] = {
            "name": spec.name,
            "hostname": spec.hostname,
            "image": spec.image,
            "detach": True,
            "network": spec.network_name,
            "dns": list(spec.dns),
            "restart_policy": {"Name": spec.restart_policy},
            "labels": spec.labels,
            "environment": environment,
            "volumes": mounts,
        }
        if spec.memory:
            host_config["mem_limit"] = spec.memory
        if spec.cpus:
            host_config["nano_cpus"] = int(float(spec.cpus) * 1_000_000_000)
        self.client.containers.run(**host_config)
        return "created", ContainerStatus(spec.name, "running", HealthState.RUNNING_NOT_CONFIRMED, spec.image)

    def status(self) -> list[ContainerStatus]:
        statuses: list[ContainerStatus] = []
        for container in self.list_managed_containers():
            labels = container.attrs.get("Config", {}).get("Labels", {}) or {}
            image = labels.get("com.uipath.runtime.base-image", "")
            state = container.attrs.get("State", {}) or {}
            docker_state = state.get("Status", container.status)
            health = HealthState.RUNNING_NOT_CONFIRMED if docker_state == "running" else HealthState.STOPPED
            if docker_state == "restarting":
                health = HealthState.RESTARTING
            if docker_state == "running" and _has_connection_evidence(_container_logs(container)):
                health = HealthState.CONNECTED
            statuses.append(ContainerStatus(container.name, docker_state, health, image))
        return sorted(statuses, key=lambda item: item.name)


def split_image(image: str) -> tuple[str, str]:
    repo, tag = image.rsplit(":", 1)
    return repo, tag


def detect_drift(attrs: dict[str, Any], spec: ContainerSpec) -> list[str]:
    drift: list[str] = []
    config = attrs.get("Config", {}) or {}
    host_config = attrs.get("HostConfig", {}) or {}
    labels = config.get("Labels", {}) or {}
    env = dict(item.split("=", 1) for item in config.get("Env", []) if "=" in item)
    if labels.get("com.uipath.runtime.base-image") != spec.base_image:
        drift.append("base image")
    if labels.get("com.uipath.runtime.ca-fingerprint") != (spec.ca_fingerprint or "none"):
        drift.append("CA fingerprint")
    if env.get("ORCHESTRATOR_URL") != spec.orchestrator_url:
        drift.append("orchestrator URL")
    if sorted(host_config.get("Dns") or []) != sorted(spec.dns):
        drift.append("DNS servers")
    if (host_config.get("RestartPolicy") or {}).get("Name") != spec.restart_policy:
        drift.append("restart policy")
    return drift


def _container_logs(container: Any) -> str:
    try:
        raw = container.logs(tail=300)
    except Exception:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


def _has_connection_evidence(log_text: str) -> bool:
    return any(
        marker in log_text
        for marker in (
            "Successfully connected to Orchestrator",
            "HeartbeatV2 Status:OK",
            "robotsservice/HeartbeatV2 Status:OK",
        )
    )
