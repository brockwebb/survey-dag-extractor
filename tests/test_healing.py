import json
from pathlib import Path

import pytest

from survey_dag_extractor.cli import main
from survey_dag_extractor.healing import recommend_repairs
from survey_dag_extractor.model import SurveyModel
from survey_dag_extractor.patching import apply_approved_recommendations
from survey_dag_extractor.validation import validate_model


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(path: str) -> dict:
    with (FIXTURES / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def approved_decision(recommendation_id: str) -> dict:
    return {
        "recommendation_id": recommendation_id,
        "decision": "approved",
        "approver": "human",
        "rationale": "Approved for test.",
    }


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


def test_missing_outgoing_question_gets_terminal_exit_recommendation():
    document = load_fixture("valid_minimal_survey.json")
    document["survey"]["dag"]["edges"] = [document["survey"]["dag"]["edges"][0]]
    model = SurveyModel(document)

    recommendations = recommend_repairs(model, validate_model(model))

    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation.type == "add_terminal_exit"
    assert recommendation.confidence == "low"
    assert recommendation.requires_approval
    assert recommendation.patch[0]["op"] == "add_edge"
    assert recommendation.patch[0]["edge"] == {
        "id": "E_AUTO_0001",
        "source": "Q2",
        "target": "SURVEY_COMPLETE",
        "condition": None,
        "condition_text": "terminal exit",
        "priority": 999,
        "type": "terminal",
    }


def test_approved_terminal_exit_patch_resolves_missing_outgoing_and_dead_end():
    document = load_fixture("valid_minimal_survey.json")
    document["survey"]["dag"]["edges"] = [document["survey"]["dag"]["edges"][0]]
    model = SurveyModel(document)
    recommendations = recommend_repairs(model, validate_model(model))

    patched = apply_approved_recommendations(
        model.document,
        recommendations,
        [approved_decision(recommendations[0].id)],
    )

    patched_issue_types = {issue.type for issue in validate_model(SurveyModel(patched))}
    assert "missing_outgoing_edge" not in patched_issue_types
    assert "dead_end" not in patched_issue_types


def test_orphan_reconnect_id_stays_before_terminal_exit_for_original_fixture():
    model = SurveyModel.from_path(FIXTURES / "orphan_node_survey.json")

    recommendations = recommend_repairs(model, validate_model(model))

    assert [(recommendation.id, recommendation.type) for recommendation in recommendations] == [
        ("REC_0001", "connect_orphan_node"),
        ("REC_0002", "add_terminal_exit"),
    ]


def test_orphan_question_gets_reconnect_recommendation():
    document = load_fixture("orphan_node_survey.json")
    document["survey"]["dag"]["edges"].append(
        {
            "id": "E002",
            "source": "Q2",
            "target": "SURVEY_COMPLETE",
            "condition": None,
            "condition_text": "complete",
            "priority": 999,
            "type": "terminal",
        }
    )
    model = SurveyModel(document)

    recommendations = recommend_repairs(model, validate_model(model))

    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation.type == "connect_orphan_node"
    assert recommendation.confidence == "low"
    assert recommendation.requires_approval
    assert recommendation.patch[0]["op"] == "add_edge"
    assert recommendation.patch[0]["edge"] == {
        "id": "E_AUTO_0001",
        "source": "Q1",
        "target": "Q2",
        "condition": None,
        "condition_text": "orphan reconnect",
        "priority": 998,
        "type": "fallthrough",
    }


def test_approved_orphan_reconnect_patch_resolves_orphan_issue():
    document = load_fixture("orphan_node_survey.json")
    document["survey"]["dag"]["edges"].append(
        {
            "id": "E002",
            "source": "Q2",
            "target": "SURVEY_COMPLETE",
            "condition": None,
            "condition_text": "complete",
            "priority": 999,
            "type": "terminal",
        }
    )
    model = SurveyModel(document)
    recommendations = recommend_repairs(model, validate_model(model))

    patched = apply_approved_recommendations(
        model.document,
        recommendations,
        [approved_decision(recommendations[0].id)],
    )

    patched_issues = validate_model(SurveyModel(patched))
    assert "orphan_node" not in {issue.type for issue in patched_issues}


def test_orphan_recommendation_is_not_generated_without_reachable_predecessor():
    document = load_fixture("valid_minimal_survey.json")
    document["survey"]["id"] = "orphan_entry"
    document["survey"]["dag"]["entry_node"] = "Q2"
    document["survey"]["dag"]["edges"] = [
        {
            "id": "E001",
            "source": "Q2",
            "target": "SURVEY_COMPLETE",
            "condition": None,
            "condition_text": "complete",
            "priority": 999,
            "type": "terminal",
        }
    ]
    model = SurveyModel(document)

    recommendations = recommend_repairs(model, validate_model(model))

    assert all(recommendation.type != "connect_orphan_node" for recommendation in recommendations)


@pytest.mark.parametrize(
    "edge_item",
    [
        None,
        {
            "source": "Q1",
            "target": "Q2",
            "condition": None,
            "condition_text": "malformed edge without id",
            "priority": 2,
            "type": "terminal",
        },
    ],
)
def test_recommendation_generation_tolerates_malformed_edge_entries(edge_item):
    document = load_fixture("missing_fallthrough_survey.json")
    document["survey"]["dag"]["edges"].append(edge_item)
    model = SurveyModel(document)

    recommendations = recommend_repairs(model, validate_model(model))

    assert recommendations
    assert recommendations[0].patch[0]["edge"]["source"] == "Q1"


def test_terminal_fallback_skips_undefined_terminal_ids():
    document = load_fixture("missing_fallthrough_survey.json")
    document["survey"]["dag"]["terminal_nodes"] = ["MISSING_TERMINAL"]
    document["survey"]["dag"]["edges"] = [
        {
            "id": "E001",
            "source": "Q1",
            "target": "Q2",
            "condition": None,
            "condition_text": "continue",
            "priority": 999,
            "type": "fallthrough",
        },
        {
            "id": "E002",
            "source": "Q2",
            "target": "SURVEY_COMPLETE",
            "condition": ["=", "Q2", 1],
            "condition_text": "Q2 = 1",
            "priority": 1,
            "type": "branch",
        },
    ]
    model = SurveyModel(document)
    issues = [issue for issue in validate_model(model) if issue.type == "missing_fallthrough"]

    recommendations = recommend_repairs(model, issues)

    assert recommendations == []


def test_recommendation_priority_avoids_duplicate_source_priorities():
    document = load_fixture("missing_fallthrough_survey.json")
    document["survey"]["dag"]["edges"].append(
        {
            "id": "E003",
            "source": "Q1",
            "target": "SURVEY_COMPLETE",
            "condition": None,
            "condition_text": "existing terminal priority",
            "priority": 999,
            "type": "terminal",
        }
    )
    model = SurveyModel(document)

    recommendations = recommend_repairs(model, validate_model(model))

    assert recommendations[0].patch[0]["edge"]["priority"] == 1000


def test_rejected_decision_is_logged_without_applying_patch():
    model = SurveyModel.from_path(FIXTURES / "missing_fallthrough_survey.json")
    recommendations = recommend_repairs(model, validate_model(model))
    decision = {
        "recommendation_id": recommendations[0].id,
        "decision": "rejected",
        "approver": "human",
        "rationale": "Rejected for audit test.",
    }

    patched = apply_approved_recommendations(model.document, recommendations, [decision])

    edges = patched["survey"]["dag"]["edges"]
    decision_log = patched["survey"]["metadata"]["decision_log"]
    assert len(edges) == len(model.document["survey"]["dag"]["edges"])
    assert decision_log[-1]["decision"] == "rejected"
    assert decision_log[-1]["issue_id"] == recommendations[0].issue_id
    assert decision_log[-1]["recommendation_id"] == recommendations[0].id


def test_unknown_recommendation_decision_is_logged_without_applying_patch():
    model = SurveyModel.from_path(FIXTURES / "missing_fallthrough_survey.json")
    recommendations = recommend_repairs(model, validate_model(model))
    decision = {
        "recommendation_id": "REC_STALE",
        "decision": "approved",
        "approver": "human",
        "rationale": "Stale decision should still be auditable.",
    }

    patched = apply_approved_recommendations(model.document, recommendations, [decision])

    edges = patched["survey"]["dag"]["edges"]
    decision_log = patched["survey"]["metadata"]["decision_log"]
    assert len(edges) == len(model.document["survey"]["dag"]["edges"])
    assert decision_log[-1]["decision"] == "approved"
    assert decision_log[-1]["issue_id"] is None
    assert decision_log[-1]["recommendation_id"] == "REC_STALE"


def test_applied_edge_is_isolated_from_later_recommendation_mutation():
    model = SurveyModel.from_path(FIXTURES / "missing_fallthrough_survey.json")
    recommendations = recommend_repairs(model, validate_model(model))
    patched = apply_approved_recommendations(
        model.document,
        recommendations,
        [approved_decision(recommendations[0].id)],
    )
    applied_edge_id = recommendations[0].patch[0]["edge"]["id"]

    recommendations[0].patch[0]["edge"]["target"] = "MUTATED"

    applied_edges = [edge for edge in patched["survey"]["dag"]["edges"] if edge["id"] == applied_edge_id]
    assert applied_edges[0]["target"] == "Q2"


def test_duplicate_approved_decisions_apply_patch_once_and_log_both_decisions():
    model = SurveyModel.from_path(FIXTURES / "missing_fallthrough_survey.json")
    recommendations = recommend_repairs(model, validate_model(model))
    decision = approved_decision(recommendations[0].id)
    duplicate_decision = {
        **approved_decision(recommendations[0].id),
        "rationale": "Duplicate approval should be audited but not re-applied.",
    }

    patched = apply_approved_recommendations(model.document, recommendations, [decision, duplicate_decision])

    patched_model = SurveyModel(patched)
    issue_types = {issue.type for issue in validate_model(patched_model)}
    applied_edge_id = recommendations[0].patch[0]["edge"]["id"]
    applied_edges = [edge for edge in patched["survey"]["dag"]["edges"] if edge["id"] == applied_edge_id]
    logged_decisions = [
        entry
        for entry in patched["survey"]["metadata"]["decision_log"]
        if entry["recommendation_id"] == recommendations[0].id
    ]

    assert len(applied_edges) == 1
    assert "duplicate_priority" not in issue_types
    assert [entry["rationale"] for entry in logged_decisions] == [decision["rationale"], duplicate_decision["rationale"]]


def test_reapplying_same_recommendation_to_patched_document_does_not_duplicate_edge():
    model = SurveyModel.from_path(FIXTURES / "missing_fallthrough_survey.json")
    recommendations = recommend_repairs(model, validate_model(model))
    decision = approved_decision(recommendations[0].id)
    patched_once = apply_approved_recommendations(model.document, recommendations, [decision])

    patched_twice = apply_approved_recommendations(patched_once, recommendations, [decision])

    applied_edge_id = recommendations[0].patch[0]["edge"]["id"]
    applied_edges = [edge for edge in patched_twice["survey"]["dag"]["edges"] if edge["id"] == applied_edge_id]
    assert len(applied_edges) == 1


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
    assert payload["applied_count"] == 1
    assert payload["post_validation_status"] == "valid"
    assert payload["output"] == str(output_path)
    assert "missing_fallthrough" not in issue_types


def test_apply_cli_reports_no_changes_for_stale_decision(tmp_path, capsys):
    survey_path = FIXTURES / "missing_fallthrough_survey.json"
    decisions_path = tmp_path / "decisions.json"
    output_path = tmp_path / "patched.json"
    decisions_path.write_text(
        json.dumps(
            [
                {
                    "recommendation_id": "REC_STALE",
                    "decision": "approved",
                    "approver": "human",
                    "rationale": "Stale decisions should not look applied.",
                }
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["apply", str(survey_path), str(decisions_path), "--output", str(output_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["status"] == "no_changes"
    assert payload["applied_count"] == 0
    assert payload["skipped_count"] == 1
    assert payload["post_validation_status"] == "invalid"
    assert output_path.exists()
