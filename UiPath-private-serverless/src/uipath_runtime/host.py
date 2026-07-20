from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from .exceptions import DockerUnavailableError, UnsupportedHostError
from .models import AppConfig

SUPPORTED_UBUNTU_VERSIONS = {"22.04", "24.04"}
REQUIRED_PACKAGES = [
    "ca-certificates",
    "curl",
    "gnupg",
    "openssl",
    "docker.io",
    "python3",
    "python3-venv",
]
DOCKER_COMPOSE_PACKAGES = ("docker-compose-plugin", "docker-compose-v2")
CONTAINER_UID = 1000
CONTAINER_GID = 1000


class HostManager:
    def validate_platform(self) -> None:
        os_release = _read_os_release()
        if os_release.get("ID") != "ubuntu" or os_release.get("VERSION_ID") not in SUPPORTED_UBUNTU_VERSIONS:
            raise UnsupportedHostError(
                "Unsupported operating system. MVP supports Ubuntu Server 22.04 LTS and 24.04 LTS."
            )
        arch = platform.machine().lower()
        if arch not in {"x86_64", "amd64"}:
            raise UnsupportedHostError(f"Unsupported architecture {arch}. The current MVP supports amd64 only.")

    def ensure_root(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            raise UnsupportedHostError("Initialization must run as root or with sudo.")

    def prepare_directories(self, config: AppConfig) -> None:
        dirs = [
            Path("/etc/uipath-runtime"),
            Path("/etc/uipath-runtime/certs"),
            Path("/var/lib/uipath-runtime"),
            config.packages.cache_path,
            config.packages.nuget_config_path.parent,
            Path("/var/lib/uipath-runtime/ca-image"),
            config.logs.host_path,
        ]
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)
        _chmod(config.packages.cache_path, 0o750)
        _chmod(config.logs.host_path, 0o755)
        _chown(config.packages.cache_path, CONTAINER_UID, CONTAINER_GID)

    def ensure_dependencies(self, *, auto_install: bool = False) -> None:
        missing = [pkg for pkg in REQUIRED_PACKAGES if shutil.which(pkg) is None and pkg != "docker.io"]
        if missing and not auto_install:
            return
        if auto_install:
            subprocess.run(["apt-get", "update"], check=True)
            subprocess.run(["apt-get", "install", "-y", *REQUIRED_PACKAGES], check=True)
            _install_first_available(DOCKER_COMPOSE_PACKAGES)

    def ensure_docker_service(self) -> None:
        docker_bin = shutil.which("docker")
        if not docker_bin:
            raise DockerUnavailableError("Docker Engine is unavailable. Confirm that Docker is installed.")
        subprocess.run(["systemctl", "enable", "--now", "docker"], check=False)
        result = subprocess.run([docker_bin, "info"], text=True, capture_output=True)
        if result.returncode != 0:
            raise DockerUnavailableError(
                "Docker Engine is unavailable. Confirm that Docker is installed and the docker service is running.",
                details=result.stderr.strip(),
            )

    def host_capacity(self) -> tuple[int, int]:
        cpus = os.cpu_count() or 0
        mem_kb = 0
        try:
            for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
                if line.startswith("MemTotal:"):
                    mem_kb = int(line.split()[1])
                    break
        except OSError:
            pass
        return cpus, mem_kb // 1024 // 1024


def _read_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


def _chmod(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except PermissionError:
        pass


def _chown(path: Path, uid: int, gid: int) -> None:
    try:
        os.chown(path, uid, gid)
    except PermissionError:
        pass


def _install_first_available(packages: tuple[str, ...]) -> None:
    for package in packages:
        result = subprocess.run(["apt-get", "install", "-y", package], text=True, capture_output=True)
        if result.returncode == 0:
            return
    raise DockerUnavailableError(
        "Docker Compose plugin package is unavailable. Tried: " + ", ".join(packages)
    )
