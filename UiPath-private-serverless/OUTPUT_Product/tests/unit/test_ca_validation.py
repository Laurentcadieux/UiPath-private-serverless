from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uipath_runtime.exceptions import InvalidCertificateError
from uipath_runtime.tls import CertificateManager


class CertificateValidationTests(unittest.TestCase):
    def test_missing_ca_fails(self) -> None:
        with self.assertRaises(InvalidCertificateError):
            CertificateManager().validate_certificate(Path("/tmp/no-such-cert.pem"))

    def test_invalid_pem_fails(self) -> None:
        handle = tempfile.NamedTemporaryFile("w", delete=False)
        handle.write("not a cert")
        handle.close()
        with self.assertRaises(InvalidCertificateError):
            CertificateManager().validate_certificate(Path(handle.name))


if __name__ == "__main__":
    unittest.main()
