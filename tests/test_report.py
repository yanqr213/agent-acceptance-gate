import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from agent_acceptance_gate.models import AcceptancePacket, Finding, GateResult, TestResult
from agent_acceptance_gate.report import render_json, render_junit, render_markdown


class ReportTests(unittest.TestCase):
    def result(self):
        packet = AcceptancePacket(
            summary="Change",
            changed_files=["src/app.py"],
            tests=[TestResult(command="python -m unittest", status="passed")],
        )
        return GateResult(
            status="fail",
            packet=packet,
            findings=[Finding("tests-required", "error", "No tests", "Tests are required.")],
        )

    def test_markdown_contains_findings(self):
        text = render_markdown(self.result())
        self.assertIn("# Agent Acceptance Gate Report", text)
        self.assertIn("tests-required", text)

    def test_json_is_machine_readable(self):
        payload = json.loads(render_json(self.result()))
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["findings"][0]["severity"], "error")

    def test_junit_contains_failure(self):
        text = render_junit(self.result())
        self.assertIn("<testsuite", text)
        self.assertIn("<failure", text)


if __name__ == "__main__":
    unittest.main()
