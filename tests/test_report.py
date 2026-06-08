import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from agent_acceptance_gate.models import AcceptancePacket, Finding, GateResult, TestResult
from agent_acceptance_gate.baseline import apply_baseline, render_baseline
from agent_acceptance_gate.report import render, render_json, render_junit, render_markdown, render_sarif


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
        self.assertIn("Fingerprint", text)

    def test_json_is_machine_readable(self):
        payload = json.loads(render_json(self.result()))
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["findings"][0]["severity"], "error")
        self.assertIn("fingerprint", payload["findings"][0])

    def test_junit_contains_failure(self):
        text = render_junit(self.result())
        self.assertIn("<testsuite", text)
        self.assertIn("<failure", text)

    def test_sarif_contains_findings(self):
        payload = json.loads(render_sarif(self.result()))
        self.assertEqual(payload["version"], "2.1.0")
        run = payload["runs"][0]
        self.assertEqual(run["tool"]["driver"]["name"], "agent-acceptance-gate")
        self.assertEqual(run["tool"]["driver"]["semanticVersion"], "0.4.0")
        self.assertEqual(run["results"][0]["ruleId"], "tests-required")
        self.assertEqual(run["results"][0]["level"], "error")
        self.assertIn("agentAcceptanceGate/v1", run["results"][0]["partialFingerprints"])

    def test_remediation_markdown_contains_agent_prompt(self):
        text = render(self.result(), "remediation")
        self.assertIn("# Agent Acceptance Remediation Plan", text)
        self.assertIn("Priority: `P1`", text)
        self.assertIn("Owner hint: `test-owner`", text)
        self.assertIn("```text", text)
        self.assertIn("After the fix, rerun the exact gate command", text)

    def test_remediation_json_is_machine_readable(self):
        payload = json.loads(render(self.result(), "remediation-json"))
        self.assertEqual(payload["summary"]["task_count"], 1)
        self.assertEqual(payload["summary"]["priorities"]["P1"], 1)
        task = payload["tasks"][0]
        self.assertEqual(task["rule_id"], "tests-required")
        self.assertEqual(task["priority"], "P1")
        self.assertEqual(task["owner_hint"], "test-owner")
        self.assertIn("agent_prompt", task)

    def test_remediation_ignores_suppressed_findings(self):
        result = self.result()
        baseline = json.loads(render_baseline(result))
        filtered = apply_baseline(result, {item["fingerprint"] for item in baseline["findings"]})

        payload = json.loads(render(filtered, "remediation-json"))
        self.assertEqual(payload["summary"]["task_count"], 0)
        self.assertEqual(payload["summary"]["suppressed"], 1)

    def test_reports_include_suppressed_findings(self):
        result = self.result()
        baseline = json.loads(render_baseline(result))
        filtered = apply_baseline(result, {item["fingerprint"] for item in baseline["findings"]})

        self.assertIn("Suppressed By Baseline", render_markdown(filtered))
        self.assertEqual(1, json.loads(render_json(filtered))["summary"]["suppressed"])
        junit = render_junit(filtered)
        self.assertIn("tests=\"1\"", junit)
        self.assertIn("skipped=\"1\"", junit)
        sarif = json.loads(render_sarif(filtered))
        self.assertEqual(1, sarif["runs"][0]["properties"]["suppressed"])


if __name__ == "__main__":
    unittest.main()
