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


if __name__ == "__main__":
    unittest.main()
