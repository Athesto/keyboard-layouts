"""Check tag conversion and rejection before any installer build."""
import unittest
from build_windows import version_number

class VersionTests(unittest.TestCase):
    def test_candidate_and_stable_share_msi_version(self):
        self.assertEqual(version_number("v1.2.3-rc.1"), "1.2.3")
        self.assertEqual(version_number("v1.2.3"), "1.2.3")
        self.assertEqual(version_number("255.255.65535"), "255.255.65535")

    def test_reject_invalid_or_unrepresentable_versions(self):
        for value in ("v1", "v1.2.3;exit", "v01.2.3", "v256.0.0", "v0.256.0", "v0.0.65536", "v1.2.3/rc"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                version_number(value)

if __name__ == "__main__":
    unittest.main()
