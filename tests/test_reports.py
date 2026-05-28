import json
from pathlib import Path

from survey_dag_extractor.cli import main
from survey_dag_extractor.model import SurveyModel
from survey_dag_extractor.reports import format_markdown_report
from survey_dag_extractor.validation import validate_model


FIXTURES = Path(__file__).parent / "fixtures"


def _write_survey_without_id(tmp_path: Path) -> Path:
    payload = json.loads((FIXTURES / "valid_minimal_survey.json").read_text(encoding="utf-8"))
    del payload["survey"]["id"]
    survey_path = tmp_path / "missing_survey_id.json"
    survey_path.write_text(json.dumps(payload), encoding="utf-8")
    return survey_path


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


def test_validate_cli_prints_invalid_json_when_survey_id_missing(tmp_path, capsys):
    survey_path = _write_survey_without_id(tmp_path)

    exit_code = main(["validate", str(survey_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["survey_id"] == "<unknown>"
    assert payload["status"] == "invalid"
    assert payload["issue_count"] > 0


def test_validate_cli_writes_report_when_survey_id_missing(tmp_path):
    survey_path = _write_survey_without_id(tmp_path)
    report_path = tmp_path / "validation.md"

    exit_code = main(["validate", str(survey_path), "--report", str(report_path)])

    assert exit_code == 1
    report = report_path.read_text(encoding="utf-8")
    assert "# Validation Report: <unknown>" in report
    assert "schema_invalid" in report


def test_heal_cli_handles_missing_survey_id(tmp_path, capsys):
    survey_path = _write_survey_without_id(tmp_path)

    exit_code = main(["heal", str(survey_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["survey_id"] == "<unknown>"
    assert "recommendations" in payload


def test_test_cli_handles_missing_survey_id(tmp_path, capsys):
    survey_path = _write_survey_without_id(tmp_path)

    exit_code = main(["test", str(survey_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["survey_id"] == "<unknown>"
    assert "tests" in payload


def test_cli_reports_invalid_json_without_traceback(tmp_path, capsys):
    survey_path = tmp_path / "broken.json"
    survey_path.write_text("{not json", encoding="utf-8")

    exit_code = main(["validate", str(survey_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 2
    assert payload["status"] == "error"
    assert payload["error"]["type"] == "invalid_json"
