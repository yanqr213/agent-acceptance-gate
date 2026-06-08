import hashlib
import json

from . import __version__
from .models import Finding, GateResult


def fingerprint_finding(finding: Finding) -> str:
    payload = {
        "rule_id": finding.rule_id,
        "path": _normalize_path(finding.path or ""),
        "title": finding.title,
        "message": " ".join(finding.message.split()),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]


def attach_fingerprints(result: GateResult) -> GateResult:
    for finding in result.findings:
        if not finding.fingerprint:
            finding.fingerprint = fingerprint_finding(finding)
    for finding in result.suppressed_findings:
        if not finding.fingerprint:
            finding.fingerprint = fingerprint_finding(finding)
    return result


def load_baseline(path: str) -> set[str]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        entries = data.get("findings", [])
    else:
        raise ValueError("baseline must be a JSON object or list")
    fingerprints = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        fingerprint = entry.get("fingerprint")
        if isinstance(fingerprint, str) and fingerprint:
            fingerprints.add(fingerprint)
    return fingerprints


def apply_baseline(result: GateResult, fingerprints) -> GateResult:
    known = set(fingerprints)
    attach_fingerprints(result)
    kept = []
    suppressed = []
    for finding in result.findings:
        if finding.fingerprint in known:
            suppressed.append(finding)
        else:
            kept.append(finding)
    result.findings = kept
    result.suppressed_findings = suppressed
    result.status = "fail" if any(item.severity == "error" for item in result.findings) else "pass"
    return result


def render_baseline(result: GateResult) -> str:
    attach_fingerprints(result)
    data = {
        "schema_version": 1,
        "generated_by": "agent-acceptance-gate",
        "tool_version": __version__,
        "description": "Known acceptance gate findings. Review before committing; CI can use this file to fail only on new findings.",
        "finding_count": len(result.findings),
        "error_count": result.error_count,
        "warning_count": result.warning_count,
        "findings": [
            {
                "fingerprint": finding.fingerprint,
                "rule_id": finding.rule_id,
                "severity": finding.severity,
                "title": finding.title,
                "message": finding.message,
                "path": _normalize_path(finding.path or ""),
            }
            for finding in sorted(result.findings, key=lambda item: (item.rule_id, item.path or "", item.fingerprint))
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("a/") or normalized.startswith("b/"):
        normalized = normalized[2:]
    return normalized
