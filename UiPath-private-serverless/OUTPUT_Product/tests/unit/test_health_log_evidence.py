from __future__ import annotations

import unittest

from uipath_runtime.docker_manager import _has_connection_evidence


class HealthLogEvidenceTests(unittest.TestCase):
    def test_detects_successful_orchestrator_connection(self) -> None:
        self.assertTrue(_has_connection_evidence("Successfully connected to Orchestrator"))

    def test_detects_successful_heartbeat(self) -> None:
        self.assertTrue(_has_connection_evidence("RequestUri:/api/robotsservice/HeartbeatV2 Status:OK"))

    def test_does_not_guess_connected_without_evidence(self) -> None:
        self.assertFalse(_has_connection_evidence("Application started. Hosting started."))


if __name__ == "__main__":
    unittest.main()
