import json
from copy import deepcopy
from pathlib import Path

import pytest

from survey_dag_extractor.model import SurveyModel


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(path: str) -> dict:
    with (FIXTURES / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_model_loads_valid_fixture_and_indexes_nodes():
    model = SurveyModel.from_path(FIXTURES / "valid_minimal_survey.json")

    assert model.survey_id == "valid_minimal"
    assert model.entry_node == "Q1"
    assert model.node_exists("Q1")
    assert model.node_exists("SURVEY_COMPLETE")
    assert model.is_terminal("SURVEY_COMPLETE")
    assert [edge["id"] for edge in model.outgoing_edges("Q1")] == ["E001"]
    assert [edge["id"] for edge in model.incoming_edges("Q2")] == ["E001"]


def test_model_uses_unknown_survey_id_when_missing():
    document = load_fixture("valid_minimal_survey.json")
    del document["survey"]["id"]

    model = SurveyModel(document)

    assert model.survey_id == "<unknown>"


def test_condition_variables_extracts_question_references():
    condition = ["AND", [">", "Q2", 0], ["=", "Q1", 1]]

    assert SurveyModel.condition_variables(condition) == {"Q1", "Q2"}


@pytest.mark.parametrize("edge_item", [None, 123, "source", []])
def test_model_ignores_non_dict_edges_when_indexing(edge_item):
    document = load_fixture("valid_minimal_survey.json")
    document["survey"]["dag"]["edges"][0] = edge_item

    model = SurveyModel(document)

    assert model.edges[0] == edge_item
    assert model.outgoing_edges("Q1") == []
    assert [edge["id"] for edge in model.incoming_edges("SURVEY_COMPLETE")] == ["E002"]


@pytest.mark.parametrize("field", ["source", "target"])
def test_model_ignores_non_string_edge_endpoints_when_indexing(field):
    document = load_fixture("valid_minimal_survey.json")
    document["survey"]["dag"]["edges"][0][field] = []

    model = SurveyModel(document)

    assert model.outgoing_edges("Q1") == ([] if field == "source" else [document["survey"]["dag"]["edges"][0]])
    assert model.incoming_edges("Q2") == ([] if field == "target" else [document["survey"]["dag"]["edges"][0]])


def test_model_sorts_malformed_priorities_deterministically():
    document = load_fixture("valid_minimal_survey.json")
    malformed_priority_edge = deepcopy(document["survey"]["dag"]["edges"][0])
    malformed_priority_edge["id"] = "E000_BAD_PRIORITY"
    malformed_priority_edge["priority"] = []
    document["survey"]["dag"]["edges"].insert(0, malformed_priority_edge)

    model = SurveyModel(document)

    assert [edge["id"] for edge in model.outgoing_edges("Q1")] == ["E000_BAD_PRIORITY", "E001"]


@pytest.mark.parametrize("edges", [None, 123, "edges", {}])
def test_model_tolerates_malformed_dag_edges_container(edges):
    document = load_fixture("valid_minimal_survey.json")
    document["survey"]["dag"]["edges"] = edges

    model = SurveyModel(document)

    assert model.edges == []
    assert model.outgoing_edges("Q1") == []
    assert model.incoming_edges("Q2") == []


@pytest.mark.parametrize("terminal_nodes", [None, 123, [[]], [{"id": "x"}]])
def test_model_tolerates_malformed_dag_terminal_nodes(terminal_nodes):
    document = load_fixture("valid_minimal_survey.json")
    document["survey"]["dag"]["terminal_nodes"] = terminal_nodes

    model = SurveyModel(document)

    assert model.terminal_ids == []
