from pathlib import Path

from survey_dag_extractor.model import SurveyModel


FIXTURES = Path(__file__).parent / "fixtures"


def test_model_loads_valid_fixture_and_indexes_nodes():
    model = SurveyModel.from_path(FIXTURES / "valid_minimal_survey.json")

    assert model.survey_id == "valid_minimal"
    assert model.entry_node == "Q1"
    assert model.node_exists("Q1")
    assert model.node_exists("SURVEY_COMPLETE")
    assert model.is_terminal("SURVEY_COMPLETE")
    assert [edge["id"] for edge in model.outgoing_edges("Q1")] == ["E001"]
    assert [edge["id"] for edge in model.incoming_edges("Q2")] == ["E001"]


def test_condition_variables_extracts_question_references():
    condition = ["AND", [">", "Q2", 0], ["=", "Q1", 1]]

    assert SurveyModel.condition_variables(condition) == {"Q1", "Q2"}
