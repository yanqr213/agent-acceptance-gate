import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from agent_acceptance_gate.baseline import apply_baseline, load_baseline, render_baseline
from agent_acceptance_gate.models import AcceptancePacket, Finding, GateResult


class BaselineTests(unittest.TestCase):
    def result(self):
        packet = AcceptancePacket(summary="Change", changed_files=["service/auth/login.py"])
        return GateResult(
            status="pass",
            packet=packet,
            findings=[Finding("risk-path", "warning", "High-risk path changed", "Changed file matches a high-risk path rule.", "service/auth/login.py")],
        )

    def test_render_baseline_contains_fingerprint(self):
        data = json.loads(render_baseline(self.result()))
        self.assertEqual(1, data["schema_version"])
        self.assertEqual("risk-path", data["findings"][0]["rule_id"])
        self.assertTrue(data["findings"][0]["fingerprint"])

    def test_apply_baseline_suppresses_known_findings(self):
        result = self.result()
        data = json.loads(render_baseline(result))
        filtered = apply_baseline(result, {item["fingerprint"] for item in data["findings"]})
        self.assertEqual([], filtered.findings)
        self.assertEqual(1, len(filtered.suppressed_findings))
        self.assertEqual("pass", filtered.status)
        self.assertEqual(0, filtered.warning_count)

    def test_load_baseline_accepts_object_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "baseline.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(render_baseline(self.result()))
            self.assertEqual(1, len(load_baseline(path)))


if __name__ == "__main__":
    unittest.main()
