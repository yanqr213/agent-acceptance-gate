import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from agent_acceptance_gate.scanner import scan_text


class ScannerTests(unittest.TestCase):
    def test_detects_secret_assignment(self):
        findings = scan_text("api_key = 'abcd1234abcd1234abcd1234'")
        self.assertEqual(findings[0]["kind"], "secret")

    def test_detects_pii_email(self):
        findings = scan_text("Contact release-owner@company.invalid for review.")
        self.assertEqual(findings[0]["kind"], "pii")

    def test_can_disable_pii(self):
        findings = scan_text("Contact release-owner@company.invalid for review.", include_pii=False)
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
