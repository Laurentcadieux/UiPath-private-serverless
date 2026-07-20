from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from .models import AppConfig, ContainerStatus, HealthState


@dataclass(frozen=True)
class ScaleDecision:
    name: str
    docker_state: str
    health: HealthState
    active_state: str
    idle_minutes: float
    eligible_to_stop: bool
    action: str
    message: str = ""


class ScaleChecker:
    def check(self, config: AppConfig, docker_manager, *, apply: bool = False) -> list[ScaleDecision]:
        now = time.time()
        state = _load_state(config.scaling.state_path)
        statuses = sorted(docker_manager.status(), key=lambda item: item.name)
        excess_count = max(0, len(statuses) - config.scaling.minimum_count)
        decisions: list[ScaleDecision] = []
        stop_candidates: list[str] = []

        for status in statuses:
            active_state, message = self._active_state(config, docker_manager, status)
            if active_state in {"active", "unknown"}:
                state[status.name] = now
                idle_minutes = 0.0
            else:
                last_active = float(state.get(status.name, now))
                state.setdefault(status.name, last_active)
                idle_minutes = max(0.0, (now - last_active) / 60)

            eligible = (
                status.docker_state == "running"
                and active_state == "idle"
                and idle_minutes >= config.scaling.idle_minutes_before_stop
            )
            if eligible:
                stop_candidates.append(status.name)

            decisions.append(
                ScaleDecision(
                    name=status.name,
                    docker_state=status.docker_state,
                    health=status.health,
                    active_state=active_state,
                    idle_minutes=idle_minutes,
                    eligible_to_stop=eligible,
                    action="keep",
                    message=message,
                )
            )

        stops = set(sorted(stop_candidates, reverse=True)[:excess_count])
        applied_decisions: list[ScaleDecision] = []
        for decision in decisions:
            action = "stop" if decision.name in stops else "keep"
            if apply and action == "stop":
                docker_manager.stop_container(decision.name)
                action = "stopped"
            applied_decisions.append(
                ScaleDecision(
                    name=decision.name,
                    docker_state=decision.docker_state,
                    health=decision.health,
                    active_state=decision.active_state,
                    idle_minutes=decision.idle_minutes,
                    eligible_to_stop=decision.eligible_to_stop,
                    action=action,
                    message=decision.message,
                )
            )

        _save_state(config.scaling.state_path, state)
        return applied_decisions

    def _active_state(self, config: AppConfig, docker_manager, status: ContainerStatus) -> tuple[str, str]:
        if status.docker_state != "running":
            return "unknown", "container is not running"
        exit_code, output = docker_manager.exec_in_container(status.name, config.scaling.active_job_probe.command)
        if exit_code == 0:
            return "active", output.strip()
        if exit_code == 1:
            return "idle", output.strip()
        return "unknown", f"probe exit {exit_code}: {output.strip()}"


def _load_state(path: Path) -> dict[str, float]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): float(value) for key, value in raw.items() if isinstance(value, (int, float))}


def _save_state(path: Path, state: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
