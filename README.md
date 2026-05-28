# Survey DAG Extractor

Survey DAG validation, healing, and test automation workbench for canonical survey routing graphs.

> Current status: the repo is building a validation, healing, and test automation workbench first. PDF extraction is planned as a draft-input importer after the canonical DAG validator is stable.

## Overview

This project turns canonical survey DAG JSON into something teams can validate, repair with human approval, and exercise with generated route coverage tests. The current MVP focuses on the graph workbench: schema checks, routing checks, Markdown validation reports, deterministic repair recommendations, approved patch application, and coverage test generation.

PDF extraction remains part of the roadmap, but it is intentionally downstream of the canonical DAG validator. For now, the most reliable input is a JSON file that follows `/schemas/canonical_survey_dag_schema.json`.

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

## Workbench Capabilities

**Validation**
- Validates canonical JSON against the project schema
- Checks graph references, entry nodes, terminal nodes, reachability, cycles, priorities, dead ends, and missing fallthrough paths
- Emits JSON summaries and optional Markdown reports

**Healing**
- Generates deterministic repair recommendations for supported structural issues
- Supports missing fallthrough and orphan reconnect recommendations
- Keeps repairs human-reviewable before they are applied
- Supports approved recommendation application through the `survey-dag apply` command

**Coverage Testing**
- Enumerates survey routes through the DAG
- Synthesizes response sets for supported edge conditions
- Reports node and edge coverage plus paths that could not be verified

## Canonical Input

The workbench expects a canonical JSON document with survey metadata, DAG nodes, edges, terminal nodes, and edge conditions. See `/schemas/canonical_survey_dag_schema.json` for the formal schema and `/docs/CANONICAL_SURVEY_DAG_SCHEMA.md` for the human-readable schema guide.

Fixture surveys in `/tests/fixtures/` provide compact examples for valid and invalid routing graphs.

## CLI Commands

```bash
survey-dag validate <survey.json> [--report report.md]
survey-dag heal <survey.json> [--output recommendations.json]
survey-dag apply <survey.json> <decisions.json> --output patched.json
survey-dag test <survey.json> [--coverage node|edge] [--output coverage_tests.json]
```

## Validation Workflow

Human validation is mandatory for repair decisions:

1. Run `survey-dag validate` to identify schema and routing issues.
2. Run `survey-dag heal` to generate recommendations for supported issue types.
3. Review recommendations and record approved decisions.
4. Run `survey-dag apply` to produce a patched survey JSON.
5. Re-run validation and generate coverage tests.

## Project Layout

| Path | Purpose |
|------|---------|
| `/survey_dag_extractor/` | Python package and CLI implementation |
| `/schemas/` | Canonical survey DAG schema |
| `/docs/` | Project documentation and design notes |
| `/tests/fixtures/` | Minimal canonical survey fixtures |
| `/data/` | Source survey files |
| `/data/extracted/` | Generated validation reports, recommendations, and test outputs |

## Development

Install development dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

Run the test suite:

```bash
python3 -m pytest -v
```

Validate the schema file is well-formed JSON:

```bash
python3 -m json.tool schemas/canonical_survey_dag_schema.json >/dev/null
```

## License

MIT License - See LICENSE file for details.
