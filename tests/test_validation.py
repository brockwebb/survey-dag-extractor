import json
from copy import deepcopy
from pathlib import Path

import pytest

from survey_dag_extractor.model import SurveyModel
from survey_dag_extractor.validation import validate_model


FIXTURES = Path(__file__).parent / "fixtures"


def issue_types(path: str) -> set[str]:
    model = SurveyModel.from_path(FIXTURES / path)
    return {issue.type for issue in validate_model(model)}


def load_fixture(path: str) -> dict:
    with (FIXTURES / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def issue_types_from_document(document: dict) -> set[str]:
    return {issue.type for issue in validate_model(SurveyModel(document))}


def issues_from_document(document: dict):
    return validate_model(SurveyModel(document))


def test_valid_minimal_survey_has_no_issues():
    assert issue_types("valid_minimal_survey.json") == set()


def test_orphan_node_is_detected():
    assert "orphan_node" in issue_types("orphan_node_survey.json")


def test_missing_edge_target_is_detected():
    assert "missing_edge_target" in issue_types("missing_edge_target_survey.json")


def test_missing_fallthrough_is_detected():
    assert "missing_fallthrough" in issue_types("missing_fallthrough_survey.json")


def test_cycle_is_detected():
    assert "cycle_detected" in issue_types("cycle_survey.json")


@pytest.mark.parametrize("missing_field", ["source", "target", "priority"])
def test_schema_invalid_edges_do_not_crash_validator(missing_field):
    document = load_fixture("valid_minimal_survey.json")
    del document["survey"]["dag"]["edges"][0][missing_field]

    types = issue_types_from_document(document)

    assert "schema_invalid" in types


def test_cycle_is_detected_in_unreachable_component():
    document = load_fixture("valid_minimal_survey.json")
    q3 = deepcopy(document["survey"]["questions"]["Q1"])
    q3["id"] = "Q3"
    q4 = deepcopy(document["survey"]["questions"]["Q2"])
    q4["id"] = "Q4"
    document["survey"]["questions"]["Q3"] = q3
    document["survey"]["questions"]["Q4"] = q4
    document["survey"]["metadata"]["total_questions"] = 4
    document["survey"]["dag"]["edges"].extend(
        [
            {
                "id": "E003",
                "source": "Q3",
                "target": "Q4",
                "condition": None,
                "condition_text": "orphan cycle",
                "priority": 999,
                "type": "fallthrough",
            },
            {
                "id": "E004",
                "source": "Q4",
                "target": "Q3",
                "condition": None,
                "condition_text": "orphan cycle",
                "priority": 999,
                "type": "fallthrough",
            },
        ]
    )

    types = issue_types_from_document(document)

    assert "orphan_node" in types
    assert "cycle_detected" in types


def test_in_condition_literal_list_is_not_treated_as_nested_expression():
    document = load_fixture("valid_minimal_survey.json")
    document["survey"]["dag"]["edges"][0] = {
        "id": "E001",
        "source": "Q1",
        "target": "Q2",
        "condition": ["in", "Q1", ["A", "B"]],
        "condition_text": "Q1 is in a literal list",
        "priority": 1,
        "type": "branch",
    }
    document["survey"]["dag"]["edges"].insert(
        1,
        {
            "id": "E001_FALLTHROUGH",
            "source": "Q1",
            "target": "Q2",
            "condition": None,
            "condition_text": "fallthrough",
            "priority": 999,
            "type": "fallthrough",
        },
    )

    types = issue_types_from_document(document)

    assert "unknown_condition_operator" not in types


def test_non_string_condition_operator_is_reported():
    document = load_fixture("valid_minimal_survey.json")
    document["survey"]["dag"]["edges"][0] = {
        "id": "E001",
        "source": "Q1",
        "target": "Q2",
        "condition": [123, "Q1", 1],
        "condition_text": "malformed operator",
        "priority": 1,
        "type": "branch",
    }
    document["survey"]["dag"]["edges"].insert(
        1,
        {
            "id": "E001_FALLTHROUGH",
            "source": "Q1",
            "target": "Q2",
            "condition": None,
            "condition_text": "fallthrough",
            "priority": 999,
            "type": "fallthrough",
        },
    )

    types = issue_types_from_document(document)

    assert "unknown_condition_operator" in types


def test_cycle_with_exit_path_to_terminal_is_not_a_dead_end():
    document = load_fixture("valid_minimal_survey.json")
    document["survey"]["dag"]["edges"] = [
        {
            "id": "E001",
            "source": "Q1",
            "target": "Q2",
            "condition": None,
            "condition_text": "fallthrough",
            "priority": 1,
            "type": "fallthrough",
        },
        {
            "id": "E002",
            "source": "Q1",
            "target": "SURVEY_COMPLETE",
            "condition": None,
            "condition_text": "complete",
            "priority": 2,
            "type": "terminal",
        },
        {
            "id": "E003",
            "source": "Q2",
            "target": "Q1",
            "condition": None,
            "condition_text": "loop",
            "priority": 1,
            "type": "fallthrough",
        },
    ]

    dead_end_nodes = {issue.node_id for issue in issues_from_document(document) if issue.type == "dead_end"}

    assert "Q2" not in dead_end_nodes
