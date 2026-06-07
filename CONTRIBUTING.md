# Contributing

Thanks for helping improve Agent Acceptance Gate.

## Development

Use Python 3.9 or newer. The runtime has no third-party dependencies.

```bash
python -m unittest discover -s tests
python -m agent_acceptance_gate --packet examples/acceptance-packet.json --rules examples/rules.yml --format markdown
```

## Design Principles

- Keep the CLI offline and deterministic.
- Prefer Python standard library modules.
- Keep rules explicit and explainable.
- Avoid storing secrets, personal data, or generated caches in the repository.

## Pull Request Checklist

- Add or update tests for parser, rules, rendering, or CLI behavior.
- Update `README.md` when CLI flags, input formats, or rules change.
- Update `CHANGELOG.md` for user-visible changes.
