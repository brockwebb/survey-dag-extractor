from survey_dag_extractor import __version__
from survey_dag_extractor.cli import build_parser


def test_package_exposes_version():
    assert __version__ == "0.1.0"


def test_cli_parser_has_expected_commands():
    parser = build_parser()
    commands = parser._subparsers._group_actions[0].choices
    assert {"validate", "heal", "apply", "test"} <= set(commands)
