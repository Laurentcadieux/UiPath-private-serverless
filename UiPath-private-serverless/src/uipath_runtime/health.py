from __future__ import annotations

from .models import ContainerStatus, HealthState


ORCHESTRATOR_SUCCESS_MARKERS = (
    "connected to orchestrator",
    "robot connected",
    "registration succeeded",
    "successfully connected",
)


def classify_from_logs(current: ContainerStatus, logs: str) -> ContainerStatus:
    lowered = logs.lower()
    if any(marker in lowered for marker in ORCHESTRATOR_SUCCESS_MARKERS):
        return ContainerStatus(current.name, current.docker_state, HealthState.CONNECTED, current.image, "log evidence")
    if "certificate" in lowered and ("failed" in lowered or "error" in lowered):
        return ContainerStatus(current.name, current.docker_state, HealthState.TLS_FAILED, current.image, "TLS error in logs")
    if "orchestrator" in lowered and ("failed" in lowered or "error" in lowered):
        return ContainerStatus(
            current.name,
            current.docker_state,
            HealthState.ORCHESTRATOR_CONNECTION_FAILED,
            current.image,
            "Orchestrator error in logs",
        )
    return current
