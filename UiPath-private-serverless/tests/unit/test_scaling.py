from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uipath_runtime.config import load_config
from uipath_runtime.models import ContainerStatus, HealthState
from uipath_runtime.scaling import ScaleChecker


CONFIG = """
version: 1
orchestrator:
  url: "https://orchestrator.example.com"
  authentication:
    type: "machine_key"
    machine_key_env: "UIPATH_MACHINE_KEY"
runtime:
  count: 3
  container_prefix: "uipath-robot"
  image: "uipathprod.azurecr.io/robot/uiautomation-runtime:latest24.10"
docker:
  network_name: "uipath-runtime-network"
  dns: ["8.8.8.8", "1.1.1.1"]
scaling:
  minimum_count: 1
  burst_max_count: 3
  idle_minutes_before_stop: 1
  state_path: "{state_path}"
  active_job_probe:
    command: ["/bin/sh", "-lc", "probe"]
"""


class FakeDocker:
    def __init__(self, exit_codes: dict[str, int]):
        self.exit_codes = exit_codes
        self.stopped: list[str] = []

    def status(self):
        return [
            ContainerStatus("uipath-robot-001", "running", HealthState.CONNECTED, "image"),
            ContainerStatus("uipath-robot-002", "running", HealthState.CONNECTED, "image"),
            ContainerStatus("uipath-robot-003", "running", HealthState.CONNECTED, "image"),
        ]

    def exec_in_container(self, name, command):
        return self.exit_codes[name], ""

    def stop_container(self, name, *, timeout=30):
        self.stopped.append(name)


class ScalingTests(unittest.TestCase):
    def config(self, state_path: Path):
        handle = tempfile.NamedTemporaryFile("w", delete=False)
        handle.write(CONFIG.format(state_path=state_path))
        handle.close()
        return load_config(Path(handle.name))

    def test_does_not_stop_on_first_idle_observation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(Path(tmp) / "state.json")
            fake = FakeDocker({"uipath-robot-001": 1, "uipath-robot-002": 1, "uipath-robot-003": 1})
            decisions = ScaleChecker().check(config, fake, apply=True)
            self.assertEqual(fake.stopped, [])
            self.assertTrue(all(not decision.eligible_to_stop for decision in decisions))

    def test_stops_only_excess_idle_containers_after_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            state_path.write_text(
                '{"uipath-robot-001": 1, "uipath-robot-002": 1, "uipath-robot-003": 1}',
                encoding="utf-8",
            )
            config = self.config(state_path)
            fake = FakeDocker({"uipath-robot-001": 1, "uipath-robot-002": 1, "uipath-robot-003": 1})
            ScaleChecker().check(config, fake, apply=True)
            self.assertEqual(fake.stopped, ["uipath-robot-002", "uipath-robot-003"])

    def test_unknown_probe_is_conservative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            state_path.write_text('{"uipath-robot-002": 1, "uipath-robot-003": 1}', encoding="utf-8")
            config = self.config(state_path)
            fake = FakeDocker({"uipath-robot-001": 1, "uipath-robot-002": 2, "uipath-robot-003": 1})
            ScaleChecker().check(config, fake, apply=True)
            self.assertEqual(fake.stopped, ["uipath-robot-003"])


if __name__ == "__main__":
    unittest.main()
