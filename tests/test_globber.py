import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from agent_acceptance_gate.globber import matches_glob, normalize_path


class GlobberTests(unittest.TestCase):
    def test_normalize_windows_path(self):
        self.assertEqual(normalize_path("src\\app.py"), "src/app.py")

    def test_double_star_prefix_matches_root(self):
        self.assertTrue(matches_glob(".env", "**/.env"))

    def test_double_star_prefix_matches_nested(self):
        self.assertTrue(matches_glob("service/.env", "**/.env"))


if __name__ == "__main__":
    unittest.main()
