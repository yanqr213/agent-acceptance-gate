import json
import os
from xml.sax.saxutils import escape

from . import __version__
from .remediation import render_remediation_json, render_remediation_markdown


def render(result, fmt):
    name = (fmt or "markdown").lower()
    if name in ("md", "markdown"):
        return render_markdown(result)
    if name == "json":
        return render_json(result)
    if name == "junit":
        return render_junit(result)
    if name == "sarif":
        return render_sarif(result)
    if name in ("remediation", "remediation-md"):
        return render_remediation_markdown(result)
    if name in ("remediation-json", "fix-json"):
        return render_remediation_json(result)
    raise ValueError("Unsupported report format: %s" % fmt)


def write_report(result, fmt, output_path):
    content = render(result, fmt)
    if output_path:
        parent = os.path.dirname(os.path.abspath(output_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(content)
    return content


def render_markdown(result):
    lines = [
        "# Agent Acceptance Gate Report",
        "",
        "- Status: `%s`" % result.status,
        "- Errors: `%s`" % result.error_count,
        "- Warnings: `%s`" % result.warning_count,
        "- Suppressed by baseline: `%s`" % len(result.suppressed_findings),
        "- Changed files: `%s`" % len(result.packet.changed_files),
        "- Tests: `%s`" % len(result.packet.tests),
        "",
    ]
    if result.findings:
        lines.extend(["## Findings", ""])
        for finding in result.findings:
            location = " (%s)" % finding.path if finding.path else ""
            lines.append("- **[%s] %s** `%s`%s - %s" % (
                finding.severity.upper(),
                finding.title,
                finding.rule_id,
                location,
                finding.message,
            ))
            lines.append("  - Fingerprint: `%s`" % finding.fingerprint)
    else:
        lines.extend(["## Findings", "", "No findings."])
    if result.suppressed_findings:
        lines.extend(["", "## Suppressed By Baseline", ""])
        for finding in result.suppressed_findings:
            location = " (%s)" % finding.path if finding.path else ""
            lines.append("- **[%s] %s** `%s`%s - `%s`" % (
                finding.severity.upper(),
                finding.title,
                finding.rule_id,
                location,
                finding.fingerprint,
            ))
    lines.extend(["", "## Tests", ""])
    if result.packet.tests:
        for test in result.packet.tests:
            lines.append("- `%s` - `%s`" % (test.command, test.status or "unknown"))
    else:
        lines.append("No tests were reported.")
    lines.extend(["", "## Changed Files", ""])
    if result.packet.changed_files:
        for path in result.packet.changed_files:
            lines.append("- `%s`" % path)
    else:
        lines.append("No changed files were reported.")
    lines.append("")
    return "\n".join(lines)


def render_json(result):
    payload = {
        "status": result.status,
        "summary": {
            "errors": result.error_count,
            "warnings": result.warning_count,
            "suppressed": len(result.suppressed_findings),
            "changed_files": len(result.packet.changed_files),
            "tests": len(result.packet.tests),
        },
        "findings": [
            {
                "rule_id": item.rule_id,
                "severity": item.severity,
                "title": item.title,
                "message": item.message,
                "path": item.path,
                "fingerprint": item.fingerprint,
            }
            for item in result.findings
        ],
        "suppressed_findings": [
            {
                "rule_id": item.rule_id,
                "severity": item.severity,
                "title": item.title,
                "message": item.message,
                "path": item.path,
                "fingerprint": item.fingerprint,
            }
            for item in result.suppressed_findings
        ],
        "tests": [
            {
                "command": test.command,
                "status": test.status,
            }
            for test in result.packet.tests
        ],
        "changed_files": result.packet.changed_files,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_junit(result):
    tests = result.findings or []
    failures = len([item for item in tests if item.severity == "error"])
    skipped = len(result.suppressed_findings)
    if not tests and not result.suppressed_findings:
        tests = [None]
    test_count = len(tests) + skipped
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<testsuite name="agent-acceptance-gate" tests="%s" failures="%s" skipped="%s">' % (
            test_count,
            failures,
            skipped,
        ),
    ]
    for item in tests:
        if item is None:
            lines.append('  <testcase classname="agent_acceptance_gate" name="gate.pass" />')
            continue
        case_name = escape(item.rule_id)
        lines.append('  <testcase classname="agent_acceptance_gate" name="%s">' % case_name)
        if item.severity == "error":
            lines.append('    <failure message="%s">%s</failure>' % (
                escape(item.title),
                escape(item.message),
            ))
        elif item.severity == "warning":
            lines.append('    <system-out>%s</system-out>' % escape(item.message))
        lines.append("  </testcase>")
    for item in result.suppressed_findings:
        case_name = escape("suppressed:%s" % item.rule_id)
        lines.append('  <testcase classname="agent_acceptance_gate" name="%s">' % case_name)
        lines.append('    <skipped message="suppressed by baseline">%s</skipped>' % escape(item.fingerprint))
        lines.append("  </testcase>")
    lines.append("</testsuite>")
    return "\n".join(lines) + "\n"


def render_sarif(result):
    rules = {}
    sarif_results = []
    for finding in result.findings:
        rules.setdefault(
            finding.rule_id,
            {
                "id": finding.rule_id,
                "name": finding.title,
                "shortDescription": {"text": finding.title},
                "fullDescription": {"text": finding.message},
                "defaultConfiguration": {"level": sarif_level(finding.severity)},
            },
        )
        location = {
            "physicalLocation": {
                "artifactLocation": {"uri": normalize_uri(finding.path) if finding.path else "acceptance-packet"},
                "region": {"startLine": 1},
            }
        }
        sarif_results.append(
            {
                "ruleId": finding.rule_id,
                "level": sarif_level(finding.severity),
                "message": {"text": finding.message},
                "partialFingerprints": {"agentAcceptanceGate/v1": finding.fingerprint},
                "locations": [location],
                "properties": {
                    "severity": finding.severity,
                    "title": finding.title,
                    "path": finding.path,
                },
            }
        )
    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "agent-acceptance-gate",
                        "semanticVersion": __version__,
                        "informationUri": "https://github.com/yanqr213/agent-acceptance-gate",
                        "rules": list(rules.values()),
                    }
                },
                "automationDetails": {"id": "agent-acceptance-gate"},
                "results": sarif_results,
                "properties": {
                    "status": result.status,
                    "errors": result.error_count,
                    "warnings": result.warning_count,
                    "suppressed": len(result.suppressed_findings),
                    "suppressed_findings": [
                        {
                            "rule_id": item.rule_id,
                            "severity": item.severity,
                            "title": item.title,
                            "path": item.path,
                            "fingerprint": item.fingerprint,
                        }
                        for item in result.suppressed_findings
                    ],
                    "changed_files": len(result.packet.changed_files),
                    "tests": len(result.packet.tests),
                },
            }
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def sarif_level(severity):
    if severity == "error":
        return "error"
    if severity == "warning":
        return "warning"
    return "note"


def normalize_uri(path):
    return str(path).replace("\\", "/")
