from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .models import AppConfig, ContainerSpec, ContainerStatus, SecretBundle
from .naming import container_name, instance_id


@dataclass
class ReconcileReport:
    requested: int
    existing: int = 0
    created: int = 0
    started: int = 0
    unchanged: int = 0
    drifted: int = 0
    failed: int = 0
    statuses: list[ContainerStatus] = field(default_factory=list)

    @property
    def running(self) -> int:
        return sum(1 for item in self.statuses if item.docker_state == "running")


class Reconciler:
    def build_specs(
        self,
        config: AppConfig,
        secrets: SecretBundle,
        *,
        effective_image: str,
        base_image: str,
        ca_fingerprint: str | None,
    ) -> list[ContainerSpec]:
        specs: list[ContainerSpec] = []
        for index in range(1, config.runtime.count + 1):
            name = container_name(config.runtime.container_prefix, index)
            specs.append(
                ContainerSpec(
                    name=name,
                    instance=instance_id(index),
                    hostname=name,
                    image=effective_image,
                    base_image=base_image,
                    network_name=config.docker.network_name,
                    dns=config.docker.dns,
                    restart_policy=config.runtime.restart_policy,
                    orchestrator_url=config.orchestrator.url,
                    machine_key=secrets.machine_key,
                    packages_cache_path=config.packages.cache_path,
                    packages_container_path=config.packages.container_cache_path,
                    nuget_config_path=config.packages.nuget_config_path,
                    nuget_container_path=config.packages.container_nuget_config_path,
                    log_path=Path(config.logs.host_path) / name,
                    environment_name=config.orchestrator.environment,
                    ca_fingerprint=ca_fingerprint,
                    memory=config.runtime.resources.memory,
                    cpus=config.runtime.resources.cpus,
                )
            )
        return specs

    def reconcile(self, docker_manager, specs: list[ContainerSpec], *, recreate: bool) -> ReconcileReport:
        report = ReconcileReport(requested=len(specs), existing=len(docker_manager.list_managed_containers()))
        for spec in specs:
            spec.log_path.mkdir(parents=True, exist_ok=True)
            try:
                action, status = docker_manager.ensure_container(spec, recreate=recreate)
                report.statuses.append(status)
                if action == "created":
                    report.created += 1
                elif action == "started":
                    report.started += 1
                elif action == "unchanged":
                    report.unchanged += 1
                elif action == "drifted":
                    report.drifted += 1
            except Exception as exc:
                report.failed += 1
                raise exc
        return report
