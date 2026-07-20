from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from uipath_runtime.host import _install_first_available


class HostDependencyTests(unittest.TestCase):
    def test_installs_first_available_compose_package(self) -> None:
        calls: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[-1] == "docker-compose-plugin":
                return subprocess.CompletedProcess(cmd, 100)
            return subprocess.CompletedProcess(cmd, 0)

        with patch("uipath_runtime.host.subprocess.run", side_effect=fake_run):
            _install_first_available(("docker-compose-plugin", "docker-compose-v2"))

        self.assertEqual(calls[0][-1], "docker-compose-plugin")
        self.assertEqual(calls[1][-1], "docker-compose-v2")


if __name__ == "__main__":
    unittest.main()
