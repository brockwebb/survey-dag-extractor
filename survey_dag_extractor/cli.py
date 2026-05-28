from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from survey_dag_extractor.healing import link_recommendations_to_issues, recommend_repairs
from survey_dag_extractor.issues import Recommendation
from survey_dag_extractor.model import SurveyModel
from survey_dag_extractor.patching import apply_approved_recommendations_with_summary
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
    heal.add_argument("--decisions-template", type=Path)
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
    linked_issues = link_recommendations_to_issues(issues, recommendations)
    payload = {
        "survey_id": model.survey_id,
        "issue_count": len(linked_issues),
        "issues": [issue.to_dict() for issue in linked_issues],
        "recommendation_count": len(recommendations),
        "recommendations": [recommendation.to_dict() for recommendation in recommendations],
    }
    if args.decisions_template:
        args.decisions_template.write_text(json.dumps(_decision_template(recommendations), indent=2), encoding="utf-8")
        payload["decisions_template"] = str(args.decisions_template)
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
    result = apply_approved_recommendations_with_summary(model.document, recommendations, decisions)
    patched = result.document
    post_issues = validate_model(SurveyModel(patched))
    args.output.write_text(json.dumps(patched, indent=2), encoding="utf-8")
    payload = {
        "status": "applied" if result.applied_count else "no_changes",
        "output": str(args.output),
        "decision_count": result.decision_count,
        "applied_count": result.applied_count,
        "skipped_count": result.skipped_count,
        "logged_count": result.logged_count,
        "post_validation_status": "valid" if not post_issues else "invalid",
        "post_issue_count": len(post_issues),
    }
    print(json.dumps(payload, indent=2))
    return 0 if not post_issues else 1


def _test(args: argparse.Namespace) -> int:
    model = SurveyModel.from_path(args.survey_path)
    payload = generate_coverage_tests(model, args.coverage)
    coverage_complete = _coverage_complete(payload)
    payload["coverage_status"] = "complete" if coverage_complete else "incomplete"
    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0 if coverage_complete else 1


def _decision_template(recommendations: list[Recommendation]) -> list[dict[str, str]]:
    return [
        {
            "recommendation_id": recommendation.id,
            "decision": "pending",
            "approver": "",
            "rationale": f"Review recommendation {recommendation.id}: approve or reject with rationale.",
        }
        for recommendation in recommendations
    ]


def _coverage_complete(payload: dict) -> bool:
    if payload["coverage_target"] == "node":
        return payload["coverage"]["node_percent"] == 100 and not payload["uncovered_nodes"]
    return (
        payload["coverage"]["edge_percent"] == 100
        and not payload["uncovered_edges"]
        and not payload["unverified_paths"]
    )


def _not_implemented(args: argparse.Namespace) -> int:
    print(json.dumps({"command": args.command, "status": "not_implemented"}, indent=2))
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except json.JSONDecodeError as error:
        _print_error("invalid_json", f"{error.msg} at line {error.lineno}, column {error.colno}")
        return 2
    except OSError as error:
        _print_error("file_error", str(error))
        return 2
    except ValueError as error:
        _print_error("input_error", str(error))
        return 2


def _print_error(error_type: str, message: str) -> None:
    print(
        json.dumps(
            {
                "status": "error",
                "error": {
                    "type": error_type,
                    "message": message,
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
