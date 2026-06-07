import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from agent_acceptance_gate.models import AcceptancePacket, TestResult
from agent_acceptance_gate.rules import evaluate


def valid_packet():
    return AcceptancePacket(
        summary="Change validator.",
        owner="quality",
        rollback_plan="Revert the validator change.",
        risk_statement="Low risk.",
        changed_files=["src/app.py"],
        tests=[TestResult(command="python -m unittest", status="passed")],
    )


class RuleTests(unittest.TestCase):
    def test_valid_packet_passes(self):
        result = evaluate(valid_packet())
        self.assertEqual(result.status, "pass")
        self.assertEqual(result.findings, [])

    def test_missing_tests_is_error(self):
        packet = valid_packet()
        packet.tests = []
        result = evaluate(packet)
        self.assertEqual(result.status, "fail")
        self.assertIn("tests-required", [item.rule_id for item in result.findings])

    def test_forbidden_path_is_error(self):
        packet = valid_packet()
        packet.changed_files = ["service/.env"]
        result = evaluate(packet)
        self.assertIn("forbidden-path", [item.rule_id for item in result.findings])

    def test_risk_path_is_warning(self):
        packet = valid_packet()
        packet.changed_files = ["service/auth/login.py"]
        result = evaluate(packet)
        self.assertIn("risk-path", [item.rule_id for item in result.findings])
        self.assertEqual(result.status, "pass")

    def test_api_change_requires_declared_impact(self):
        packet = valid_packet()
        packet.changed_files = ["service/api/users.py"]
        result = evaluate(packet)
        self.assertIn("impact-undisclosed", [item.rule_id for item in result.findings])

    def test_declared_impact_suppresses_warning(self):
        packet = valid_packet()
        packet.changed_files = ["service/api/users.py"]
        packet.declared_impacts = ["api"]
        result = evaluate(packet)
        self.assertNotIn("impact-undisclosed", [item.rule_id for item in result.findings])

    def test_missing_owner_and_rollback_plan_are_errors(self):
        packet = valid_packet()
        packet.owner = ""
        packet.rollback_plan = ""
        result = evaluate(packet)
        ids = [item.rule_id for item in result.findings]
        self.assertIn("owner-required", ids)
        self.assertIn("rollback-required", ids)

    def test_secret_is_error(self):
        packet = valid_packet()
        packet.diff_summary = "token='abcd1234abcd1234abcd1234'"
        result = evaluate(packet)
        self.assertIn("secret-detected", [item.rule_id for item in result.findings])


if __name__ == "__main__":
    unittest.main()
