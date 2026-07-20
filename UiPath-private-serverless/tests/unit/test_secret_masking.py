from __future__ import annotations

import unittest

from uipath_runtime.models import mask_secret


class SecretMaskingTests(unittest.TestCase):
    def test_masks_machine_key(self) -> None:
        self.assertEqual(mask_secret("abc1237A92"), "****7A92")

    def test_short_secret_is_fully_masked(self) -> None:
        self.assertEqual(mask_secret("abc"), "****")


if __name__ == "__main__":
    unittest.main()
