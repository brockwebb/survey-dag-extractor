# Project Evaluation

**Date:** 2026-05-23
**Status:** Active
**Scope:** Repository structure, documentation, schema assets, conversion helper, and lightweight verification.

---

## Executive Summary

The project has a strong product direction and a cleaner schema-first restart than the archived legacy work, but the current tracked repository is still mostly specification, not an executable extractor. The biggest risk is source-of-truth drift: the README advertises a package and commands that do not exist, the active v2 schema and `schema_v3/` disagree, and the one conversion script produces output that is not valid against the active schema.

Recommended immediate focus:

1. Pick one canonical schema version and make every doc/tool target it.
2. Add a minimal installable Python package, dependency file, and smoke tests.
3. Implement semantic DAG validation before adding more extraction logic.
4. Decide whether `restart/` and `handoffs/` are local-only references or repository artifacts.

---

## What Is Present

Tracked repository contents are intentionally small:

- `README.md`
- `docs/REQUIREMENTS.md`
- `docs/CANONICAL_SURVEY_DAG_SCHEMA.md`
- `docs/CATALOGUE.md`
- `schemas/canonical_survey_dag_schema.json`
- `schema_v3/CANONICAL_SCHEMA_V3.md`
- `schema_v3/convert_v2_to_v3.py`
- `data/HTOPS_2502_Questionnaire_ENGLISH.pdf`
- `AGENTS.md`, `.gitignore`, `LICENSE`

The workspace also contains ignored local reference folders:

- `restart/`
- `handoffs/`
- `.claude/`

This means much of the historical context exists locally but is not part of the tracked repo.

---

## Strengths

- The requirements are unusually clear about the real domain problem: convert paper survey instruments into a canonical DAG that can be validated, tested, and exported.
- The v2 schema correctly moves toward explicit routing edges with priorities, instead of scattering routing across questions and options.
- The handoff captures the previous failure mode well: condition strings and lost routing priority caused the prior system to fail at execution time.
- The repo has useful process rules in `AGENTS.md`, especially schema-first changes, human validation, and catalogue maintenance.
- The project is small enough right now to correct drift before adding more code.

---

## Priority Findings

### 1. The README describes software that is not in the repo

`README.md` references `survey_dag_extractor.SchemaCompliantDAGExtractor`, `survey_analyzer.PathAnalyzer`, `survey_visualizer.D3NetworkGraph`, `validate_schema.py`, `analyze_coverage.py`, and a `tests/` directory. None of those exist in the tracked repository.

Impact: a new contributor will follow the quick start and immediately fail. It also hides the real current state, which is a schema restart plus one prototype conversion script.

Recommendation: rewrite the README as a current-state README:

- Mark extractor, analyzer, visualizer, and exports as roadmap items.
- Add exact commands that work today.
- Point users to `schemas/canonical_survey_dag_schema.json`, `docs/REQUIREMENTS.md`, and `schema_v3/convert_v2_to_v3.py`.

### 2. Active schema v2 and `schema_v3/` are inconsistent

The active catalogue says `/schemas/canonical_survey_dag_schema.json` is the active v2 schema. Separately, `schema_v3/` defines a v3 shape and converter.

Important mismatches:

- Active v2 requires top-level `survey.terminal_nodes`; v3 converter omits it.
- Active v2 requires `dag.entry_node` and `dag.terminal_nodes`; v3 converter omits both.
- Active v2 edge types are `branch`, `fallthrough`, `terminal`; v3 docs say `branch`, `fallthrough`, `terminate`.
- Active v2 docs use lower-case set operators such as `in` and `not_in`; v3 docs and converter use `IN` and `NOT_IN`.
- `schema_v3/convert_v2_to_v3.py` outputs `"version": "3.0"`, but there is no formal v3 JSON Schema under `/schemas/`.

Impact: generated v3 output has no single authoritative validator. Downstream tooling will either reject it or silently depend on undocumented behavior.

Recommendation: either promote v3 into `/schemas/canonical_survey_dag_schema.json` and update the canonical docs/catalogue, or move `schema_v3/` under an explicit draft/experimental status and make the converter target v2.

### 3. The conversion helper is useful but still a prototype

`schema_v3/convert_v2_to_v3.py` has a good seed parser for simple expressions, but it is not yet safe as pipeline infrastructure.

Observed limitations:

- Unparseable expressions become `["UNPARSED", expr]`, but the schema is permissive enough that this shape can pass structural validation.
- Boolean parsing is intentionally shallow and does not handle nested parentheses or precedence beyond simple two-part `AND`/`OR`.
- Conditional questions get branch edges, but the script explicitly leaves complex fallthrough/skip-path handling for manual review.
- It tracks `has_incoming` but does not use it to report orphans.
- It does not create terminal edges or active-schema DAG metadata.
- There are no tests around the parser, edge generation, or invalid input cases.

Recommendation: keep the script, but treat it as a migration prototype until tests and semantic validation exist.

### 4. Validation requirements are specified but not implemented

`docs/REQUIREMENTS.md` calls for orphan detection, dead-end detection, cycle detection, impossible-condition detection, validation reports, and test generation. The current tracked repo has no validator module, no test generation module, no extracted sample JSON, and no `data/extracted/` directory.

Impact: the main project promise cannot yet be demonstrated from the clean tree.

Recommendation: build the validator before the extractor. A hand-authored tiny fixture plus a semantic validator will lock down the contract and prevent another extraction attempt from producing unusable graph data.

### 5. Dependency and test setup is missing

There is no `pyproject.toml`, `requirements.txt`, or tracked environment spec. Local checks show `pytest`, `jsonschema`, `langextract`, and `networkx` are not available in the default Python environment.

Impact: there is no reproducible way to install, test, or run the project from a fresh clone.

Recommendation: add a small `pyproject.toml` with runtime and dev dependencies. Start with `jsonschema`, `pytest`, and whichever PDF extraction dependency is selected. Add optional extras later for LLM extraction and visualization.

### 6. Important referenced folders are ignored and untracked

`.gitignore` ignores `restart/`, `handoffs/`, and `cc_scripts/`, while `docs/CATALOGUE.md` references files inside `restart/` and `handoffs/`.

Impact: the local workspace has context that a fresh clone will not have. The catalogue may point to missing files for another contributor or automation runner.

Recommendation: decide explicitly:

- If these are repository references, stop ignoring them and track the curated subset.
- If they are local-only archives, move their catalogue entries to a "local workspace references" section and do not rely on them for core project continuity.

---

## Suggested Next Roadmap

### Phase 0: Repo Hygiene

- Update README to describe the current clean restart honestly.
- Add `pyproject.toml` and a minimal package skeleton.
- Create `data/extracted/.gitkeep` if extracted outputs are expected there.
- Decide tracked vs local-only status for `restart/` and `handoffs/`.

### Phase 1: Canonical Schema Decision

- Choose v2 or v3 as the one active schema.
- Move the active schema to `/schemas/canonical_survey_dag_schema.json`.
- Update `/docs/CANONICAL_SURVEY_DAG_SCHEMA.md`.
- Update `/docs/CATALOGUE.md`.
- Add examples that validate against the active schema.

### Phase 2: Validator First

Implement a validator that checks:

- JSON Schema validity.
- Every edge source and target exists.
- Every referenced condition variable exists.
- Every non-terminal node has outgoing edges.
- Every non-entry node is reachable.
- Branch priorities are unique per source.
- Every branching node has a fallthrough.
- The graph is acyclic.
- Every path can reach a terminal.
- `UNPARSED` or unknown condition operators are hard validation failures.

### Phase 3: Minimal Demonstrable Pipeline

- Add one tiny hand-authored fixture survey.
- Add one extracted HTOPS sample only after human validation.
- Add commands for validation report generation.
- Then wire in PDF/LLM extraction.

### Phase 4: Analysis, Test Generation, and Exports

- Implement path coverage after validator semantics are stable.
- Add metrics once graph correctness is reliable.
- Add Word/OMB/QSF exports after the canonical JSON proves stable.

---

## Verification Performed

Passing checks:

```bash
python3 -m json.tool schemas/canonical_survey_dag_schema.json >/dev/null
python3 -m py_compile schema_v3/convert_v2_to_v3.py
```

Parser smoke cases passed for:

- `always_show`
- `D11 > 0`
- `EMP1 == 2`
- `D11 > 0 AND EMP1 = 2`
- `D12 includes 1`

Expected or informative failures:

```bash
python3 -m pytest tests/
```

Result: failed because `pytest` is not installed in the default environment, and there is no tracked root `tests/` directory.

```bash
python3 schema_v3/convert_v2_to_v3.py
```

Result: exits with usage message when no input/output args are provided, as expected.

Converter compatibility smoke check:

- A minimal converted v3 survey was missing active-schema-required `survey.terminal_nodes`, `dag.entry_node`, and `dag.terminal_nodes`.

Environment notes:

- `jsonschema`, `langextract`, and `networkx` were not installed in the default Python environment.
- `pdfinfo` and `pdftotext` were not available on PATH.

---

## Bottom Line

The project is at a good reset point. The domain model is pointed in the right direction, and the previous failure has been correctly diagnosed. The next best move is not more extraction; it is to stabilize the canonical schema and validator so that any future extraction output can be proven usable.
