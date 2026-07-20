from __future__ import annotations

import unittest

from uipath_runtime.exceptions import ExitCode


class ExitCodeTests(unittest.TestCase):
    def test_exit_code_mapping(self) -> None:
        self.assertEqual(int(ExitCode.SUCCESS), 0)
        self.assertEqual(int(ExitCode.IMAGE_NOT_FOUND), 5)
        self.assertEqual(int(ExitCode.CONFIGURATION_DRIFT), 14)


if __name__ == "__main__":
    unittest.main()
