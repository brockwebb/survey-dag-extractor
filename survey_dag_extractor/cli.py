from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from survey_dag_extractor.healing import recommend_repairs
from survey_dag_extractor.model import SurveyModel
from survey_dag_extractor.patching import apply_approved_recommendations
from survey_dag_extractor.reports import format_markdown_report, safe_survey_id
from survey_dag_extractor.testing import generate_coverage_tests
from survey_dag_extractor.validation import validate_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="survey-dag")
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate", help="Validate a canonical survey DAG JSON file")
    validate.add_argument("survey_path", type=Path)
    validate.add_argument("--report", type=Path)
    validate.set_defaults(func=_validate)

    heal = subcommands.add_parser("heal", help="Generate deterministic repair recommendations")
    heal.add_argument("survey_path", type=Path)
    heal.add_argument("--output", type=Path)
    heal.set_defaults(func=_heal)

    apply_cmd = subcommands.add_parser("apply", help="Apply approved recommendations")
    apply_cmd.add_argument("survey_path", type=Path)
    apply_cmd.add_argument("decisions_path", type=Path)
    apply_cmd.add_argument("--output", type=Path, required=True)
    apply_cmd.set_defaults(func=_apply)

    test_cmd = subcommands.add_parser("test", help="Generate and simulate coverage tests")
    test_cmd.add_argument("survey_path", type=Path)
    test_cmd.add_argument("--coverage", choices=["node", "edge"], default="edge")
    test_cmd.add_argument("--output", type=Path)
    test_cmd.set_defaults(func=_test)

    return parser


def _validate(args: argparse.Namespace) -> int:
    model = SurveyModel.from_path(args.survey_path)
    issues = validate_model(model)
    if args.report:
        args.report.write_text(format_markdown_report(model, issues), encoding="utf-8")
    payload = {
        "survey_id": safe_survey_id(model),
        "status": "valid" if not issues else "invalid",
        "issue_count": len(issues),
        "issues": [issue.to_dict() for issue in issues],
    }
    print(json.dumps(payload, indent=2))
    return 0 if not issues else 1


def _heal(args: argparse.Namespace) -> int:
    model = SurveyModel.from_path(args.survey_path)
    issues = validate_model(model)
    recommendations = recommend_repairs(model, issues)
    payload = {
        "survey_id": model.survey_id,
        "recommendation_count": len(recommendations),
        "recommendations": [recommendation.to_dict() for recommendation in recommendations],
    }
    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


def _apply(args: argparse.Namespace) -> int:
    model = SurveyModel.from_path(args.survey_path)
    issues = validate_model(model)
    recommendations = recommend_repairs(model, issues)
    with args.decisions_path.open("r", encoding="utf-8") as file:
        decisions = json.load(file)
    patched = apply_approved_recommendations(model.document, recommendations, decisions)
    args.output.write_text(json.dumps(patched, indent=2), encoding="utf-8")
    print(json.dumps({"status": "applied", "output": str(args.output)}, indent=2))
    return 0


def _test(args: argparse.Namespace) -> int:
    model = SurveyModel.from_path(args.survey_path)
    payload = generate_coverage_tests(model, args.coverage)
    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


def _not_implemented(args: argparse.Namespace) -> int:
    print(json.dumps({"command": args.command, "status": "not_implemented"}, indent=2))
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
