from pathlib import Path

from survey_dag_extractor.model import SurveyModel
from survey_dag_extractor.validation import validate_model


FIXTURES = Path(__file__).parent / "fixtures"


def issue_types(path: str) -> set[str]:
    model = SurveyModel.from_path(FIXTURES / path)
    return {issue.type for issue in validate_model(model)}


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
