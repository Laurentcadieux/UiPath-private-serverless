from __future__ import annotations

import unittest
from pathlib import Path

from uipath_runtime.docker_manager import detect_drift
from uipath_runtime.models import ContainerSpec


def spec(log_path: Path | None = None) -> ContainerSpec:
    return ContainerSpec(
        name="uipath-robot-001",
        instance="001",
        hostname="uipath-robot-001",
        image="repo/image:1.0",
        base_image="repo/image:1.0",
        network_name="net",
        dns=("8.8.8.8",),
        restart_policy="unless-stopped",
        orchestrator_url="https://orchestrator.example.com",
        machine_key="secret",
        packages_cache_path=Path("/var/lib/uipath-runtime/packages"),
        packages_container_path=Path("/application/Packages"),
        nuget_config_path=Path("/var/lib/uipath-runtime/nuget/NuGet.Config"),
        nuget_container_path=Path("/home/robotuser/.nuget/NuGet/NuGet.Config"),
        log_path=log_path or Path("/var/log/uipath-runtime/uipath-robot-001"),
        environment_name="Production",
        ca_fingerprint=None,
    )


class DriftDetectionTests(unittest.TestCase):
    def test_no_drift_for_matching_container(self) -> None:
        attrs = {
            "Config": {
                "Labels": spec().labels,
                "Env": ["ORCHESTRATOR_URL=https://orchestrator.example.com"],
            },
            "HostConfig": {"Dns": ["8.8.8.8"], "RestartPolicy": {"Name": "unless-stopped"}},
        }
        self.assertEqual(detect_drift(attrs, spec()), [])

    def test_detects_ca_drift(self) -> None:
        attrs = {
            "Config": {
                "Labels": {**spec().labels, "com.uipath.runtime.ca-fingerprint": "SHA256:OLD"},
                "Env": ["ORCHESTRATOR_URL=https://orchestrator.example.com"],
            },
            "HostConfig": {"Dns": ["8.8.8.8"], "RestartPolicy": {"Name": "unless-stopped"}},
        }
        self.assertIn("CA fingerprint", detect_drift(attrs, spec()))


if __name__ == "__main__":
    unittest.main()
