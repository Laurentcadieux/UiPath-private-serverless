from __future__ import annotations

import unittest
from pathlib import Path

from uipath_runtime.derived_image import DerivedImageManager
from uipath_runtime.models import CertificateMetadata


class DerivedImageTagTests(unittest.TestCase):
    def test_tag_is_deterministic(self) -> None:
        cert = CertificateMetadata(Path("/tmp/ca.crt"), "abc", "SHA256:AA")
        mgr = DerivedImageManager()
        tag1 = mgr.determine_image_tag("local/uipath-runtime", "repo/image:latest24.10", "sha256:base", cert)
        tag2 = mgr.determine_image_tag("local/uipath-runtime", "repo/image:latest24.10", "sha256:base", cert)
        self.assertEqual(tag1, tag2)
        self.assertTrue(tag1.startswith("local/uipath-runtime:latest24.10-ca-"))


if __name__ == "__main__":
    unittest.main()
