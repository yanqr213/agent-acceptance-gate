import re


SECRET_PATTERNS = [
    ("secret.assignment", re.compile(r"(?i)\b(api[_-]?key|token|secret|password|private[_-]?key)\b\s*[:=]\s*['\"]?([A-Za-z0-9_./+=-]{16,})")),
    ("aws.access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private.key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("bearer.token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_./+=-]{20,}")),
]

PII_PATTERNS = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("us.ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("phone", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")),
]


def scan_text(text, include_pii=True):
    findings = []
    value = text or ""
    for name, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(value):
            findings.append({"kind": "secret", "pattern": name, "snippet": _mask(match.group(0))})
    if include_pii:
        for name, pattern in PII_PATTERNS:
            for match in pattern.finditer(value):
                findings.append({"kind": "pii", "pattern": name, "snippet": _mask(match.group(0))})
    return findings


def packet_scan_text(packet):
    parts = [
        packet.summary,
        packet.risk_statement,
        packet.rollback_plan,
        packet.diff_summary,
        "\n".join(packet.changed_files),
        "\n".join(packet.declared_impacts),
    ]
    for test in packet.tests:
        parts.extend([test.command, test.output])
    return "\n".join(parts)


def _mask(value):
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-4:]
