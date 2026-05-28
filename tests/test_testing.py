from pathlib import Path

import pytest

from survey_dag_extractor.model import SurveyModel
from survey_dag_extractor.testing import evaluate_condition, generate_coverage_tests, simulate_route


FIXTURES = Path(__file__).parent / "fixtures"


def _branchy_model() -> SurveyModel:
    return SurveyModel(
        {
            "survey": {
                "id": "branchy",
                "questions": {
                    "Q1": {"id": "Q1", "type": "radio", "text": "Branch?", "options": []},
                    "Q2": {"id": "Q2", "type": "text", "text": "Follow-up"},
                },
                "terminal_nodes": {
                    "SURVEY_COMPLETE": {"id": "SURVEY_COMPLETE", "type": "terminal", "is_final": True}
                },
                "dag": {
                    "entry_node": "Q1",
                    "terminal_nodes": ["SURVEY_COMPLETE"],
                    "edges": [
                        {
                            "id": "E_BRANCH",
                            "source": "Q1",
                            "target": "Q2",
                            "condition": ["=", "Q1", 1],
                            "priority": 1,
                            "type": "branch",
                        },
                        {
                            "id": "E_FALLTHROUGH",
                            "source": "Q1",
                            "target": "SURVEY_COMPLETE",
                            "condition": None,
                            "priority": 999,
                            "type": "fallthrough",
                        },
                        {
                            "id": "E_COMPLETE",
                            "source": "Q2",
                            "target": "SURVEY_COMPLETE",
                            "condition": None,
                            "priority": 999,
                            "type": "terminal",
                        },
                    ],
                },
            }
        }
    )


def _or_branchy_model() -> SurveyModel:
    return SurveyModel(
        {
            "survey": {
                "id": "or_branchy",
                "questions": {
                    "Q1": {"id": "Q1", "type": "radio", "text": "Branch?", "options": []},
                    "Q2": {"id": "Q2", "type": "text", "text": "Follow-up"},
                },
                "terminal_nodes": {
                    "SURVEY_COMPLETE": {"id": "SURVEY_COMPLETE", "type": "terminal", "is_final": True}
                },
                "dag": {
                    "entry_node": "Q1",
                    "terminal_nodes": ["SURVEY_COMPLETE"],
                    "edges": [
                        {
                            "id": "E_OR_BRANCH",
                            "source": "Q1",
                            "target": "Q2",
                            "condition": ["OR", ["=", "Q1", 1], ["=", "Q1", 2]],
                            "priority": 1,
                            "type": "branch",
                        },
                        {
                            "id": "E_OR_FALLTHROUGH",
                            "source": "Q1",
                            "target": "SURVEY_COMPLETE",
                            "condition": None,
                            "priority": 999,
                            "type": "fallthrough",
                        },
                        {
                            "id": "E_OR_COMPLETE",
                            "source": "Q2",
                            "target": "SURVEY_COMPLETE",
                            "condition": None,
                            "priority": 999,
                            "type": "terminal",
                        },
                    ],
                },
            }
        }
    )


def _priority_short_circuit_model() -> SurveyModel:
    return SurveyModel(
        {
            "survey": {
                "id": "priority_short_circuit",
                "questions": {
                    "Q1": {"id": "Q1", "type": "radio", "text": "Start", "options": []},
                    "Q2": {"id": "Q2", "type": "text", "text": "Lower-priority path"},
                },
                "terminal_nodes": {
                    "SURVEY_COMPLETE": {"id": "SURVEY_COMPLETE", "type": "terminal", "is_final": True}
                },
                "dag": {
                    "entry_node": "Q1",
                    "terminal_nodes": ["SURVEY_COMPLETE"],
                    "edges": [
                        {
                            "id": "E_TRUE",
                            "source": "Q1",
                            "target": "SURVEY_COMPLETE",
                            "condition": ["TRUE"],
                            "priority": 1,
                            "type": "terminal",
                        },
                        {
                            "id": "E_MALFORMED",
                            "source": "Q1",
                            "target": "Q2",
                            "condition": ["=", "Q1"],
                            "priority": 2,
                            "type": "branch",
                        },
                    ],
                },
            }
        }
    )


def test_evaluate_condition_supports_basic_operators():
    state = {"Q1": 1, "Q2": 3, "Q3": [2, 4]}

    assert evaluate_condition(["=", "Q1", 1], state)
    assert evaluate_condition([">", "Q2", 2], state)
    assert evaluate_condition(["contains", "Q3", 4], state)
    assert evaluate_condition(["AND", ["=", "Q1", 1], [">", "Q2", 2]], state)
    assert not evaluate_condition(["FALSE"], state)


def test_evaluate_condition_uses_canonical_in_not_in_semantics():
    state = {"STATE": 2, "CHOICES": [1, 3]}

    assert evaluate_condition(["in", "STATE", [1, 2, 3]], state)
    assert not evaluate_condition(["not_in", "STATE", [1, 2, 3]], state)
    assert evaluate_condition(["contains", "CHOICES", 3], state)


def test_evaluate_condition_unknown_operator_raises_value_error_without_operands():
    with pytest.raises(ValueError, match="Unknown condition operator: UNKNOWN"):
        evaluate_condition(["UNKNOWN"], {})


def test_evaluate_condition_list_operator_raises_value_error():
    with pytest.raises(ValueError, match="Unknown condition operator"):
        evaluate_condition([["BAD"], "Q1", 1], {"Q1": 1})


@pytest.mark.parametrize(
    ("condition", "state"),
    [
        (["NOT"], {}),
        (["=", "Q1"], {"Q1": 1}),
        ([">", "Q1", 1], {"Q1": "one"}),
    ],
)
def test_evaluate_condition_malformed_known_operators_raise_value_error(condition, state):
    with pytest.raises(ValueError):
        evaluate_condition(condition, state)


def test_simulate_route_follows_valid_minimal_path():
    model = SurveyModel.from_path(FIXTURES / "valid_minimal_survey.json")

    result = simulate_route(model, {})

    assert result["path"] == ["Q1", "Q2", "SURVEY_COMPLETE"]
    assert result["terminated"]


def test_simulate_route_short_circuits_after_first_matching_priority_edge():
    model = _priority_short_circuit_model()

    result = simulate_route(model, {})

    assert result["path"] == ["Q1", "SURVEY_COMPLETE"]
    assert result["edge_ids"] == ["E_TRUE"]
    assert result["terminated"]


def test_generate_coverage_tests_for_valid_fixture():
    model = SurveyModel.from_path(FIXTURES / "valid_minimal_survey.json")

    payload = generate_coverage_tests(model, coverage_target="edge")

    assert payload["survey_id"] == "valid_minimal"
    assert payload["coverage"]["node_percent"] == 100
    assert payload["coverage"]["edge_percent"] == 100
    assert payload["tests"][0]["expected_path"] == ["Q1", "Q2", "SURVEY_COMPLETE"]


def test_generate_coverage_tests_synthesizes_or_equality_fallthrough():
    model = _or_branchy_model()

    payload = generate_coverage_tests(model, coverage_target="edge")

    fallthrough_tests = [
        test for test in payload["tests"] if test["covered_edges"] == ["E_OR_FALLTHROUGH"]
    ]
    assert len(fallthrough_tests) == 1
    fallthrough_test = fallthrough_tests[0]
    assert fallthrough_test["responses"]["Q1"] not in {1, 2}
    assert simulate_route(model, fallthrough_test["responses"])["path"] == fallthrough_test["expected_path"]
    assert "E_OR_FALLTHROUGH" not in payload["uncovered_edges"]


def test_generate_coverage_tests_synthesizes_responses_and_counts_simulated_edges():
    model = _branchy_model()

    payload = generate_coverage_tests(model, coverage_target="edge")

    simulations = [simulate_route(model, test["responses"]) for test in payload["tests"]]
    for test, simulation in zip(payload["tests"], simulations):
        assert simulation["path"] == test["expected_path"]
        assert simulation["edge_ids"] == test["covered_edges"]

    responses_by_path = {tuple(test["expected_path"]): test["responses"] for test in payload["tests"]}
    assert responses_by_path[("Q1", "Q2", "SURVEY_COMPLETE")]["Q1"] == 1
    assert responses_by_path[("Q1", "SURVEY_COMPLETE")]["Q1"] != 1

    simulated_nodes = {node for simulation in simulations for node in simulation["path"]}
    simulated_edges = {edge_id for simulation in simulations for edge_id in simulation["edge_ids"]}
    assert payload["coverage"]["node_percent"] == round((len(simulated_nodes) / len(model.node_ids)) * 100)
    assert payload["coverage"]["edge_percent"] == round((len(simulated_edges) / len(model.edges)) * 100)
    assert payload["coverage"]["node_percent"] == 100
    assert payload["coverage"]["edge_percent"] == 100
    assert payload["uncovered_nodes"] == []


def test_node_coverage_generates_only_paths_needed_for_nodes():
    model = _branchy_model()

    payload = generate_coverage_tests(model, coverage_target="node")

    assert len(payload["tests"]) == 1
    assert payload["tests"][0]["expected_path"] == ["Q1", "Q2", "SURVEY_COMPLETE"]
    assert payload["coverage"]["node_percent"] == 100
    assert payload["coverage"]["edge_percent"] < 100
    assert payload["uncovered_nodes"] == []
    assert payload["uncovered_edges"] == ["E_FALLTHROUGH"]


def test_generate_coverage_tests_rejects_unknown_coverage_target():
    model = _branchy_model()

    with pytest.raises(ValueError, match="Unknown coverage target"):
        generate_coverage_tests(model, coverage_target="path")
