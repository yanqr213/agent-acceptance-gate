from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TestResult:
    command: str = ""
    status: str = ""
    output: str = ""

    @property
    def passed(self):
        return self.status.lower() in ("pass", "passed", "success", "ok", "green")


@dataclass
class AcceptancePacket:
    summary: str = ""
    owner: str = ""
    rollback_plan: str = ""
    risk_statement: str = ""
    changed_files: List[str] = field(default_factory=list)
    diff_summary: str = ""
    tests: List[TestResult] = field(default_factory=list)
    declared_impacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Finding:
    rule_id: str
    severity: str
    title: str
    message: str
    path: Optional[str] = None
    fingerprint: str = ""


@dataclass
class GateResult:
    status: str
    findings: List[Finding]
    packet: AcceptancePacket
    suppressed_findings: List[Finding] = field(default_factory=list)

    @property
    def error_count(self):
        return sum(1 for item in self.findings if item.severity == "error")

    @property
    def warning_count(self):
        return sum(1 for item in self.findings if item.severity == "warning")


DEFAULT_RULES = {
    "required_tests": True,
    "required_fields": ["summary", "risk_statement"],
    "require_owner": True,
    "require_rollback_plan": True,
    "risk_path_globs": [
        "**/auth/**",
        "**/security/**",
        "**/payment/**",
        "**/billing/**",
        "**/migrations/**",
        "**/schema/**",
        "**/infra/**",
        "**/.github/workflows/**",
    ],
    "forbidden_paths": [
        "**/.env",
        "**/.env.*",
        "**/id_rsa",
        "**/id_ed25519",
        "**/*.pem",
        "**/*.key",
    ],
    "impact_file_globs": {
        "public_api": ["**/api/**", "**/routes/**", "**/openapi.*", "**/*api*.py", "**/*api*.ts"],
        "database": ["**/migrations/**", "**/*migration*", "**/db/**", "**/database/**"],
        "schema": ["**/schema/**", "**/*.schema.json", "**/graphql/**", "**/*.graphql"],
        "config": ["**/*.toml", "**/*.yml", "**/*.yaml", "**/*.ini", "**/*.cfg", "**/.github/workflows/**"],
    },
    "scan_secrets": True,
    "scan_pii": True,
}
