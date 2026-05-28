import json
from pathlib import Path

from survey_dag_extractor.cli import main
from survey_dag_extractor.model import SurveyModel
from survey_dag_extractor.reports import format_markdown_report
from survey_dag_extractor.validation import validate_model


FIXTURES = Path(__file__).parent / "fixtures"


def test_markdown_report_names_issue_type():
    model = SurveyModel.from_path(FIXTURES / "orphan_node_survey.json")
    report = format_markdown_report(model, validate_model(model))

    assert "# Validation Report: orphan_node" in report
    assert "orphan_node" in report
    assert "Q2 is not reachable" in report


def test_validate_cli_writes_report(tmp_path):
    report_path = tmp_path / "validation.md"

    exit_code = main(["validate", str(FIXTURES / "orphan_node_survey.json"), "--report", str(report_path)])

    assert exit_code == 1
    assert "orphan_node" in report_path.read_text(encoding="utf-8")


def test_validate_cli_prints_json_for_valid_fixture(capsys):
    exit_code = main(["validate", str(FIXTURES / "valid_minimal_survey.json")])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["issue_count"] == 0
    assert payload["status"] == "valid"
