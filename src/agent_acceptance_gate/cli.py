import argparse
import sys

from . import __version__
from .baseline import apply_baseline, load_baseline, render_baseline
from .parser import load_packet, load_rules
from .report import render, write_report
from .rules import evaluate


def build_parser():
    parser = argparse.ArgumentParser(
        prog="agent-acceptance-gate",
        description="Offline acceptance gate for AI coding agent deliveries.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--packet", required=True, help="Acceptance packet path: JSON, YAML-lite, or Markdown.")
    parser.add_argument("--rules", help="Rule configuration path: JSON or YAML-lite.")
    parser.add_argument("--format", choices=["markdown", "json", "junit", "sarif"], default="markdown", help="Report format.")
    parser.add_argument("--output", help="Write report to this path. Parent directories are created.")
    parser.add_argument("--baseline", help="JSON baseline file. Matching findings are suppressed before reporting and --check.")
    parser.add_argument("--write-baseline", help="Write a reviewed baseline JSON for current findings instead of a normal report. Use '-' for stdout.")
    parser.add_argument(
        "--check",
        choices=["warning", "error"],
        help="Exit non-zero when warnings or errors are present.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        packet = load_packet(args.packet)
        rules = load_rules(args.rules)
        result = evaluate(packet, rules)
        if args.write_baseline:
            content = render_baseline(result)
            if args.write_baseline == "-":
                sys.stdout.write(content)
            else:
                write_text(args.write_baseline, content)
            return 0
        if args.baseline:
            result = apply_baseline(result, load_baseline(args.baseline))
        if args.output:
            content = write_report(result, args.format, args.output)
        else:
            content = render(result, args.format)
        if not args.output:
            sys.stdout.write(content)
        if args.check == "error" and result.error_count:
            return 1
        if args.check == "warning" and (result.error_count or result.warning_count):
            return 1
        return 0
    except Exception as exc:
        sys.stderr.write("agent-acceptance-gate: %s\n" % exc)
        return 2


def write_text(path, content):
    import os

    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


if __name__ == "__main__":
    raise SystemExit(main())
