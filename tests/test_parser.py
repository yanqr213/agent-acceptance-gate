import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from agent_acceptance_gate.parser import parse_markdown_packet, parse_packet


class ParserTests(unittest.TestCase):
    def test_parse_json_packet(self):
        packet = parse_packet(json.dumps({
            "summary": "ship gate",
            "owner": "quality",
            "rollback_plan": "revert change",
            "risk_statement": "low",
            "changed_files": ["src/app.py"],
            "tests": [{"command": "python -m unittest", "status": "passed"}],
        }), "packet.json")
        self.assertEqual(packet.summary, "ship gate")
        self.assertEqual(packet.tests[0].command, "python -m unittest")

    def test_parse_yaml_lite_packet(self):
        packet = parse_packet("""
summary: ship gate
owner: quality
rollback_plan: revert change
risk_statement: low
changed_files:
  - src/app.py
tests:
  - command: python -m unittest
    status: passed
""", "packet.yml")
        self.assertEqual(packet.changed_files, ["src/app.py"])
        self.assertTrue(packet.tests[0].passed)

    def test_parse_markdown_packet(self):
        data = parse_markdown_packet("""
# Summary
Ship gate.
# Owner
quality
# Changed Files
- src/app.py
# Tests
- passed: python -m unittest
""")
        self.assertEqual(data["owner"], "quality")
        self.assertEqual(data["changed_files"], ["src/app.py"])
        self.assertEqual(data["tests"][0]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
