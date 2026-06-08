import json
import os
import re

from .models import AcceptancePacket, TestResult
from .yaml_lite import parse_yaml_lite


def load_packet(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        text = handle.read()
    return parse_packet(text, path)


def load_rules(path):
    if not path:
        return {}
    with open(path, "r", encoding="utf-8-sig") as handle:
        text = handle.read()
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        return json.loads(text)
    return parse_yaml_lite(text)


def parse_packet(text, source_name="packet"):
    text = text.lstrip("\ufeff")
    ext = os.path.splitext(source_name)[1].lower()
    if ext == ".json":
        data = json.loads(text)
    elif ext in (".yml", ".yaml"):
        data = parse_yaml_lite(text)
    elif ext in (".md", ".markdown"):
        data = parse_markdown_packet(text)
    else:
        stripped = text.lstrip()
        if stripped.startswith("{"):
            data = json.loads(text)
        elif stripped.startswith("#"):
            data = parse_markdown_packet(text)
        else:
            data = parse_yaml_lite(text)
    return packet_from_dict(data)


def parse_markdown_packet(text):
    sections = {}
    current = "summary"
    buffer = []
    for line in text.splitlines():
        match = re.match(r"^#{1,3}\s+(.+?)\s*$", line)
        if match:
            sections[current] = "\n".join(buffer).strip()
            current = _slug(match.group(1))
            buffer = []
        else:
            buffer.append(line)
    sections[current] = "\n".join(buffer).strip()

    data = {
        "summary": sections.get("summary", ""),
        "risk_statement": sections.get("risk-statement", sections.get("risk", "")),
        "rollback_plan": sections.get("rollback-plan", sections.get("rollback", "")),
        "owner": sections.get("owner", ""),
        "diff_summary": sections.get("diff-summary", sections.get("diff", "")),
        "changed_files": _extract_list(sections.get("changed-files", sections.get("files", ""))),
        "declared_impacts": _extract_list(sections.get("declared-impacts", sections.get("impacts", ""))),
        "tests": _extract_tests(sections.get("tests", "")),
    }
    return data


def packet_from_dict(data):
    data = data or {}
    tests = []
    for item in data.get("tests") or []:
        if isinstance(item, str):
            tests.append(TestResult(command=item, status=""))
        else:
            tests.append(TestResult(
                command=str(item.get("command", "")),
                status=str(item.get("status", "")),
                output=str(item.get("output", "")),
            ))
    changed_files = data.get("changed_files", data.get("changedFiles", [])) or []
    declared_impacts = data.get("declared_impacts", data.get("declaredImpacts", [])) or []
    return AcceptancePacket(
        summary=str(data.get("summary", "") or ""),
        owner=str(data.get("owner", "") or ""),
        rollback_plan=str(data.get("rollback_plan", data.get("rollbackPlan", "")) or ""),
        risk_statement=str(data.get("risk_statement", data.get("riskStatement", "")) or ""),
        changed_files=[str(item) for item in changed_files],
        diff_summary=str(data.get("diff_summary", data.get("diffSummary", "")) or ""),
        tests=tests,
        declared_impacts=[str(item) for item in declared_impacts],
        metadata=dict(data.get("metadata") or {}),
    )


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _extract_list(text):
    values = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        stripped = re.sub(r"^[-*]\s+", "", stripped)
        values.append(stripped)
    return values


def _extract_tests(text):
    tests = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        stripped = re.sub(r"^[-*]\s+", "", stripped)
        status = ""
        command = stripped
        if ":" in stripped:
            left, right = stripped.split(":", 1)
            if left.strip().lower() in ("pass", "passed", "fail", "failed", "warning", "skipped"):
                status = left.strip()
                command = right.strip()
        tests.append({"command": command, "status": status})
    return tests
