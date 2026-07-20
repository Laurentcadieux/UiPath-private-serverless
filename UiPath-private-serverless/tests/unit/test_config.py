from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uipath_runtime.config import load_config
from uipath_runtime.exceptions import InvalidConfigurationError


VALID_CONFIG = """
version: 1
orchestrator:
  url: "https://orchestrator.example.com"
  authentication:
    type: "machine_key"
    machine_key_env: "UIPATH_MACHINE_KEY"
runtime:
  count: 10
  container_prefix: "uipath-robot"
  image: "uipathprod.azurecr.io/robot/uiautomation-runtime:latest24.10"
docker:
  network_name: "uipath-runtime-network"
  dns: ["8.8.8.8", "1.1.1.1"]
"""


class ConfigTests(unittest.TestCase):
    def write_config(self, text: str) -> Path:
        handle = tempfile.NamedTemporaryFile("w", delete=False)
        handle.write(text)
        handle.close()
        return Path(handle.name)

    def test_valid_config_parses(self) -> None:
        config = load_config(self.write_config(VALID_CONFIG))
        self.assertEqual(config.runtime.count, 10)
        self.assertEqual(config.orchestrator.url, "https://orchestrator.example.com")

    def test_count_override(self) -> None:
        config = load_config(self.write_config(VALID_CONFIG), count_override=3)
        self.assertEqual(config.runtime.count, 3)

    def test_missing_required_field_fails(self) -> None:
        bad = VALID_CONFIG.replace('  url: "https://orchestrator.example.com"\n', "")
        with self.assertRaises(InvalidConfigurationError):
            load_config(self.write_config(bad))

    def test_http_url_fails(self) -> None:
        bad = VALID_CONFIG.replace("https://orchestrator.example.com", "http://orchestrator.example.com")
        with self.assertRaises(InvalidConfigurationError):
            load_config(self.write_config(bad))

    def test_invalid_count_fails(self) -> None:
        bad = VALID_CONFIG.replace("count: 10", "count: 0")
        with self.assertRaises(InvalidConfigurationError):
            load_config(self.write_config(bad))

    def test_latest_tag_fails(self) -> None:
        bad = VALID_CONFIG.replace("latest24.10", "latest")
        with self.assertRaises(InvalidConfigurationError):
            load_config(self.write_config(bad))

    def test_invalid_dns_fails(self) -> None:
        bad = VALID_CONFIG.replace('"8.8.8.8"', '"not-dns"')
        with self.assertRaises(InvalidConfigurationError):
            load_config(self.write_config(bad))

    def test_unknown_field_fails(self) -> None:
        bad = VALID_CONFIG + "\nunknown: true\n"
        with self.assertRaises(InvalidConfigurationError):
            load_config(self.write_config(bad))

    def test_scaling_config_parses(self) -> None:
        text = VALID_CONFIG + """
scaling:
  minimum_count: 2
  burst_max_count: 12
  idle_minutes_before_stop: 45
  poll_interval_seconds: 90
  active_job_probe:
    command: ["/bin/sh", "-lc", "true"]
"""
        config = load_config(self.write_config(text))
        self.assertEqual(config.scaling.minimum_count, 2)
        self.assertEqual(config.scaling.burst_max_count, 12)
        self.assertEqual(config.scaling.idle_minutes_before_stop, 45)
        self.assertEqual(config.scaling.active_job_probe.command, ("/bin/sh", "-lc", "true"))

    def test_runtime_count_cannot_exceed_burst_max(self) -> None:
        text = VALID_CONFIG + """
scaling:
  minimum_count: 1
  burst_max_count: 3
"""
        with self.assertRaises(InvalidConfigurationError):
            load_config(self.write_config(text))


if __name__ == "__main__":
    unittest.main()
