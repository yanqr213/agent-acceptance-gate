# agent-acceptance-gate

离线 CLI，用来对一次 AI coding agent 交付做验收门禁。它读取 agent 提供的验收包、变更文件、测试结果、风险声明和规则配置，输出 Markdown、JSON、JUnit、SARIF 或 remediation 报告，并可在 CI 中用 `--check` 阻断不合格交付。

本项目和 `agent-handoff-kit` 的边界很清楚：handoff 工具关注“交接包是否完整、上下文是否能传给下一个人或 agent”，`agent-acceptance-gate` 关注“这次交付能不能过团队验收门禁”。

## 适用场景

- 团队把 Codex、Claude Code、Cursor、ChatGPT agent 接入日常开发流程。
- 需要离线检查 agent 交付是否写明测试、风险、owner 和 rollback plan。
- 需要在 CI 中检查高风险路径、禁止路径、未声明的 API/DB/schema/config 变更。
- 需要扫描验收包中的 secret 或 PII 痕迹。
- 需要把验收结果输出为 Markdown 给人读，JSON 给系统读，JUnit 给 CI 展示，SARIF 给 GitHub Code Scanning 或安全看板消费。
- 需要用 baseline 记录已复核的历史验收 finding，让 CI 只拦截新增 warning/error。
- 需要把失败 finding 转成可执行的修复队列，给 Codex、Claude Code、Cursor 或内部 bot 继续处理。

## 快速开始

```bash
python -m pip install -e .
python -m agent_acceptance_gate --packet examples/acceptance-packet.json --rules examples/rules.yml --format markdown
```

也可以使用安装后的命令：

```bash
agent-acceptance-gate --packet examples/acceptance-packet.md --rules examples/rules.yml --format json
agent-acceptance-gate --packet examples/acceptance-packet.json --rules examples/rules.yml --format sarif --output reports/aag.sarif
agent-acceptance-gate --packet examples/acceptance-packet.json --rules examples/rules.yml --format remediation --output reports/remediation.md
agent-acceptance-gate --packet examples/acceptance-packet.json --rules examples/rules.yml --format remediation-json --output reports/remediation.json
aag --packet examples/acceptance-packet.json --check warning
```

生成并使用 reviewed baseline：

```bash
agent-acceptance-gate --packet examples/acceptance-packet.json --rules examples/rules.yml --write-baseline reports/aag-baseline.json
agent-acceptance-gate --packet examples/acceptance-packet.json --rules examples/rules.yml --baseline reports/aag-baseline.json --check warning
```

## 输入格式

验收包支持 JSON、YAML-lite 和 Markdown。推荐字段：

```json
{
  "summary": "Add stricter validation to the local acceptance gate CLI.",
  "owner": "platform-quality",
  "rollback_plan": "Revert the CLI validation commit and rerun the previous release package.",
  "risk_statement": "Low operational risk.",
  "changed_files": ["src/agent_acceptance_gate/cli.py"],
  "declared_impacts": ["config"],
  "tests": [
    {
      "command": "python -m unittest discover -s tests",
      "status": "passed",
      "output": "Ran tests successfully"
    }
  ],
  "diff_summary": "CLI validates packets, evaluates rules, and renders reports."
}
```

Markdown 包按标题解析：

```markdown
# Summary
Add stricter validation.

# Owner
platform-quality

# Rollback Plan
Revert the validation commit.

# Risk Statement
Low risk.

# Changed Files
- src/agent_acceptance_gate/cli.py

# Tests
- passed: python -m unittest discover -s tests
```

YAML-lite 支持字典、列表、布尔值和字符串，足够覆盖规则文件和常见验收包；它不是完整 YAML 解释器。

## 规则配置

默认规则包含：

- `required_tests`: 是否要求至少一个通过的测试命令。
- `required_fields`: 必填字段，如 `summary`、`risk_statement`。
- `require_owner`: 是否要求 owner。
- `require_rollback_plan`: 是否要求 rollback plan。
- `risk_path_globs`: 高风险路径，命中后产生 warning。
- `forbidden_paths`: 禁止路径，命中后产生 error。
- `impact_file_globs`: 用文件路径推断 public API、database、schema、config 变更。
- `scan_secrets`: 扫描 secret 模式。
- `scan_pii`: 扫描 PII 模式。

示例：

```yaml
required_tests: true
required_fields:
  - summary
  - risk_statement
require_owner: true
require_rollback_plan: true
risk_path_globs:
  - "**/auth/**"
  - "**/migrations/**"
forbidden_paths:
  - "**/.env"
  - "**/*.pem"
impact_file_globs:
  public_api:
    - "**/api/**"
  database:
    - "**/migrations/**"
scan_secrets: true
scan_pii: true
```

如果文件路径暗示 API、DB、schema 或 config 变更，但 `declared_impacts` 未声明相应影响，报告会给出 warning。

## CI 用法

`--check error` 在存在 error 时返回退出码 `1`。`--check warning` 在存在 warning 或 error 时返回退出码 `1`。

```bash
agent-acceptance-gate \
  --packet acceptance-packet.json \
  --rules acceptance-rules.yml \
  --format sarif \
  --output reports/agent-acceptance-gate.sarif \
  --check warning
```

输出文件的父目录会自动创建。

如果已有仓库首次接入时存在一批已复核 warning，可以先生成 baseline，再在后续 CI 中消费它：

```bash
agent-acceptance-gate \
  --packet acceptance-packet.json \
  --rules acceptance-rules.yml \
  --write-baseline reports/agent-acceptance-baseline.json

agent-acceptance-gate \
  --packet acceptance-packet.json \
  --rules acceptance-rules.yml \
  --baseline reports/agent-acceptance-baseline.json \
  --format json \
  --output reports/agent-acceptance-gate.json \
  --check warning
```

baseline 是可审阅、可提交的 JSON 文件，包含 `rule_id`、`path`、`title`、`message` 和稳定 `fingerprint`。不要在同一个阻断型 CI run 中先生成 baseline 再扫描当前交付，否则当前 finding 会被直接放过。

需要把 CI 失败交给人或 agent 继续修时，可以生成 remediation 报告：

```bash
agent-acceptance-gate \
  --packet acceptance-packet.json \
  --rules acceptance-rules.yml \
  --format remediation \
  --output reports/agent-acceptance-remediation.md

agent-acceptance-gate \
  --packet acceptance-packet.json \
  --rules acceptance-rules.yml \
  --format remediation-json \
  --output reports/agent-acceptance-remediation.json
```

`remediation` 是给人读的 Markdown 修复计划；`remediation-json` 是给自动化系统、issue bot、PR 评论机器人或多 agent 调度器消费的稳定 JSON。每个任务包含 `priority`、`owner_hint`、`recommended_action`、`acceptance_criteria`、`agent_prompt` 和稳定 `fingerprint`。使用 baseline 后，已复核 finding 不会变成新的 remediation task，但 suppressed 数量仍保留在摘要里。

GitHub Actions 中可以把 SARIF 上传到 Code Scanning：

```yaml
permissions:
  contents: read
  security-events: write
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.12"
  - run: python -m pip install .
  - run: agent-acceptance-gate --packet acceptance-packet.json --rules acceptance-rules.yml --format sarif --output reports/aag.sarif --check error
  - uses: github/codeql-action/upload-sarif@v3
    if: always()
    with:
      sarif_file: reports/aag.sarif
```

## 输出示例

Markdown：

```markdown
# Agent Acceptance Gate Report

- Status: `pass`
- Errors: `0`
- Warnings: `1`

## Findings

- **[WARNING] High-risk path changed** `risk-path` (service/auth/login.py) - Changed file matches a high-risk path rule.
```

JSON：

```json
{
  "status": "pass",
  "summary": {
    "errors": 0,
    "warnings": 1,
    "changed_files": 1,
    "tests": 1
  },
  "findings": []
}
```

Remediation：

~~~markdown
# Agent Acceptance Remediation Plan

- Status: `fail`
- Tasks: `1`

## AAG-P1-abc12345: No tests reported

- Priority: `P1`
- Owner hint: `test-owner`

### Agent Prompt

```text
You are repairing an agent-acceptance-gate finding.
Current gate status: fail (1 errors, 0 warnings).
After the fix, rerun the exact gate command and include the result in the delivery notes.
```
~~~

JUnit 输出适合上传到 CI 测试报告视图；error 会渲染为 `<failure>`，warning 会渲染为 `<system-out>`。SARIF 输出适合把 risky path、forbidden path、敏感信息和未声明影响作为 code scanning alert 展示。Remediation 输出适合把 finding 转成修复任务、Issue、PR 评论或下一轮 agent prompt。使用 baseline 后，Markdown、JSON、JUnit、SARIF 和 remediation 都会保留 suppressed finding 统计或明细，方便后续清理历史例外。

## 和 handoff 工具的边界

- `agent-handoff-kit`: 关注上下文、任务状态、后续步骤、交接材料。
- `agent-acceptance-gate`: 关注验收规则、风险声明、测试结果、敏感信息和 CI gate。

两个工具可以串联使用：先由 handoff 工具生成交接包，再由本项目读取验收包并做门禁判断。

## 限制

- Secret/PII 扫描是启发式规则，不替代专业 DLP 或密钥扫描器。
- YAML-lite 不是完整 YAML 标准实现，不支持锚点、复杂 tag 或多文档流。
- Diff summary 只按输入内容判断；CLI 不会主动连接远程服务，也不会请求 GitHub token。
- 规则结果服务于验收决策，不替代人工代码评审。
- baseline 是审计文件，不是永久忽略规则；请像维护安全例外一样审阅和定期清理。

## 维护说明

- Python 3.9+。
- 运行时优先标准库，无第三方依赖。
- 测试命令：`python -m unittest discover -s tests`。
- 修改规则、输入格式或 CLI flags 时，请同步更新 README、CHANGELOG 和测试。

---

# English

`agent-acceptance-gate` is an offline CLI for acceptance-gating AI coding agent deliveries. It reads an acceptance packet, changed files, test command results, risk statements, diff summaries, and rule configuration. It emits Markdown, JSON, JUnit, SARIF, or remediation reports and supports CI blocking through `--check`.

It is intentionally different from `agent-handoff-kit`: handoff tooling focuses on transferring context and next steps, while this project focuses on deciding whether a delivered change passes acceptance gates.

## Use Cases

- Teams using Codex, Claude Code, Cursor, or ChatGPT agent in daily development.
- Offline validation that a delivery includes tests, owner, rollback plan, and risk statement.
- CI checks for risky paths, forbidden paths, and undisclosed API, database, schema, or configuration changes.
- Heuristic scanning for secrets and personal data in the acceptance packet.
- Human-readable Markdown, machine-readable JSON, CI-friendly JUnit, and GitHub Code Scanning friendly SARIF output.
- Reviewed baselines for accepted historical gate findings, while still failing CI on new findings.
- Remediation queues that turn failed findings into prioritized tasks, owner hints, acceptance criteria, and copy-ready agent prompts.

## Quick Start

```bash
python -m pip install -e .
python -m agent_acceptance_gate --packet examples/acceptance-packet.json --rules examples/rules.yml --format markdown
```

Installed commands:

```bash
agent-acceptance-gate --packet examples/acceptance-packet.md --rules examples/rules.yml --format json
agent-acceptance-gate --packet examples/acceptance-packet.json --rules examples/rules.yml --format sarif --output reports/aag.sarif
agent-acceptance-gate --packet examples/acceptance-packet.json --rules examples/rules.yml --format remediation --output reports/remediation.md
agent-acceptance-gate --packet examples/acceptance-packet.json --rules examples/rules.yml --format remediation-json --output reports/remediation.json
aag --packet examples/acceptance-packet.json --check warning
```

Baseline workflow:

```bash
agent-acceptance-gate --packet examples/acceptance-packet.json --rules examples/rules.yml --write-baseline reports/aag-baseline.json
agent-acceptance-gate --packet examples/acceptance-packet.json --rules examples/rules.yml --baseline reports/aag-baseline.json --check warning
```

## Input Format

Acceptance packets can be JSON, YAML-lite, or Markdown. Recommended fields are `summary`, `owner`, `rollback_plan`, `risk_statement`, `changed_files`, `declared_impacts`, `tests`, and `diff_summary`.

Test statuses such as `passed`, `pass`, `success`, `ok`, and `green` are treated as passing. Markdown packets are parsed by section headings such as `Summary`, `Owner`, `Rollback Plan`, `Risk Statement`, `Changed Files`, `Declared Impacts`, `Tests`, and `Diff Summary`.

## Rule Configuration

Rules include required tests, required fields, owner, rollback plan, risky path globs, forbidden path globs, impact file globs, secret scanning, and PII scanning. If a changed file suggests a public API, database, schema, or config impact but `declared_impacts` does not include that impact, the report emits a warning.

## CI Usage

`--check error` exits with code `1` when errors exist. `--check warning` exits with code `1` when warnings or errors exist.

```bash
agent-acceptance-gate \
  --packet acceptance-packet.json \
  --rules acceptance-rules.yml \
  --format sarif \
  --output reports/agent-acceptance-gate.sarif \
  --check warning
```

The CLI creates the output parent directory automatically.

Reviewed baseline JSON files contain stable fingerprints for accepted findings. Commit or otherwise review the baseline before using it in CI; do not generate and consume a baseline in the same blocking CI run.

Generate remediation reports when a failed gate should become a repair queue for a human, bot, or coding agent:

```bash
agent-acceptance-gate \
  --packet acceptance-packet.json \
  --rules acceptance-rules.yml \
  --format remediation \
  --output reports/agent-acceptance-remediation.md

agent-acceptance-gate \
  --packet acceptance-packet.json \
  --rules acceptance-rules.yml \
  --format remediation-json \
  --output reports/agent-acceptance-remediation.json
```

`remediation` is a human-readable Markdown repair plan. `remediation-json` is stable structured output for issue bots, PR comments, CI queue tooling, or multi-agent schedulers. Each task includes `priority`, `owner_hint`, `recommended_action`, `acceptance_criteria`, `agent_prompt`, and the stable finding `fingerprint`. Baseline-suppressed findings do not become new remediation tasks, but their count remains visible in the summary.

GitHub Actions can upload SARIF to Code Scanning:

```yaml
permissions:
  contents: read
  security-events: write
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.12"
  - run: python -m pip install .
  - run: agent-acceptance-gate --packet acceptance-packet.json --rules acceptance-rules.yml --format sarif --output reports/aag.sarif --check error
  - uses: github/codeql-action/upload-sarif@v3
    if: always()
    with:
      sarif_file: reports/aag.sarif
```

## Output

Markdown reports summarize status, counts, findings, tests, and changed files. JSON reports provide stable structured fields for automation. JUnit reports render errors as failures and warnings as system output. SARIF reports map gate findings to code scanning results so risky paths, forbidden files, sensitive-data findings, and undeclared impacts can appear in security dashboards. Remediation reports turn findings into prioritized repair tasks with owner hints, acceptance criteria, and copy-ready prompts for another agent pass. Suppressed baseline findings remain visible in report metadata for audit and cleanup.

## Boundary with Handoff Tools

`agent-handoff-kit` answers “can someone continue this work with enough context?” This project answers “does this delivered change satisfy the team acceptance gate?” They can be used together, but they solve different parts of the agent workflow.

## Limitations

- Secret and PII detection is heuristic and does not replace dedicated scanners.
- YAML-lite is intentionally small and does not implement the full YAML specification.
- The CLI does not connect to remote services and never needs a GitHub token.
- Gate results support engineering judgment but do not replace human review.

## Maintenance

Use Python 3.9 or newer. Runtime dependencies are intentionally avoided. Run `python -m unittest discover -s tests` before shipping changes, and update documentation plus changelog for user-visible behavior changes.
