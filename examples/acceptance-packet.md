# Summary

Add stricter validation to the local acceptance gate CLI.

# Owner

platform-quality

# Rollback Plan

Revert the CLI validation commit and rerun the previous release package.

# Risk Statement

Low operational risk. The change is local-only and does not modify production services.

# Changed Files

- src/agent_acceptance_gate/cli.py
- src/agent_acceptance_gate/rules.py
- tests/test_rules.py

# Declared Impacts

# Tests

- passed: python -m unittest discover -s tests

# Diff Summary

CLI validates packets, evaluates rules, and renders reports.
