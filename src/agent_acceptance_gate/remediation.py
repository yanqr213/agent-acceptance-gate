import json
from dataclasses import asdict, dataclass

from .baseline import attach_fingerprints


@dataclass
class RemediationTask:
    task_id: str
    priority: str
    severity: str
    rule_id: str
    title: str
    path: str
    owner_hint: str
    summary: str
    recommended_action: str
    acceptance_criteria: list
    agent_prompt: str
    fingerprint: str


PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def build_remediation_plan(result):
    attach_fingerprints(result)
    tasks = [_task_for_finding(result, finding) for finding in result.findings]
    return sorted(
        tasks,
        key=lambda item: (
            PRIORITY_ORDER.get(item.priority, 9),
            item.rule_id,
            item.path,
            item.fingerprint,
        ),
    )


def render_remediation_json(result):
    tasks = build_remediation_plan(result)
    payload = {
        "status": result.status,
        "summary": {
            "task_count": len(tasks),
            "errors": result.error_count,
            "warnings": result.warning_count,
            "suppressed": len(result.suppressed_findings),
            "priorities": _priority_counts(tasks),
        },
        "tasks": [asdict(task) for task in tasks],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_remediation_markdown(result):
    tasks = build_remediation_plan(result)
    lines = [
        "# Agent Acceptance Remediation Plan",
        "",
        "- Status: `%s`" % result.status,
        "- Tasks: `%s`" % len(tasks),
        "- Errors: `%s`" % result.error_count,
        "- Warnings: `%s`" % result.warning_count,
        "- Suppressed by baseline: `%s`" % len(result.suppressed_findings),
        "",
    ]
    if not tasks:
        lines.extend([
            "## Tasks",
            "",
            "No remediation tasks. The current acceptance findings are clear after baseline filtering.",
            "",
        ])
        return "\n".join(lines)
    for task in tasks:
        location = task.path or "acceptance-packet"
        lines.extend([
            "## %s: %s" % (task.task_id, task.title),
            "",
            "- Priority: `%s`" % task.priority,
            "- Severity: `%s`" % task.severity,
            "- Rule: `%s`" % task.rule_id,
            "- Owner hint: `%s`" % task.owner_hint,
            "- Path: `%s`" % location,
            "- Fingerprint: `%s`" % task.fingerprint,
            "",
            "### Summary",
            "",
            task.summary,
            "",
            "### Recommended Action",
            "",
            task.recommended_action,
            "",
            "### Acceptance Criteria",
            "",
        ])
        for criterion in task.acceptance_criteria:
            lines.append("- %s" % criterion)
        lines.extend([
            "",
            "### Agent Prompt",
            "",
            "```text",
            task.agent_prompt,
            "```",
            "",
        ])
    return "\n".join(lines)


def _task_for_finding(result, finding):
    priority = _priority(finding)
    owner_hint = _owner_hint(finding)
    action = _recommended_action(finding)
    criteria = _acceptance_criteria(finding)
    task_id = "AAG-%s-%s" % (priority, (finding.fingerprint or "pending")[:8])
    summary = "%s: %s" % (finding.title, finding.message)
    return RemediationTask(
        task_id=task_id,
        priority=priority,
        severity=finding.severity,
        rule_id=finding.rule_id,
        title=finding.title,
        path=finding.path or "",
        owner_hint=owner_hint,
        summary=summary,
        recommended_action=action,
        acceptance_criteria=criteria,
        agent_prompt=_agent_prompt(result, finding, priority, owner_hint, action, criteria),
        fingerprint=finding.fingerprint,
    )


def _priority(finding):
    if finding.rule_id in ("secret-detected", "forbidden-path"):
        return "P0"
    if finding.rule_id in ("tests-required", "tests-not-passing", "required-field", "owner-required", "rollback-required"):
        return "P1"
    if finding.severity == "error":
        return "P1"
    if finding.rule_id in ("risk-path", "impact-undisclosed", "pii-detected"):
        return "P2"
    if finding.severity == "warning":
        return "P2"
    return "P3"


def _owner_hint(finding):
    if finding.rule_id in ("secret-detected", "pii-detected", "forbidden-path"):
        return "security-or-release-owner"
    if finding.rule_id in ("tests-required", "tests-not-passing"):
        return "test-owner"
    if finding.rule_id in ("owner-required", "rollback-required", "required-field"):
        return "delivery-owner"
    if finding.rule_id in ("risk-path", "impact-undisclosed"):
        return "domain-reviewer"
    return "delivery-owner"


def _recommended_action(finding):
    rule_id = finding.rule_id
    if rule_id == "secret-detected":
        return "Remove the secret-like value from the acceptance packet, rotate the real credential if it was exposed, and replace the packet text with a redacted placeholder."
    if rule_id == "pii-detected":
        return "Remove or redact personal data from the acceptance packet, then reference an internal ticket or role alias instead of raw contact details."
    if rule_id == "forbidden-path":
        return "Remove the forbidden file from the delivery or move the change into an approved, reviewable location before rerunning the gate."
    if rule_id in ("tests-required", "tests-not-passing"):
        return "Run a meaningful test command, make it pass, and record the command plus passing status in the acceptance packet."
    if rule_id == "owner-required":
        return "Set the accountable owner in the acceptance packet so follow-up and rollback decisions have a clear responsible party."
    if rule_id == "rollback-required":
        return "Add a concrete rollback plan that names the revert, disable, or recovery action and any validation needed after rollback."
    if rule_id == "required-field":
        return "Fill the missing required acceptance-packet field with specific delivery evidence rather than a placeholder."
    if rule_id == "risk-path":
        return "Add explicit review notes, targeted tests, or risk mitigation for the high-risk path, then keep the finding visible or baseline it only after review."
    if rule_id == "impact-undisclosed":
        return "Add the inferred impact to declared_impacts or explain why the file change does not affect that surface."
    return "Update the delivery or acceptance packet so this finding no longer appears when the gate is rerun."


def _acceptance_criteria(finding):
    criteria = [
        "Rerunning agent-acceptance-gate no longer reports this finding as a new active task.",
        "The acceptance packet records the remediation evidence in a field reviewers can audit.",
    ]
    if finding.path:
        criteria.append("The path `%s` is reviewed, removed, or covered by targeted validation." % finding.path)
    if finding.rule_id in ("secret-detected", "pii-detected"):
        criteria.append("No raw sensitive value remains in the acceptance packet or generated reports.")
    if finding.rule_id in ("tests-required", "tests-not-passing"):
        criteria.append("At least one relevant test command is recorded with a passing status.")
    return criteria


def _agent_prompt(result, finding, priority, owner_hint, action, criteria):
    location = finding.path or "acceptance-packet"
    lines = [
        "You are repairing an agent-acceptance-gate finding.",
        "Current gate status: %s (%s errors, %s warnings)." % (result.status, result.error_count, result.warning_count),
        "Priority: %s." % priority,
        "Owner hint: %s." % owner_hint,
        "Finding: [%s] %s (%s) at %s." % (finding.severity.upper(), finding.title, finding.rule_id, location),
        "Message: %s" % finding.message,
        "Recommended action: %s" % action,
        "Acceptance criteria:",
    ]
    lines.extend("- %s" % item for item in criteria)
    lines.append("After the fix, rerun the exact gate command and include the result in the delivery notes.")
    return "\n".join(lines)


def _priority_counts(tasks):
    counts = {key: 0 for key in ("P0", "P1", "P2", "P3")}
    for task in tasks:
        counts[task.priority] = counts.get(task.priority, 0) + 1
    return counts
