from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from test_drift_detection import spec
from uipath_runtime.reconciliation import Reconciler


class FakeDocker:
    def __init__(self):
        self.actions = []

    def list_managed_containers(self):
        return []

    def ensure_container(self, container_spec, *, recreate: bool):
        self.actions.append(container_spec.name)
        from uipath_runtime.models import ContainerStatus, HealthState

        return "created", ContainerStatus(container_spec.name, "running", HealthState.RUNNING_NOT_CONFIRMED, container_spec.image)


class ReconciliationTests(unittest.TestCase):
    def test_reconcile_creates_exact_specs(self) -> None:
        fake = FakeDocker()
        with tempfile.TemporaryDirectory() as tmp:
            specs = [spec(log_path=Path(tmp) / "one"), spec(log_path=Path(tmp) / "two")]
            report = Reconciler().reconcile(fake, specs, recreate=False)
            self.assertEqual(report.created, 2)
            self.assertEqual(len(fake.actions), 2)


if __name__ == "__main__":
    unittest.main()
