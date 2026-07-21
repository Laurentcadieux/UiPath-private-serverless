from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from uipath_runtime.autoscaling import Autoscaler, CloudVm
from uipath_runtime.config import load_config
from uipath_runtime.models import ContainerStatus, HealthState


CONFIG = """
version: 1
orchestrator:
  url: "https://orchestrator.example.com"
  authentication:
    type: "machine_key"
    machine_key_env: "UIPATH_MACHINE_KEY"
runtime:
  count: 2
  container_prefix: "uipath-robot"
  image: "uipathprod.azurecr.io/robot/uiautomation-runtime:latest24.10"
docker:
  network_name: "uipath-runtime-network"
  dns: ["8.8.8.8", "1.1.1.1"]
scaling:
  minimum_count: 1
  burst_max_count: 2
  idle_minutes_before_stop: 1
  state_path: "{state_path}"
  active_job_probe:
    command: ["/bin/sh", "-lc", "probe"]
autoscaling:
  enabled: {enabled}
  provider: "digitalocean"
  min_vms: 1
  max_vms: 3
  scale_up_active_ratio: 0.8
  scale_down_active_ratio: 0.1
  scale_down_idle_minutes: 1
  protected_vm_names: ["uipath-runtime-worker-001"]
  digitalocean:
    token_env: "DIGITALOCEAN_TOKEN"
    region: "nyc1"
    size: "s-2vcpu-2gb"
    image: "ubuntu-24-04-x64"
    ssh_keys: []
    tags: ["uipath-runtime"]
    name_prefix: "uipath-runtime-worker"
"""


class FakeDocker:
    def __init__(self, exit_codes: dict[str, int]):
        self.exit_codes = exit_codes

    def status(self):
        return [
            ContainerStatus("uipath-robot-001", "running", HealthState.CONNECTED, "image"),
            ContainerStatus("uipath-robot-002", "running", HealthState.CONNECTED, "image"),
        ]

    def exec_in_container(self, name, command):
        return self.exit_codes[name], ""


class FakeProvider:
    def __init__(self):
        self.created: list[str] = []
        self.deleted: list[str] = []
        self.vms = [
            CloudVm("1", "uipath-runtime-worker-001", "active", "2026-01-01T00:00:00Z"),
            CloudVm("2", "uipath-runtime-worker-002", "active", "2026-01-02T00:00:00Z"),
        ]

    def list_vms(self):
        return list(self.vms)

    def create_vm(self, name: str) -> CloudVm:
        self.created.append(name)
        return CloudVm("3", name, "new", "2026-01-03T00:00:00Z")

    def delete_vm(self, vm_id: str) -> None:
        self.deleted.append(vm_id)


class AutoscalingTests(unittest.TestCase):
    def config(self, state_path: Path, *, enabled: bool = True):
        handle = tempfile.NamedTemporaryFile("w", delete=False)
        handle.write(CONFIG.format(state_path=state_path, enabled=str(enabled).lower()))
        handle.close()
        return load_config(Path(handle.name))

    def test_disabled_autoscaling_never_calls_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(Path(tmp) / "state.json", enabled=False)
            usage, decision = Autoscaler().check(
                config,
                FakeDocker({"uipath-robot-001": 0, "uipath-robot-002": 0}),
                FakeProvider(),
            )
            self.assertEqual(usage.active, 2)
            self.assertEqual(decision.action, "disabled")

    def test_dry_run_scale_up_when_all_containers_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(Path(tmp) / "state.json")
            provider = FakeProvider()
            usage, decision = Autoscaler().check(
                config,
                FakeDocker({"uipath-robot-001": 0, "uipath-robot-002": 0}),
                provider,
                apply=False,
            )
            self.assertEqual(usage.active_ratio, 1.0)
            self.assertEqual(decision.action, "scale_up")
            self.assertFalse(decision.applied)
            self.assertEqual(provider.created, [])

    def test_apply_scale_down_deletes_unprotected_idle_vm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            old_timestamp = time.time() - 120
            state_path.write_text(
                '{"uipath-robot-001": %s, "uipath-robot-002": %s}' % (old_timestamp, old_timestamp),
                encoding="utf-8",
            )
            config = self.config(state_path)
            provider = FakeProvider()
            usage, decision = Autoscaler().check(
                config,
                FakeDocker({"uipath-robot-001": 1, "uipath-robot-002": 1}),
                provider,
                apply=True,
            )
            self.assertEqual(usage.idle, 2)
            self.assertEqual(decision.action, "scale_down")
            self.assertEqual(decision.target_vm, "uipath-runtime-worker-002")
            self.assertEqual(provider.deleted, ["2"])


if __name__ == "__main__":
    unittest.main()
