from __future__ import annotations

import unittest

from uipath_runtime.naming import container_name, instance_id


class NamingTests(unittest.TestCase):
    def test_instance_id_is_three_digits(self) -> None:
        self.assertEqual(instance_id(1), "001")
        self.assertEqual(instance_id(10), "010")

    def test_container_name_is_deterministic(self) -> None:
        self.assertEqual(container_name("uipath-robot", 10), "uipath-robot-010")

    def test_zero_instance_rejected(self) -> None:
        with self.assertRaises(ValueError):
            instance_id(0)


if __name__ == "__main__":
    unittest.main()
