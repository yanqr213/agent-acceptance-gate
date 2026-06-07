from copy import deepcopy

from .globber import any_match
from .models import DEFAULT_RULES, Finding, GateResult
from .scanner import packet_scan_text, scan_text


IMPACT_ALIASES = {
    "api": "public_api",
    "public-api": "public_api",
    "public_api": "public_api",
    "db": "database",
    "database": "database",
    "schema": "schema",
    "config": "config",
    "configuration": "config",
}


def merge_rules(custom):
    rules = deepcopy(DEFAULT_RULES)
    for key, value in (custom or {}).items():
        if isinstance(value, dict) and isinstance(rules.get(key), dict):
            merged = deepcopy(rules[key])
            merged.update(value)
            rules[key] = merged
        else:
            rules[key] = value
    return rules


def evaluate(packet, custom_rules=None):
    rules = merge_rules(custom_rules)
    findings = []
    _check_required_fields(packet, rules, findings)
    _check_tests(packet, rules, findings)
    _check_paths(packet, rules, findings)
    _check_impacts(packet, rules, findings)
    _check_sensitive_data(packet, rules, findings)
    status = "fail" if any(item.severity == "error" for item in findings) else "pass"
    return GateResult(status=status, findings=findings, packet=packet)


def _check_required_fields(packet, rules, findings):
    field_map = {
        "summary": packet.summary,
        "risk_statement": packet.risk_statement,
        "risk": packet.risk_statement,
        "owner": packet.owner,
        "rollback_plan": packet.rollback_plan,
        "rollback": packet.rollback_plan,
    }
    for field in rules.get("required_fields") or []:
        if not str(field_map.get(field, "")).strip():
            findings.append(Finding(
                rule_id="required-field",
                severity="error",
                title="Missing required field",
                message="Acceptance packet is missing required field '%s'." % field,
            ))
    if rules.get("require_owner") and not packet.owner.strip():
        findings.append(Finding(
            rule_id="owner-required",
            severity="error",
            title="Missing owner",
            message="Acceptance packet must name the accountable owner.",
        ))
    if rules.get("require_rollback_plan") and not packet.rollback_plan.strip():
        findings.append(Finding(
            rule_id="rollback-required",
            severity="error",
            title="Missing rollback plan",
            message="Acceptance packet must include a rollback plan.",
        ))


def _check_tests(packet, rules, findings):
    if not rules.get("required_tests"):
        return
    if not packet.tests:
        findings.append(Finding(
            rule_id="tests-required",
            severity="error",
            title="No tests reported",
            message="At least one test command result is required.",
        ))
        return
    passing = [test for test in packet.tests if test.passed]
    if not passing:
        findings.append(Finding(
            rule_id="tests-not-passing",
            severity="error",
            title="No passing tests reported",
            message="At least one test command must have a passing status.",
        ))


def _check_paths(packet, rules, findings):
    for path in packet.changed_files:
        if any_match(path, rules.get("forbidden_paths") or []):
            findings.append(Finding(
                rule_id="forbidden-path",
                severity="error",
                title="Forbidden path changed",
                message="Changed file matches a forbidden path rule.",
                path=path,
            ))
        if any_match(path, rules.get("risk_path_globs") or []):
            findings.append(Finding(
                rule_id="risk-path",
                severity="warning",
                title="High-risk path changed",
                message="Changed file matches a high-risk path rule.",
                path=path,
            ))


def _check_impacts(packet, rules, findings):
    declared = set()
    for item in packet.declared_impacts:
        key = IMPACT_ALIASES.get(item.strip().lower(), item.strip().lower())
        if key:
            declared.add(key)
    impact_globs = rules.get("impact_file_globs") or {}
    for impact, patterns in impact_globs.items():
        for path in packet.changed_files:
            if any_match(path, patterns) and impact not in declared:
                findings.append(Finding(
                    rule_id="impact-undisclosed",
                    severity="warning",
                    title="Potential impact not declared",
                    message="File suggests a %s change, but declared_impacts does not include it." % impact,
                    path=path,
                ))
                break


def _check_sensitive_data(packet, rules, findings):
    if not rules.get("scan_secrets") and not rules.get("scan_pii"):
        return
    scans = scan_text(packet_scan_text(packet), include_pii=bool(rules.get("scan_pii")))
    for item in scans:
        if item["kind"] == "secret" and not rules.get("scan_secrets"):
            continue
        severity = "error" if item["kind"] == "secret" else "warning"
        findings.append(Finding(
            rule_id="%s-detected" % item["kind"],
            severity=severity,
            title="%s pattern detected" % item["kind"].upper(),
            message="Detected %s pattern '%s' in packet content: %s" % (
                item["kind"],
                item["pattern"],
                item["snippet"],
            ),
        ))
