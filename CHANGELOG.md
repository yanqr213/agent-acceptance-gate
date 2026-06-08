# Changelog

## 0.3.0 - 2026-06-08

- Added reviewed baseline JSON output for accepted gate findings.
- Added `--baseline` filtering and `--write-baseline` support.
- Added stable finding fingerprints and suppressed-finding metadata to Markdown, JSON, JUnit, and SARIF reports.
- Added CI smoke coverage for baseline generation and filtered checks.

## 0.2.0 - 2026-06-08

- Added SARIF 2.1.0 report output for GitHub Code Scanning and security dashboards.
- Added `--version` CLI support.
- Added package URL metadata.
- Added tests for SARIF output and path normalization.
- Expanded Chinese and English README documentation for SARIF workflows.

## 0.1.0 - 2026-06-08

- Initial local release.
- Added JSON, YAML-lite, and Markdown acceptance packet parsing.
- Added rules for required tests, required fields, risky paths, forbidden paths, impact disclosure, owner, rollback plan, secret scanning, and PII scanning.
- Added Markdown, JSON, and JUnit report rendering.
- Added CLI `--check warning|error` support for CI gating.
