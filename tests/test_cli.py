import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write_packet(self, payload):
        path = os.path.join(self.tmp, "packet.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        return path

    def run_cli(self, args):
        env = os.environ.copy()
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
        env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [sys.executable, "-m", "agent_acceptance_gate"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

    def test_version(self):
        result = self.run_cli(["--version"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("agent-acceptance-gate 0.3.0", result.stdout)

    def test_check_error_exit_code_passes_without_errors(self):
        packet = self.write_packet({
            "summary": "Change",
            "owner": "quality",
            "rollback_plan": "revert",
            "risk_statement": "low",
            "changed_files": ["src/app.py"],
            "tests": [{"command": "python -m unittest", "status": "passed"}],
        })
        result = self.run_cli(["--packet", packet, "--check", "error"])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_check_warning_fails_on_warning(self):
        packet = self.write_packet({
            "summary": "Change",
            "owner": "quality",
            "rollback_plan": "revert",
            "risk_statement": "low",
            "changed_files": ["service/auth/login.py"],
            "tests": [{"command": "python -m unittest", "status": "passed"}],
        })
        result = self.run_cli(["--packet", packet, "--check", "warning"])
        self.assertEqual(result.returncode, 1)

    def test_baseline_suppresses_known_warning_for_check(self):
        packet = self.write_packet({
            "summary": "Change",
            "owner": "quality",
            "rollback_plan": "revert",
            "risk_statement": "low",
            "changed_files": ["service/auth/login.py"],
            "tests": [{"command": "python -m unittest", "status": "passed"}],
        })
        baseline = os.path.join(self.tmp, "baseline.json")
        output = os.path.join(self.tmp, "report.json")
        write_result = self.run_cli(["--packet", packet, "--write-baseline", baseline])
        self.assertEqual(write_result.returncode, 0, write_result.stderr)
        result = self.run_cli(["--packet", packet, "--baseline", baseline, "--check", "warning", "--format", "json", "--output", output])
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(output, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual([], payload["findings"])
        self.assertEqual(1, payload["summary"]["suppressed"])

    def test_output_parent_directory_is_created(self):
        packet = self.write_packet({
            "summary": "Change",
            "owner": "quality",
            "rollback_plan": "revert",
            "risk_statement": "low",
            "changed_files": ["src/app.py"],
            "tests": [{"command": "python -m unittest", "status": "passed"}],
        })
        output = os.path.join(self.tmp, "nested", "report.json")
        result = self.run_cli(["--packet", packet, "--format", "json", "--output", output])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.exists(output))

    def test_sarif_output_file(self):
        packet = self.write_packet({
            "summary": "Change",
            "owner": "quality",
            "rollback_plan": "revert",
            "risk_statement": "low",
            "changed_files": ["service\\auth\\login.py"],
            "tests": [{"command": "python -m unittest", "status": "passed"}],
        })
        output = os.path.join(self.tmp, "reports", "gate.sarif")
        result = self.run_cli(["--packet", packet, "--format", "sarif", "--output", output])
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(output, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        uri = payload["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        self.assertEqual(uri, "service/auth/login.py")


if __name__ == "__main__":
    unittest.main()
