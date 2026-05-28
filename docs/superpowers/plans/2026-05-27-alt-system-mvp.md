# Alternative Survey DAG Workbench MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable version of the alternate survey DAG workbench: deterministic validation, typed issues, reports, healing recommendations, approved patch application, and basic route/test generation on canonical fixtures.

**Architecture:** Use the existing v2 canonical schema as the MVP contract and build a small Python package around it. The package loads canonical survey JSON into a focused model, validates structural and routing invariants, emits stable issue records, formats reports, proposes deterministic repairs, applies approved patches, and simulates routes for coverage tests. Extraction remains outside this MVP and is treated as a future importer.

**Tech Stack:** Python 3.11+, `jsonschema` for JSON Schema validation, `pytest` for tests, standard-library `argparse`, `dataclasses`, `json`, `pathlib`, and graph traversal implemented with small local helpers.

---

## File Structure

Repository root: `/Users/brock/Documents/GitHub/survey-dag-extractor`

Create:

- `/Users/brock/Documents/GitHub/survey-dag-extractor/pyproject.toml` - package metadata, dependencies, CLI entry point, pytest config.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/__init__.py` - public package exports.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/model.py` - canonical survey loader and graph indexes.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/issues.py` - typed validation issue and recommendation records.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/validation.py` - schema, graph, AST, reachability, cycle, dead-end, and fallthrough validation.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/reports.py` - Markdown validation report formatting.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/healing.py` - deterministic recommendations for first structural issue types.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/patching.py` - approved recommendation patch application and decision log updates.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/testing.py` - condition evaluation, route simulation, and basic coverage test generation.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/cli.py` - `survey-dag` CLI with `validate`, `heal`, `apply`, and `test` commands.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/data/extracted/.gitkeep` - preserve expected output directory.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/valid_minimal_survey.json` - valid canonical fixture.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/orphan_node_survey.json` - broken fixture for orphan detection.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/missing_fallthrough_survey.json` - broken fixture for healing.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/missing_edge_target_survey.json` - broken fixture for edge reference checks.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/cycle_survey.json` - broken fixture for cycle detection.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_package.py` - packaging and CLI smoke tests.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_model.py` - model loading/index tests.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_validation.py` - validator issue tests.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_reports.py` - Markdown report tests.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_healing.py` - recommendation and patch tests.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_testing.py` - route simulation and generated coverage tests.

Modify:

- `/Users/brock/Documents/GitHub/survey-dag-extractor/docs/CATALOGUE.md` - add this plan if not already listed and update Last Updated.
- `/Users/brock/Documents/GitHub/survey-dag-extractor/README.md` - replace non-existent quick start with MVP commands after code is implemented.

---

## Schema Decision for This MVP

Use `/schemas/canonical_survey_dag_schema.json` as the active schema for this implementation. Condition operators use the lower-case vocabulary documented for v2: `=`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not_in`, `contains`, `AND`, `OR`, `NOT`, `TRUE`, `FALSE`.

Do not promote `schema_v3/` in this plan. The v3 draft can be reconciled after the validator exists.

---

### Task 1: Package and CLI Scaffold

**Files:**

- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/pyproject.toml`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/__init__.py`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/cli.py`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_package.py`

- [ ] **Step 1: Write the package smoke tests**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_package.py`:

```python
from survey_dag_extractor import __version__
from survey_dag_extractor.cli import build_parser


def test_package_exposes_version():
    assert __version__ == "0.1.0"


def test_cli_parser_has_expected_commands():
    parser = build_parser()
    commands = parser._subparsers._group_actions[0].choices
    assert {"validate", "heal", "apply", "test"} <= set(commands)
```

- [ ] **Step 2: Run the smoke tests and verify they fail**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_package.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'survey_dag_extractor'` or `No module named pytest` if dependencies have not been installed yet.

- [ ] **Step 3: Add package metadata**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "survey-dag-extractor"
version = "0.1.0"
description = "Survey DAG validation, healing, and test automation workbench"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "jsonschema>=4.22.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0"
]

[project.scripts]
survey-dag = "survey_dag_extractor.cli:main"

[tool.setuptools.packages.find]
include = ["survey_dag_extractor*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 4: Add the package export**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/__init__.py`:

```python
"""Survey DAG validation, healing, and test automation workbench."""

__version__ = "0.1.0"
```

- [ ] **Step 5: Add the CLI parser skeleton**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/cli.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="survey-dag")
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate", help="Validate a canonical survey DAG JSON file")
    validate.add_argument("survey_path", type=Path)
    validate.add_argument("--report", type=Path)
    validate.set_defaults(func=_not_implemented)

    heal = subcommands.add_parser("heal", help="Generate deterministic repair recommendations")
    heal.add_argument("survey_path", type=Path)
    heal.add_argument("--output", type=Path)
    heal.set_defaults(func=_not_implemented)

    apply_cmd = subcommands.add_parser("apply", help="Apply approved recommendations")
    apply_cmd.add_argument("survey_path", type=Path)
    apply_cmd.add_argument("decisions_path", type=Path)
    apply_cmd.add_argument("--output", type=Path, required=True)
    apply_cmd.set_defaults(func=_not_implemented)

    test_cmd = subcommands.add_parser("test", help="Generate and simulate coverage tests")
    test_cmd.add_argument("survey_path", type=Path)
    test_cmd.add_argument("--coverage", choices=["node", "edge"], default="edge")
    test_cmd.add_argument("--output", type=Path)
    test_cmd.set_defaults(func=_not_implemented)

    return parser


def _not_implemented(args: argparse.Namespace) -> int:
    print(json.dumps({"command": args.command, "status": "not_implemented"}, indent=2))
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Install dev dependencies**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pip install -e ".[dev]"
```

Expected: package installs successfully with `jsonschema` and `pytest`.

- [ ] **Step 7: Run the package smoke tests**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_package.py -v
```

Expected: PASS with `2 passed`.

- [ ] **Step 8: Commit the scaffold**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
git add pyproject.toml survey_dag_extractor/__init__.py survey_dag_extractor/cli.py tests/test_package.py
git commit -m "chore: scaffold survey dag workbench package"
```

Expected: commit succeeds and does not stage unrelated local changes.

---

### Task 2: Canonical Fixtures

**Files:**

- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/data/extracted/.gitkeep`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/valid_minimal_survey.json`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/orphan_node_survey.json`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/missing_fallthrough_survey.json`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/missing_edge_target_survey.json`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/cycle_survey.json`

- [ ] **Step 1: Preserve the extracted output directory**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/data/extracted/.gitkeep` as an empty file.

- [ ] **Step 2: Add a valid minimal survey fixture**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/valid_minimal_survey.json`:

```json
{
  "survey": {
    "id": "valid_minimal",
    "title": "Valid Minimal Survey",
    "version": "1.0",
    "metadata": {
      "created_date": "2026-05-27T00:00:00Z",
      "source_file": "fixture",
      "extraction_method": "hand-authored",
      "extraction_date": "2026-05-27T00:00:00Z",
      "total_questions": 2,
      "total_blocks": 1,
      "estimated_duration_minutes": 1
    },
    "blocks": {
      "main": {
        "id": "main",
        "title": "Main",
        "order": 1,
        "questions": ["Q1", "Q2"],
        "description": "Minimal happy path"
      }
    },
    "questions": {
      "Q1": {
        "id": "Q1",
        "type": "radio",
        "text": "Do you want to continue?",
        "required": true,
        "options": [
          {"value": 1, "text": "Yes"},
          {"value": 2, "text": "No"}
        ]
      },
      "Q2": {
        "id": "Q2",
        "type": "number",
        "text": "How many people live here?",
        "required": true,
        "validation": {"min": 0, "max": 20}
      }
    },
    "terminal_nodes": {
      "SURVEY_COMPLETE": {
        "id": "SURVEY_COMPLETE",
        "type": "terminal",
        "text": "Thank you.",
        "is_final": true
      }
    },
    "dag": {
      "entry_node": "Q1",
      "terminal_nodes": ["SURVEY_COMPLETE"],
      "edges": [
        {
          "id": "E001",
          "source": "Q1",
          "target": "Q2",
          "condition": null,
          "condition_text": "fallthrough",
          "priority": 999,
          "type": "fallthrough"
        },
        {
          "id": "E002",
          "source": "Q2",
          "target": "SURVEY_COMPLETE",
          "condition": null,
          "condition_text": "complete",
          "priority": 999,
          "type": "terminal"
        }
      ]
    }
  }
}
```

- [ ] **Step 3: Add an orphan-node fixture**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/orphan_node_survey.json` by copying `valid_minimal_survey.json`, changing the `survey.id` to `orphan_node`, and replacing `dag.edges` with:

```json
[
  {
    "id": "E001",
    "source": "Q1",
    "target": "SURVEY_COMPLETE",
    "condition": null,
    "condition_text": "complete",
    "priority": 999,
    "type": "terminal"
  }
]
```

- [ ] **Step 4: Add a missing-fallthrough fixture**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/missing_fallthrough_survey.json` by copying `valid_minimal_survey.json`, changing the `survey.id` to `missing_fallthrough`, and replacing the edge from `Q1` to `Q2` with:

```json
{
  "id": "E001",
  "source": "Q1",
  "target": "Q2",
  "condition": ["=", "Q1", 1],
  "condition_text": "Q1 = 1",
  "priority": 1,
  "type": "branch"
}
```

Keep the `Q2 -> SURVEY_COMPLETE` terminal edge unchanged.

- [ ] **Step 5: Add a missing-edge-target fixture**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/missing_edge_target_survey.json` by copying `valid_minimal_survey.json`, changing the `survey.id` to `missing_edge_target`, and changing edge `E001.target` from `Q2` to `MISSING_Q`.

- [ ] **Step 6: Add a cycle fixture**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/fixtures/cycle_survey.json` by copying `valid_minimal_survey.json`, changing the `survey.id` to `cycle_survey`, and replacing `dag.edges` with:

```json
[
  {
    "id": "E001",
    "source": "Q1",
    "target": "Q2",
    "condition": null,
    "condition_text": "fallthrough",
    "priority": 999,
    "type": "fallthrough"
  },
  {
    "id": "E002",
    "source": "Q2",
    "target": "Q1",
    "condition": null,
    "condition_text": "loop",
    "priority": 999,
    "type": "fallthrough"
  }
]
```

- [ ] **Step 7: Verify fixture JSON parses**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
for file in tests/fixtures/*.json; do python3 -m json.tool "$file" >/dev/null; done
```

Expected: command exits 0.

- [ ] **Step 8: Commit fixtures**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
git add data/extracted/.gitkeep tests/fixtures
git commit -m "test: add canonical survey validation fixtures"
```

Expected: commit succeeds.

---

### Task 3: Model and Issue Types

**Files:**

- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/issues.py`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/model.py`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_model.py`

- [ ] **Step 1: Write model tests**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_model.py`:

```python
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
```

- [ ] **Step 2: Run model tests and verify they fail**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_model.py -v
```

Expected: FAIL with `ModuleNotFoundError` or missing `SurveyModel`.

- [ ] **Step 3: Add issue and recommendation records**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/issues.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["error", "warning", "info"]
IssueStatus = Literal["open", "recommended", "approved", "rejected", "applied", "verified", "waived"]


@dataclass(frozen=True)
class ValidationIssue:
    id: str
    severity: Severity
    type: str
    message: str
    node_id: str | None = None
    edge_id: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    recommendation_ids: list[str] = field(default_factory=list)
    status: IssueStatus = "open"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "type": self.type,
            "node_id": self.node_id,
            "edge_id": self.edge_id,
            "message": self.message,
            "evidence": self.evidence,
            "recommendation_ids": self.recommendation_ids,
            "status": self.status,
        }


@dataclass(frozen=True)
class Recommendation:
    id: str
    issue_id: str
    type: str
    confidence: Literal["low", "medium", "high"]
    rationale: str
    patch: list[dict[str, Any]]
    requires_approval: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "issue_id": self.issue_id,
            "type": self.type,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "patch": self.patch,
            "requires_approval": self.requires_approval,
        }
```

- [ ] **Step 4: Add the survey model**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/model.py`:

```python
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


class SurveyModel:
    def __init__(self, document: dict[str, Any]):
        self.document = document
        self.survey = document["survey"]
        self.questions = self.survey.get("questions", {})
        self.terminals = self.survey.get("terminal_nodes", {})
        self.dag = self.survey.get("dag", {})
        self.edges = list(self.dag.get("edges", []))
        self._outgoing = self._index_edges("source")
        self._incoming = self._index_edges("target")

    @classmethod
    def from_path(cls, path: Path | str) -> "SurveyModel":
        with Path(path).open("r", encoding="utf-8") as file:
            return cls(json.load(file))

    @property
    def survey_id(self) -> str:
        return self.survey["id"]

    @property
    def entry_node(self) -> str | None:
        return self.dag.get("entry_node")

    @property
    def terminal_ids(self) -> list[str]:
        return list(self.dag.get("terminal_nodes", []))

    @property
    def node_ids(self) -> set[str]:
        return set(self.questions) | set(self.terminals)

    def node_exists(self, node_id: str) -> bool:
        return node_id in self.node_ids

    def is_terminal(self, node_id: str) -> bool:
        return node_id in self.terminals

    def outgoing_edges(self, node_id: str) -> list[dict[str, Any]]:
        return sorted(self._outgoing.get(node_id, []), key=lambda edge: (edge.get("priority", 999), edge.get("id", "")))

    def incoming_edges(self, node_id: str) -> list[dict[str, Any]]:
        return sorted(self._incoming.get(node_id, []), key=lambda edge: edge.get("id", ""))

    def block_order(self) -> list[str]:
        ordered_blocks = sorted(self.survey.get("blocks", {}).values(), key=lambda block: block.get("order", 999))
        ordered: list[str] = []
        for block in ordered_blocks:
            ordered.extend(qid for qid in block.get("questions", []) if qid in self.questions)
        for qid in self.questions:
            if qid not in ordered:
                ordered.append(qid)
        return ordered

    def next_question_after(self, node_id: str) -> str | None:
        ordered = self.block_order()
        if node_id not in ordered:
            return None
        index = ordered.index(node_id)
        if index + 1 >= len(ordered):
            return None
        return ordered[index + 1]

    def _index_edges(self, key: str) -> dict[str, list[dict[str, Any]]]:
        index: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in self.edges:
            if key in edge:
                index[edge[key]].append(edge)
        return dict(index)

    @staticmethod
    def condition_variables(condition: Any) -> set[str]:
        if condition is None or not isinstance(condition, list) or not condition:
            return set()
        op = condition[0]
        if op in {"=", "!=", ">", "<", ">=", "<=", "in", "not_in", "contains"} and len(condition) >= 2:
            return {condition[1]} if isinstance(condition[1], str) else set()
        variables: set[str] = set()
        for item in condition[1:]:
            variables |= SurveyModel.condition_variables(item)
        return variables
```

- [ ] **Step 5: Run model tests**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_model.py -v
```

Expected: PASS with `2 passed`.

- [ ] **Step 6: Commit model layer**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
git add survey_dag_extractor/issues.py survey_dag_extractor/model.py tests/test_model.py
git commit -m "feat: add canonical survey model and issue records"
```

Expected: commit succeeds.

---

### Task 4: Deterministic Validator

**Files:**

- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/validation.py`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_validation.py`

- [ ] **Step 1: Write validator tests**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_validation.py`:

```python
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
```

- [ ] **Step 2: Run validator tests and verify they fail**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_validation.py -v
```

Expected: FAIL with missing `survey_dag_extractor.validation`.

- [ ] **Step 3: Add validation implementation**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/validation.py`:

```python
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from survey_dag_extractor.issues import ValidationIssue
from survey_dag_extractor.model import SurveyModel

KNOWN_OPERATORS = {"=", "!=", ">", "<", ">=", "<=", "in", "not_in", "contains", "AND", "OR", "NOT", "TRUE", "FALSE"}


def validate_model(model: SurveyModel, schema_path: Path | None = None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(_schema_issues(model, schema_path))
    issues.extend(_reference_issues(model))
    issues.extend(_condition_issues(model))
    issues.extend(_priority_issues(model))
    issues.extend(_routing_issues(model))
    return _renumber(issues)


def _schema_issues(model: SurveyModel, schema_path: Path | None) -> list[ValidationIssue]:
    schema_file = schema_path or Path(__file__).resolve().parents[1] / "schemas" / "canonical_survey_dag_schema.json"
    with schema_file.open("r", encoding="utf-8") as file:
        schema = json.load(file)
    validator = Draft7Validator(schema)
    issues = []
    for error in sorted(validator.iter_errors(model.document), key=lambda err: list(err.path)):
        issues.append(
            ValidationIssue(
                id="ISSUE_PENDING",
                severity="error",
                type="schema_invalid",
                message=error.message,
                evidence={"path": list(error.path)},
            )
        )
    return issues


def _reference_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not model.entry_node:
        issues.append(ValidationIssue("ISSUE_PENDING", "error", "missing_entry_node", "DAG has no entry_node."))
    elif not model.node_exists(model.entry_node):
        issues.append(
            ValidationIssue(
                "ISSUE_PENDING",
                "error",
                "missing_entry_node",
                f"Entry node {model.entry_node} does not exist.",
                node_id=model.entry_node,
            )
        )
    for terminal_id in model.terminal_ids:
        if terminal_id not in model.terminals:
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "missing_terminal_node",
                    f"Terminal node {terminal_id} is listed in dag.terminal_nodes but is not defined.",
                    node_id=terminal_id,
                )
            )
    for edge in model.edges:
        if not model.node_exists(edge["source"]):
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "missing_edge_source",
                    f"Edge {edge['id']} source {edge['source']} does not exist.",
                    node_id=edge["source"],
                    edge_id=edge["id"],
                )
            )
        if not model.node_exists(edge["target"]):
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "missing_edge_target",
                    f"Edge {edge['id']} target {edge['target']} does not exist.",
                    node_id=edge["target"],
                    edge_id=edge["id"],
                )
            )
    return issues


def _condition_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for edge in model.edges:
        condition = edge.get("condition")
        for op in _condition_operators(condition):
            if op == "UNPARSED":
                issues.append(
                    ValidationIssue(
                        "ISSUE_PENDING",
                        "error",
                        "unparsed_condition",
                        f"Edge {edge['id']} has an unparsed condition.",
                        edge_id=edge["id"],
                        evidence={"condition": condition},
                    )
                )
            elif op not in KNOWN_OPERATORS:
                issues.append(
                    ValidationIssue(
                        "ISSUE_PENDING",
                        "error",
                        "unknown_condition_operator",
                        f"Edge {edge['id']} uses unknown condition operator {op}.",
                        edge_id=edge["id"],
                        evidence={"operator": op, "condition": condition},
                    )
                )
        for variable in model.condition_variables(condition):
            if variable not in model.questions:
                issues.append(
                    ValidationIssue(
                        "ISSUE_PENDING",
                        "error",
                        "missing_condition_variable",
                        f"Edge {edge['id']} condition references missing question {variable}.",
                        node_id=variable,
                        edge_id=edge["id"],
                    )
                )
    return issues


def _condition_operators(condition: Any) -> list[str]:
    if condition is None or not isinstance(condition, list) or not condition:
        return []
    operators = [condition[0]] if isinstance(condition[0], str) else []
    for item in condition[1:]:
        operators.extend(_condition_operators(item))
    return operators


def _priority_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    by_source: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    for edge in model.edges:
        by_source[edge["source"]][edge["priority"]].append(edge["id"])
    for source, priorities in by_source.items():
        for priority, edge_ids in priorities.items():
            if len(edge_ids) > 1:
                issues.append(
                    ValidationIssue(
                        "ISSUE_PENDING",
                        "error",
                        "duplicate_priority",
                        f"Source {source} has duplicate priority {priority}.",
                        node_id=source,
                        evidence={"priority": priority, "edge_ids": edge_ids},
                    )
                )
    return issues


def _routing_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(_missing_outgoing_issues(model))
    issues.extend(_reachability_issues(model))
    issues.extend(_cycle_issues(model))
    issues.extend(_dead_end_issues(model))
    issues.extend(_fallthrough_issues(model))
    return issues


def _missing_outgoing_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues = []
    for node_id in model.questions:
        if not model.outgoing_edges(node_id):
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "missing_outgoing_edge",
                    f"Question {node_id} has no outgoing edge.",
                    node_id=node_id,
                )
            )
    return issues


def _reachable_nodes(model: SurveyModel) -> set[str]:
    if not model.entry_node or not model.node_exists(model.entry_node):
        return set()
    visited: set[str] = set()
    stack = [model.entry_node]
    while stack:
        node_id = stack.pop()
        if node_id in visited:
            continue
        visited.add(node_id)
        for edge in model.outgoing_edges(node_id):
            if model.node_exists(edge["target"]):
                stack.append(edge["target"])
    return visited


def _reachability_issues(model: SurveyModel) -> list[ValidationIssue]:
    reachable = _reachable_nodes(model)
    issues = []
    for node_id in sorted(model.node_ids - reachable):
        if node_id == model.entry_node:
            continue
        issues.append(
            ValidationIssue(
                "ISSUE_PENDING",
                "error",
                "orphan_node",
                f"{node_id} is not reachable from the entry node.",
                node_id=node_id,
                evidence={"entry_node": model.entry_node, "incoming_edges": [edge["id"] for edge in model.incoming_edges(node_id)]},
            )
        )
    return issues


def _cycle_issues(model: SurveyModel) -> list[ValidationIssue]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: list[list[str]] = []

    def visit(node_id: str, path: list[str]) -> None:
        if node_id in visiting:
            start = path.index(node_id)
            cycles.append(path[start:] + [node_id])
            return
        if node_id in visited or model.is_terminal(node_id):
            return
        visiting.add(node_id)
        for edge in model.outgoing_edges(node_id):
            if model.node_exists(edge["target"]):
                visit(edge["target"], path + [edge["target"]])
        visiting.remove(node_id)
        visited.add(node_id)

    if model.entry_node and model.node_exists(model.entry_node):
        visit(model.entry_node, [model.entry_node])

    return [
        ValidationIssue(
            "ISSUE_PENDING",
            "error",
            "cycle_detected",
            "Graph contains a directed cycle.",
            node_id=cycle[0],
            evidence={"cycle": cycle},
        )
        for cycle in cycles
    ]


def _dead_end_issues(model: SurveyModel) -> list[ValidationIssue]:
    terminal_ids = set(model.terminal_ids)
    memo: dict[str, bool] = {}

    def reaches_terminal(node_id: str, path: set[str]) -> bool:
        if node_id in terminal_ids:
            return True
        if node_id in memo:
            return memo[node_id]
        if node_id in path:
            memo[node_id] = False
            return False
        outgoing = [edge for edge in model.outgoing_edges(node_id) if model.node_exists(edge["target"])]
        if not outgoing:
            memo[node_id] = False
            return False
        memo[node_id] = any(reaches_terminal(edge["target"], path | {node_id}) for edge in outgoing)
        return memo[node_id]

    issues = []
    for node_id in sorted(_reachable_nodes(model)):
        if node_id not in terminal_ids and not reaches_terminal(node_id, set()):
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "dead_end",
                    f"{node_id} has no path to a terminal node.",
                    node_id=node_id,
                )
            )
    return issues


def _fallthrough_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues = []
    for source in sorted({edge["source"] for edge in model.edges}):
        outgoing = model.outgoing_edges(source)
        has_branch = any(edge.get("type") == "branch" for edge in outgoing)
        has_fallthrough = any(edge.get("type") == "fallthrough" and edge.get("condition") is None for edge in outgoing)
        if has_branch and not has_fallthrough:
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "missing_fallthrough",
                    f"Branching source {source} has no fallthrough edge.",
                    node_id=source,
                    evidence={"outgoing_edges": [edge["id"] for edge in outgoing]},
                )
            )
    return issues


def _renumber(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    return [
        ValidationIssue(
            id=f"ISSUE_{index:04d}",
            severity=issue.severity,
            type=issue.type,
            message=issue.message,
            node_id=issue.node_id,
            edge_id=issue.edge_id,
            evidence=issue.evidence,
            recommendation_ids=issue.recommendation_ids,
            status=issue.status,
        )
        for index, issue in enumerate(issues, start=1)
    ]
```

- [ ] **Step 4: Run validator tests**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_validation.py -v
```

Expected: PASS with `5 passed`.

- [ ] **Step 5: Run package, model, and validator tests together**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_package.py tests/test_model.py tests/test_validation.py -v
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit validator**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
git add survey_dag_extractor/validation.py tests/test_validation.py
git commit -m "feat: add deterministic survey dag validator"
```

Expected: commit succeeds.

---

### Task 5: Markdown Reports and Validate CLI

**Files:**

- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/reports.py`
- Modify: `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/cli.py`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_reports.py`

- [ ] **Step 1: Write report and CLI tests**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_reports.py`:

```python
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
```

- [ ] **Step 2: Run report tests and verify they fail**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_reports.py -v
```

Expected: FAIL with missing `survey_dag_extractor.reports` or CLI still returning `not_implemented`.

- [ ] **Step 3: Add Markdown reporting**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/reports.py`:

```python
from __future__ import annotations

from survey_dag_extractor.issues import ValidationIssue
from survey_dag_extractor.model import SurveyModel


def format_markdown_report(model: SurveyModel, issues: list[ValidationIssue]) -> str:
    lines = [
        f"# Validation Report: {model.survey_id}",
        "",
        f"- Entry node: `{model.entry_node}`",
        f"- Questions: {len(model.questions)}",
        f"- Terminal nodes: {len(model.terminals)}",
        f"- Edges: {len(model.edges)}",
        f"- Issues: {len(issues)}",
        "",
    ]
    if not issues:
        lines.extend(["## Result", "", "No validation issues found.", ""])
        return "\n".join(lines)

    lines.extend(["## Issues", ""])
    for issue in issues:
        lines.extend(
            [
                f"### {issue.id}: {issue.type}",
                "",
                f"- Severity: `{issue.severity}`",
                f"- Status: `{issue.status}`",
                f"- Node: `{issue.node_id}`" if issue.node_id else "- Node: none",
                f"- Edge: `{issue.edge_id}`" if issue.edge_id else "- Edge: none",
                f"- Message: {issue.message}",
                "",
            ]
        )
    return "\n".join(lines)
```

- [ ] **Step 4: Replace CLI skeleton command handlers**

Modify `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/cli.py` to this content:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from survey_dag_extractor.model import SurveyModel
from survey_dag_extractor.reports import format_markdown_report
from survey_dag_extractor.validation import validate_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="survey-dag")
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate", help="Validate a canonical survey DAG JSON file")
    validate.add_argument("survey_path", type=Path)
    validate.add_argument("--report", type=Path)
    validate.set_defaults(func=_validate)

    heal = subcommands.add_parser("heal", help="Generate deterministic repair recommendations")
    heal.add_argument("survey_path", type=Path)
    heal.add_argument("--output", type=Path)
    heal.set_defaults(func=_not_implemented)

    apply_cmd = subcommands.add_parser("apply", help="Apply approved recommendations")
    apply_cmd.add_argument("survey_path", type=Path)
    apply_cmd.add_argument("decisions_path", type=Path)
    apply_cmd.add_argument("--output", type=Path, required=True)
    apply_cmd.set_defaults(func=_not_implemented)

    test_cmd = subcommands.add_parser("test", help="Generate and simulate coverage tests")
    test_cmd.add_argument("survey_path", type=Path)
    test_cmd.add_argument("--coverage", choices=["node", "edge"], default="edge")
    test_cmd.add_argument("--output", type=Path)
    test_cmd.set_defaults(func=_not_implemented)

    return parser


def _validate(args: argparse.Namespace) -> int:
    model = SurveyModel.from_path(args.survey_path)
    issues = validate_model(model)
    if args.report:
        args.report.write_text(format_markdown_report(model, issues), encoding="utf-8")
    payload = {
        "survey_id": model.survey_id,
        "status": "valid" if not issues else "invalid",
        "issue_count": len(issues),
        "issues": [issue.to_dict() for issue in issues],
    }
    print(json.dumps(payload, indent=2))
    return 0 if not issues else 1


def _not_implemented(args: argparse.Namespace) -> int:
    print(json.dumps({"command": args.command, "status": "not_implemented"}, indent=2))
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run report tests**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_reports.py -v
```

Expected: PASS with `3 passed`.

- [ ] **Step 6: Commit reports and validate CLI**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
git add survey_dag_extractor/reports.py survey_dag_extractor/cli.py tests/test_reports.py
git commit -m "feat: add validation reports and validate cli"
```

Expected: commit succeeds.

---

### Task 6: Healing Recommendations and Approved Patches

**Files:**

- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/healing.py`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/patching.py`
- Modify: `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/cli.py`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_healing.py`

- [ ] **Step 1: Write healing and patch tests**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_healing.py`:

```python
from pathlib import Path

from survey_dag_extractor.healing import recommend_repairs
from survey_dag_extractor.model import SurveyModel
from survey_dag_extractor.patching import apply_approved_recommendations
from survey_dag_extractor.validation import validate_model


FIXTURES = Path(__file__).parent / "fixtures"


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
            "rationale": "Default path should continue to Q2 for this fixture."
        }
    ]

    patched = apply_approved_recommendations(model.document, recommendations, decisions)
    patched_model = SurveyModel(patched)
    issue_types = {issue.type for issue in validate_model(patched_model)}

    assert "missing_fallthrough" not in issue_types
```

- [ ] **Step 2: Run healing tests and verify they fail**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_healing.py -v
```

Expected: FAIL with missing `survey_dag_extractor.healing`.

- [ ] **Step 3: Add deterministic healing**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/healing.py`:

```python
from __future__ import annotations

from survey_dag_extractor.issues import Recommendation, ValidationIssue
from survey_dag_extractor.model import SurveyModel


def recommend_repairs(model: SurveyModel, issues: list[ValidationIssue]) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    for issue in issues:
        if issue.type == "missing_fallthrough" and issue.node_id:
            recommendation = _recommend_fallthrough(model, issue, len(recommendations) + 1)
            if recommendation:
                recommendations.append(recommendation)
    return recommendations


def _recommend_fallthrough(model: SurveyModel, issue: ValidationIssue, index: int) -> Recommendation | None:
    source = issue.node_id
    target = model.next_question_after(source)
    if target is None:
        terminal_ids = model.terminal_ids
        target = terminal_ids[0] if terminal_ids else None
    if target is None:
        return None
    edge_id = _next_edge_id(model, index)
    return Recommendation(
        id=f"REC_{index:04d}",
        issue_id=issue.id,
        type="add_fallthrough_edge",
        confidence="medium",
        rationale=f"Branching source {source} has no default path; use the next question or terminal as a human-reviewable fallthrough.",
        patch=[
            {
                "op": "add_edge",
                "edge": {
                    "id": edge_id,
                    "source": source,
                    "target": target,
                    "condition": None,
                    "condition_text": "fallthrough",
                    "priority": 999,
                    "type": "fallthrough",
                },
            }
        ],
    )


def _next_edge_id(model: SurveyModel, index: int) -> str:
    existing = {edge["id"] for edge in model.edges}
    candidate = f"E_AUTO_{index:04d}"
    while candidate in existing:
        index += 1
        candidate = f"E_AUTO_{index:04d}"
    return candidate
```

- [ ] **Step 4: Add patch application**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/patching.py`:

```python
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from survey_dag_extractor.issues import Recommendation


def apply_approved_recommendations(
    document: dict[str, Any],
    recommendations: list[Recommendation],
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    patched = copy.deepcopy(document)
    recommendation_by_id = {recommendation.id: recommendation for recommendation in recommendations}
    for decision in decisions:
        if decision.get("decision") != "approved":
            continue
        recommendation = recommendation_by_id[decision["recommendation_id"]]
        for operation in recommendation.patch:
            _apply_operation(patched, operation)
        _append_decision(patched, recommendation, decision)
    return patched


def _apply_operation(document: dict[str, Any], operation: dict[str, Any]) -> None:
    if operation["op"] == "add_edge":
        document["survey"]["dag"]["edges"].append(operation["edge"])
        return
    raise ValueError(f"Unsupported patch operation: {operation['op']}")


def _append_decision(document: dict[str, Any], recommendation: Recommendation, decision: dict[str, Any]) -> None:
    metadata = document["survey"].setdefault("metadata", {})
    decision_log = metadata.setdefault("decision_log", [])
    decision_log.append(
        {
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "approver": decision["approver"],
            "issue_id": recommendation.issue_id,
            "recommendation_id": recommendation.id,
            "decision": decision["decision"],
            "rationale": decision["rationale"],
        }
    )
```

- [ ] **Step 5: Run healing tests**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_healing.py -v
```

Expected: PASS with `2 passed`.

- [ ] **Step 6: Add heal and apply CLI commands**

Modify `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/cli.py`:

- Import `recommend_repairs` from `survey_dag_extractor.healing`.
- Import `apply_approved_recommendations` from `survey_dag_extractor.patching`.
- Change the `heal` subcommand handler from `_not_implemented` to `_heal`.
- Change the `apply` subcommand handler from `_not_implemented` to `_apply`.
- Add these functions:

```python
def _heal(args: argparse.Namespace) -> int:
    model = SurveyModel.from_path(args.survey_path)
    issues = validate_model(model)
    recommendations = recommend_repairs(model, issues)
    payload = {
        "survey_id": model.survey_id,
        "recommendation_count": len(recommendations),
        "recommendations": [recommendation.to_dict() for recommendation in recommendations],
    }
    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


def _apply(args: argparse.Namespace) -> int:
    model = SurveyModel.from_path(args.survey_path)
    issues = validate_model(model)
    recommendations = recommend_repairs(model, issues)
    with args.decisions_path.open("r", encoding="utf-8") as file:
        decisions = json.load(file)
    patched = apply_approved_recommendations(model.document, recommendations, decisions)
    args.output.write_text(json.dumps(patched, indent=2), encoding="utf-8")
    print(json.dumps({"status": "applied", "output": str(args.output)}, indent=2))
    return 0
```

- [ ] **Step 7: Run all tests so far**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_package.py tests/test_model.py tests/test_validation.py tests/test_reports.py tests/test_healing.py -v
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit healing and patching**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
git add survey_dag_extractor/healing.py survey_dag_extractor/patching.py survey_dag_extractor/cli.py tests/test_healing.py
git commit -m "feat: add deterministic healing and approved patching"
```

Expected: commit succeeds.

---

### Task 7: Route Simulation and Coverage Test Generation

**Files:**

- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/testing.py`
- Modify: `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/cli.py`
- Create: `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_testing.py`

- [ ] **Step 1: Write route simulation tests**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/tests/test_testing.py`:

```python
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
```

- [ ] **Step 2: Run testing tests and verify they fail**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_testing.py -v
```

Expected: FAIL with missing `survey_dag_extractor.testing`.

- [ ] **Step 3: Add route simulation and coverage generation**

Create `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/testing.py`:

```python
from __future__ import annotations

from typing import Any

from survey_dag_extractor.model import SurveyModel


def evaluate_condition(condition: Any, state: dict[str, Any]) -> bool:
    if condition is None:
        return True
    if not isinstance(condition, list) or not condition:
        return bool(condition)
    op = condition[0]
    if op == "TRUE":
        return True
    if op == "FALSE":
        return False
    if op == "AND":
        return all(evaluate_condition(part, state) for part in condition[1:])
    if op == "OR":
        return any(evaluate_condition(part, state) for part in condition[1:])
    if op == "NOT":
        return not evaluate_condition(condition[1], state)
    left = state.get(condition[1])
    right = condition[2]
    if op == "=":
        return left == right
    if op == "!=":
        return left != right
    if op == ">":
        return left is not None and left > right
    if op == "<":
        return left is not None and left < right
    if op == ">=":
        return left is not None and left >= right
    if op == "<=":
        return left is not None and left <= right
    if op in {"contains", "in"}:
        return right in left if isinstance(left, list) else left == right
    if op == "not_in":
        return right not in left if isinstance(left, list) else left != right
    raise ValueError(f"Unknown condition operator: {op}")


def simulate_route(model: SurveyModel, responses: dict[str, Any], max_steps: int = 1000) -> dict[str, Any]:
    if not model.entry_node:
        return {"path": [], "edge_ids": [], "terminated": False, "reason": "missing_entry_node"}
    current = model.entry_node
    path = [current]
    edge_ids: list[str] = []
    for _ in range(max_steps):
        if model.is_terminal(current):
            return {"path": path, "edge_ids": edge_ids, "terminated": True, "reason": "terminal"}
        matching = [edge for edge in model.outgoing_edges(current) if evaluate_condition(edge.get("condition"), responses)]
        if not matching:
            return {"path": path, "edge_ids": edge_ids, "terminated": False, "reason": "no_matching_edge"}
        edge = matching[0]
        edge_ids.append(edge["id"])
        current = edge["target"]
        path.append(current)
    return {"path": path, "edge_ids": edge_ids, "terminated": False, "reason": "max_steps"}


def generate_coverage_tests(model: SurveyModel, coverage_target: str = "edge") -> dict[str, Any]:
    paths = _enumerate_paths(model)
    tests = []
    covered_nodes: set[str] = set()
    covered_edges: set[str] = set()
    for index, path_info in enumerate(paths, start=1):
        covered_nodes.update(path_info["path"])
        covered_edges.update(path_info["edge_ids"])
        tests.append(
            {
                "id": f"TEST_{index:04d}",
                "responses": {},
                "expected_path": path_info["path"],
                "covered_edges": path_info["edge_ids"],
            }
        )
    total_nodes = len(model.node_ids)
    total_edges = len(model.edges)
    return {
        "survey_id": model.survey_id,
        "coverage_target": coverage_target,
        "tests": tests,
        "coverage": {
            "node_percent": _percent(len(covered_nodes), total_nodes),
            "edge_percent": _percent(len(covered_edges), total_edges),
        },
    }


def _enumerate_paths(model: SurveyModel) -> list[dict[str, Any]]:
    if not model.entry_node:
        return []
    paths: list[dict[str, Any]] = []

    def walk(node_id: str, path: list[str], edge_ids: list[str]) -> None:
        if model.is_terminal(node_id):
            paths.append({"path": path, "edge_ids": edge_ids})
            return
        outgoing = model.outgoing_edges(node_id)
        if not outgoing:
            paths.append({"path": path, "edge_ids": edge_ids})
            return
        for edge in outgoing:
            if edge["target"] in path:
                paths.append({"path": path + [edge["target"]], "edge_ids": edge_ids + [edge["id"]]})
            else:
                walk(edge["target"], path + [edge["target"]], edge_ids + [edge["id"]])

    walk(model.entry_node, [model.entry_node], [])
    return paths


def _percent(numerator: int, denominator: int) -> int:
    if denominator == 0:
        return 100
    return round((numerator / denominator) * 100)
```

- [ ] **Step 4: Add test CLI command**

Modify `/Users/brock/Documents/GitHub/survey-dag-extractor/survey_dag_extractor/cli.py`:

- Import `generate_coverage_tests` from `survey_dag_extractor.testing`.
- Change the `test` subcommand handler from `_not_implemented` to `_test`.
- Add this function:

```python
def _test(args: argparse.Namespace) -> int:
    model = SurveyModel.from_path(args.survey_path)
    payload = generate_coverage_tests(model, args.coverage)
    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0
```

- [ ] **Step 5: Run route simulation tests**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest tests/test_testing.py -v
```

Expected: PASS with `3 passed`.

- [ ] **Step 6: Run the full test suite**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit testing support**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
git add survey_dag_extractor/testing.py survey_dag_extractor/cli.py tests/test_testing.py
git commit -m "feat: add route simulation and coverage test generation"
```

Expected: commit succeeds.

---

### Task 8: README and Catalogue Alignment

**Files:**

- Modify: `/Users/brock/Documents/GitHub/survey-dag-extractor/README.md`
- Modify: `/Users/brock/Documents/GitHub/survey-dag-extractor/docs/CATALOGUE.md`

- [ ] **Step 1: Replace README quick start with runnable MVP commands**

Modify `/Users/brock/Documents/GitHub/survey-dag-extractor/README.md` so the Quick Start section contains:

````markdown
## Quick Start

Install the workbench in editable mode:

```bash
python3 -m pip install -e ".[dev]"
```

Validate a canonical survey DAG:

```bash
survey-dag validate tests/fixtures/valid_minimal_survey.json
```

Generate a Markdown validation report:

```bash
survey-dag validate tests/fixtures/orphan_node_survey.json --report data/extracted/orphan_validation.md
```

Generate repair recommendations:

```bash
survey-dag heal tests/fixtures/missing_fallthrough_survey.json --output data/extracted/recommendations.json
```

Generate coverage tests:

```bash
survey-dag test tests/fixtures/valid_minimal_survey.json --coverage edge --output data/extracted/coverage_tests.json
```
````

Also add a short status note near the top:

```markdown
> Current status: the repo is building a validation, healing, and test automation workbench first. PDF extraction is planned as a draft-input importer after the canonical DAG validator is stable.
```

- [ ] **Step 2: Update the catalogue**

Modify `/Users/brock/Documents/GitHub/survey-dag-extractor/docs/CATALOGUE.md`:

- Set `Last Updated` to the implementation date.
- Keep `/docs/ALT_SYSTEM_DESIGN.md` listed as Draft.
- Add `/docs/superpowers/plans/2026-05-27-alt-system-mvp.md` as Draft with description `MVP implementation plan for the alternate survey DAG workbench`.
- Change README status from `Needs update` to `Active` once the runnable commands are in place.

- [ ] **Step 3: Run documentation sanity checks**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m json.tool schemas/canonical_survey_dag_schema.json >/dev/null
rg -n "SchemaCompliantDAGExtractor|validate_schema.py|analyze_coverage.py|your-org" README.md
```

Expected: first command exits 0. Second command exits 1 because those stale README references are gone.

- [ ] **Step 4: Run the full test suite after docs changes**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit documentation alignment**

Run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
git add README.md docs/CATALOGUE.md docs/ALT_SYSTEM_DESIGN.md docs/superpowers/plans/2026-05-27-alt-system-mvp.md
git commit -m "docs: align project docs with alternate workbench mvp"
```

Expected: commit succeeds.

---

## Final Verification

After all tasks are complete, run:

```bash
cd /Users/brock/Documents/GitHub/survey-dag-extractor
python3 -m pytest -v
survey-dag validate tests/fixtures/valid_minimal_survey.json
survey-dag validate tests/fixtures/orphan_node_survey.json --report data/extracted/orphan_validation.md
survey-dag heal tests/fixtures/missing_fallthrough_survey.json --output data/extracted/recommendations.json
survey-dag test tests/fixtures/valid_minimal_survey.json --coverage edge --output data/extracted/coverage_tests.json
python3 -m json.tool data/extracted/recommendations.json >/dev/null
python3 -m json.tool data/extracted/coverage_tests.json >/dev/null
```

Expected:

- `pytest` exits 0.
- Valid fixture validation exits 0 and reports `status: valid`.
- Orphan fixture validation exits 1 and writes a Markdown report naming `orphan_node`.
- Healing writes valid recommendation JSON.
- Test generation writes valid coverage JSON with 100 percent node and edge coverage for the minimal fixture.

---

## Self-Review Notes

Spec coverage:

- Canonical model: Task 3.
- Validator and typed issues: Task 4.
- Markdown report: Task 5.
- Healing recommendations: Task 6.
- Human approval patch path: Task 6.
- Route simulation and coverage tests: Task 7.
- Extraction as draft importer: explicitly deferred by schema decision and README alignment.

Type consistency:

- `ValidationIssue` and `Recommendation` are defined once in `issues.py`.
- `SurveyModel` is used by validation, reports, healing, and testing.
- CLI commands call the same functions tested directly by unit tests.

Scope:

- This plan implements the MVP from `/docs/ALT_SYSTEM_DESIGN.md`.
- It does not implement PDF extraction, LLM-assisted import, UI review, or export formats.
