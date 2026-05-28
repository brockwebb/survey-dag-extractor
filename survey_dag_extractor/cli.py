from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="survey-dag")
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate", help="Validate a canonical survey DAG JSON file")
    validate.add_argument("survey_path", type=Path)
    validate.add_argument("--report", type=Path)
    validate.set_defaults(func=_not_implemented)

    heal = subcommands.add_parser("heal", help="Generate deterministic repair recommendations")
    heal.add_argument("survey_path", type=Path)
    heal.add_argument("--output", type=Path)
    heal.set_defaults(func=_not_implemented)

    apply_cmd = subcommands.add_parser("apply", help="Apply approved recommendations")
    apply_cmd.add_argument("survey_path", type=Path)
    apply_cmd.add_argument("decisions_path", type=Path)
    apply_cmd.add_argument("--output", type=Path, required=True)
    apply_cmd.set_defaults(func=_not_implemented)

    test_cmd = subcommands.add_parser("test", help="Generate and simulate coverage tests")
    test_cmd.add_argument("survey_path", type=Path)
    test_cmd.add_argument("--coverage", choices=["node", "edge"], default="edge")
    test_cmd.add_argument("--output", type=Path)
    test_cmd.set_defaults(func=_not_implemented)

    return parser


def _not_implemented(args: argparse.Namespace) -> int:
    print(json.dumps({"command": args.command, "status": "not_implemented"}, indent=2))
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
