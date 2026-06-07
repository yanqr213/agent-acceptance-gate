import json
import os
from xml.sax.saxutils import escape


def render(result, fmt):
    name = (fmt or "markdown").lower()
    if name in ("md", "markdown"):
        return render_markdown(result)
    if name == "json":
        return render_json(result)
    if name == "junit":
        return render_junit(result)
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
    else:
        lines.extend(["## Findings", "", "No findings."])
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
            }
            for item in result.findings
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
    skipped = 0
    if not tests:
        tests = [None]
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<testsuite name="agent-acceptance-gate" tests="%s" failures="%s" skipped="%s">' % (
            len(tests),
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
    lines.append("</testsuite>")
    return "\n".join(lines) + "\n"
