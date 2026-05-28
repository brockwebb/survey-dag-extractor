import json
from pathlib import Path

from survey_dag_extractor.cli import main
from survey_dag_extractor.healing import recommend_repairs
from survey_dag_extractor.model import SurveyModel
from survey_dag_extractor.patching import apply_approved_recommendations
from survey_dag_extractor.validation import validate_model


FIXTURES = Path(__file__).parent / "fixtures"


def test_missing_fallthrough_gets_add_edge_recommendation():
    model = SurveyModel.from_path(FIXTURES / "missing_fallthrough_survey.json")
    issues = validate_model(model)
    recommendations = recommend_repairs(model, issues)

    assert recommendations
    recommendation = recommendations[0]
    assert recommendation.type == "add_fallthrough_edge"
    assert recommendation.patch[0]["op"] == "add_edge"
    assert recommendation.patch[0]["edge"]["source"] == "Q1"
    assert recommendation.patch[0]["edge"]["target"] == "Q2"


def test_approved_fallthrough_patch_resolves_missing_fallthrough():
    model = SurveyModel.from_path(FIXTURES / "missing_fallthrough_survey.json")
    issues = validate_model(model)
    recommendations = recommend_repairs(model, issues)
    decisions = [
        {
            "recommendation_id": recommendations[0].id,
            "decision": "approved",
            "approver": "human",
            "rationale": "Default path should continue to Q2 for this fixture.",
        }
    ]

    patched = apply_approved_recommendations(model.document, recommendations, decisions)
    patched_model = SurveyModel(patched)
    issue_types = {issue.type for issue in validate_model(patched_model)}

    assert "missing_fallthrough" not in issue_types


def test_heal_cli_prints_recommendations(capsys):
    exit_code = main(["heal", str(FIXTURES / "missing_fallthrough_survey.json")])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["survey_id"] == "missing_fallthrough"
    assert payload["recommendation_count"] == 1
    assert payload["recommendations"][0]["type"] == "add_fallthrough_edge"


def test_apply_cli_writes_patched_survey(tmp_path, capsys):
    survey_path = FIXTURES / "missing_fallthrough_survey.json"
    model = SurveyModel.from_path(survey_path)
    recommendations = recommend_repairs(model, validate_model(model))
    decisions_path = tmp_path / "decisions.json"
    output_path = tmp_path / "patched.json"
    decisions_path.write_text(
        json.dumps(
            [
                {
                    "recommendation_id": recommendations[0].id,
                    "decision": "approved",
                    "approver": "human",
                    "rationale": "Approved for CLI patch test.",
                }
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["apply", str(survey_path), str(decisions_path), "--output", str(output_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    patched_model = SurveyModel.from_path(output_path)
    issue_types = {issue.type for issue in validate_model(patched_model)}

    assert exit_code == 0
    assert payload["status"] == "applied"
    assert payload["output"] == str(output_path)
    assert "missing_fallthrough" not in issue_types
