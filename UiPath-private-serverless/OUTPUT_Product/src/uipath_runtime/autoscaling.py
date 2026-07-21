from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .models import AppConfig
from .scaling import ScaleChecker


@dataclass(frozen=True)
class UsageSample:
    total: int
    running: int
    active: int
    idle: int
    unknown: int
    min_idle_minutes: float

    @property
    def active_ratio(self) -> float:
        return 0.0 if self.running == 0 else self.active / self.running


@dataclass(frozen=True)
class CloudVm:
    id: str
    name: str
    status: str
    created_at: str = ""


@dataclass(frozen=True)
class AutoscaleDecision:
    action: str
    reason: str
    enabled: bool
    provider: str
    current_vms: int
    min_vms: int
    max_vms: int
    target_vm: str = ""
    applied: bool = False


class CloudProvider(Protocol):
    def list_vms(self) -> list[CloudVm]:
        ...

    def create_vm(self, name: str) -> CloudVm:
        ...

    def delete_vm(self, vm_id: str) -> None:
        ...


class LocalUsageMonitor:
    def sample(self, config: AppConfig, docker_manager) -> UsageSample:
        decisions = ScaleChecker().check(config, docker_manager, apply=False)
        running = sum(1 for item in decisions if item.docker_state == "running")
        active = sum(1 for item in decisions if item.active_state == "active")
        idle = sum(1 for item in decisions if item.active_state == "idle")
        unknown = sum(1 for item in decisions if item.active_state == "unknown")
        idle_minutes = [item.idle_minutes for item in decisions if item.active_state == "idle"]
        return UsageSample(
            total=len(decisions),
            running=running,
            active=active,
            idle=idle,
            unknown=unknown,
            min_idle_minutes=min(idle_minutes, default=0.0),
        )


class Autoscaler:
    def __init__(self, monitor: LocalUsageMonitor | None = None):
        self.monitor = monitor or LocalUsageMonitor()

    def check(self, config: AppConfig, docker_manager, provider: CloudProvider, *, apply: bool = False) -> tuple[UsageSample, AutoscaleDecision]:
        usage = self.monitor.sample(config, docker_manager)
        autoscaling = config.autoscaling
        if not autoscaling.enabled:
            return usage, AutoscaleDecision(
                action="disabled",
                reason="autoscaling.enabled is false",
                enabled=False,
                provider=autoscaling.provider,
                current_vms=0,
                min_vms=autoscaling.min_vms,
                max_vms=autoscaling.max_vms,
                applied=False,
            )

        vms = provider.list_vms()
        current_vms = len(vms)
        if usage.unknown:
            return usage, AutoscaleDecision(
                action="keep",
                reason="usage contains unknown containers",
                enabled=True,
                provider=autoscaling.provider,
                current_vms=current_vms,
                min_vms=autoscaling.min_vms,
                max_vms=autoscaling.max_vms,
                applied=False,
            )

        if usage.active_ratio >= autoscaling.scale_up_active_ratio and current_vms < autoscaling.max_vms:
            name = self._new_vm_name(config)
            applied = False
            if apply:
                created = provider.create_vm(name)
                name = created.name
                applied = True
            return usage, AutoscaleDecision(
                action="scale_up",
                reason=f"active ratio {usage.active_ratio:.2f} >= {autoscaling.scale_up_active_ratio:.2f}",
                enabled=True,
                provider=autoscaling.provider,
                current_vms=current_vms,
                min_vms=autoscaling.min_vms,
                max_vms=autoscaling.max_vms,
                target_vm=name,
                applied=applied,
            )

        can_scale_down = (
            usage.active_ratio <= autoscaling.scale_down_active_ratio
            and usage.idle == usage.running
            and usage.running > 0
            and usage.min_idle_minutes >= autoscaling.scale_down_idle_minutes
            and current_vms > autoscaling.min_vms
        )
        if can_scale_down:
            target = self._scale_down_candidate(vms, autoscaling.protected_vm_names)
            if target is None:
                return usage, AutoscaleDecision(
                    action="keep",
                    reason="no unprotected managed VM is available for scale down",
                    enabled=True,
                    provider=autoscaling.provider,
                    current_vms=current_vms,
                    min_vms=autoscaling.min_vms,
                    max_vms=autoscaling.max_vms,
                    applied=False,
                )
            applied = False
            if apply:
                provider.delete_vm(target.id)
                applied = True
            return usage, AutoscaleDecision(
                action="scale_down",
                reason=f"all containers idle for {usage.min_idle_minutes:.1f} minutes",
                enabled=True,
                provider=autoscaling.provider,
                current_vms=current_vms,
                min_vms=autoscaling.min_vms,
                max_vms=autoscaling.max_vms,
                target_vm=target.name,
                applied=applied,
            )

        return usage, AutoscaleDecision(
            action="keep",
            reason="usage is within autoscaling thresholds",
            enabled=True,
            provider=autoscaling.provider,
            current_vms=current_vms,
            min_vms=autoscaling.min_vms,
            max_vms=autoscaling.max_vms,
            applied=False,
        )

    def _new_vm_name(self, config: AppConfig) -> str:
        return f"{config.autoscaling.digitalocean.name_prefix}-{int(time.time())}"

    def _scale_down_candidate(self, vms: list[CloudVm], protected_names: tuple[str, ...]) -> CloudVm | None:
        protected = set(protected_names) | {socket.gethostname()}
        candidates = [vm for vm in vms if vm.name not in protected]
        return sorted(candidates, key=lambda vm: (vm.created_at, vm.name), reverse=True)[0] if candidates else None


class DigitalOceanProvider:
    endpoint = "https://api.digitalocean.com/v2"

    def __init__(self, config: AppConfig, *, environ: dict[str, str] | None = None):
        self.config = config.autoscaling.digitalocean
        env = environ if environ is not None else os.environ
        self.token = env.get(self.config.token_env, "")
        if not self.token:
            raise ValueError(f"DigitalOcean token not found in environment variable {self.config.token_env}")

    def list_vms(self) -> list[CloudVm]:
        tag = self.config.tags[0] if self.config.tags else ""
        path = "/droplets"
        if tag:
            path += f"?tag_name={urllib.parse.quote(tag)}"
        payload = self._request("GET", path)
        return [
            CloudVm(
                id=str(item.get("id", "")),
                name=str(item.get("name", "")),
                status=str(item.get("status", "")),
                created_at=str(item.get("created_at", "")),
            )
            for item in payload.get("droplets", [])
            if str(item.get("name", "")).startswith(self.config.name_prefix)
        ]

    def create_vm(self, name: str) -> CloudVm:
        body: dict[str, Any] = {
            "name": name,
            "region": self.config.region,
            "size": self.config.size,
            "image": self.config.image,
            "tags": list(self.config.tags),
        }
        if self.config.ssh_keys:
            body["ssh_keys"] = list(self.config.ssh_keys)
        if self.config.user_data_path is not None:
            body["user_data"] = self.config.user_data_path.read_text(encoding="utf-8")
        payload = self._request("POST", "/droplets", body)
        droplet = payload.get("droplet") or {}
        return CloudVm(
            id=str(droplet.get("id", "")),
            name=str(droplet.get("name", name)),
            status=str(droplet.get("status", "new")),
            created_at=str(droplet.get("created_at", "")),
        )

    def delete_vm(self, vm_id: str) -> None:
        self._request("DELETE", f"/droplets/{vm_id}")

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.endpoint}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DigitalOcean API {method} {path} failed: HTTP {exc.code} {details}") from exc
        if not raw:
            return {}
        return json.loads(raw)
