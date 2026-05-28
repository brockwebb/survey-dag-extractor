from pathlib import Path

from survey_dag_extractor.model import SurveyModel
from survey_dag_extractor.testing import evaluate_condition, generate_coverage_tests, simulate_route


FIXTURES = Path(__file__).parent / "fixtures"


def test_evaluate_condition_supports_basic_operators():
    state = {"Q1": 1, "Q2": 3, "Q3": [2, 4]}

    assert evaluate_condition(["=", "Q1", 1], state)
    assert evaluate_condition([">", "Q2", 2], state)
    assert evaluate_condition(["contains", "Q3", 4], state)
    assert evaluate_condition(["AND", ["=", "Q1", 1], [">", "Q2", 2]], state)
    assert not evaluate_condition(["FALSE"], state)


def test_simulate_route_follows_valid_minimal_path():
    model = SurveyModel.from_path(FIXTURES / "valid_minimal_survey.json")

    result = simulate_route(model, {})

    assert result["path"] == ["Q1", "Q2", "SURVEY_COMPLETE"]
    assert result["terminated"]


def test_generate_coverage_tests_for_valid_fixture():
    model = SurveyModel.from_path(FIXTURES / "valid_minimal_survey.json")

    payload = generate_coverage_tests(model, coverage_target="edge")

    assert payload["survey_id"] == "valid_minimal"
    assert payload["coverage"]["node_percent"] == 100
    assert payload["coverage"]["edge_percent"] == 100
    assert payload["tests"][0]["expected_path"] == ["Q1", "Q2", "SURVEY_COMPLETE"]
