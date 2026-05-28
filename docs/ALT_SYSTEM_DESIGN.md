# Alternative System Design

**Date:** 2026-05-27
**Status:** Draft
**Purpose:** Reframe the project around survey DAG validation, healing, editing, and test automation before attempting full PDF-to-DAG extraction.

---

## Product Thesis

The most valuable system is not a fully automated survey PDF extractor. The best core system is a survey DAG workbench that can accept an imperfect draft survey graph, prove what is wrong with it, help a human repair it, and generate tests that demonstrate the finished graph is complete.

Extraction remains useful, but it should be treated as a proposal generator. It can draft questions, edges, and conditions with source evidence and confidence scores. The canonical DAG is only trusted after validation and human approval.

This design changes the project center of gravity:

```text
Old center: PDF -> extractor -> canonical DAG
New center: draft DAG -> validate -> heal -> approve -> test -> canonical DAG
```

---

## Goals

1. Make survey graph correctness measurable.
2. Detect missing, unreachable, cyclic, ambiguous, or unparseable routing.
3. Provide human-reviewable repair recommendations.
4. Preserve all repair decisions in an audit trail.
5. Generate test paths that prove node and edge coverage.
6. Support multiple draft inputs, including hand-authored JSON, legacy exports, future PDF extraction, and external survey platforms.

---

## Non-Goals

1. Do not make fully automated extraction the first milestone.
2. Do not auto-apply graph repairs without human approval.
3. Do not build real-time survey hosting.
4. Do not require a graphical UI for the first working version.
5. Do not optimize for every export format until the canonical graph and validator are stable.

---

## Core Workflow

```text
Draft survey artifact
  -> normalize to canonical survey DAG
  -> run structural and semantic validation
  -> produce issue list with precise node/edge references
  -> generate repair recommendations
  -> human approves, rejects, or edits recommendations
  -> apply approved patches
  -> re-run validation
  -> generate coverage tests
  -> produce final validation and test report
```

The workflow is iterative. A survey is not complete until validation passes and the generated coverage suite reaches the configured coverage target.

---

## System Components

### 1. Canonical Survey DAG Model

The model is the stable in-memory representation used by all tools. It should map directly to `/schemas/canonical_survey_dag_schema.json`.

Responsibilities:

- Load survey JSON.
- Preserve question content, blocks, terminal nodes, DAG edges, conditions, priorities, and metadata.
- Provide lookup helpers for nodes, edges, incoming edges, outgoing edges, and condition variables.
- Keep edits as explicit patch operations rather than opaque rewrites.

Inputs:

- Canonical JSON.
- Normalized drafts from importers.

Outputs:

- Canonical JSON.
- JSON Patch-style edit operations.
- Validation and test reports.

### 2. Validator

The validator is the first major build target. It must be deterministic, fast, and independent of LLMs.

Required checks:

- JSON Schema validity.
- Exactly one configured entry node.
- Entry node exists.
- All terminal nodes exist.
- Every edge source exists.
- Every edge target exists.
- Every condition variable references an existing question.
- Every condition AST uses known operators.
- No `UNPARSED`, placeholder, or unknown condition operators.
- Edge priorities are unique for each source.
- Every non-terminal node has at least one outgoing edge.
- Every non-entry node is reachable from the entry node.
- Every path eventually reaches a terminal node.
- Graph contains no cycles.
- Every branching source has a fallthrough edge unless marked intentionally exhaustive.

Output:

- A machine-readable validation report.
- A human-readable Markdown report.
- A list of typed issues.

### 3. Issue Model

Every detected problem should be represented as a typed issue with stable fields.

Suggested fields:

```json
{
  "id": "ISSUE_0001",
  "severity": "error",
  "type": "orphan_node",
  "node_id": "FD2",
  "edge_id": null,
  "message": "FD2 is not reachable from the entry node.",
  "evidence": {
    "entry_node": "ADDRESS_CONFIRM",
    "incoming_edges": []
  },
  "recommendation_ids": ["REC_0001"],
  "status": "open"
}
```

Severity levels:

- `error`: blocks canonical approval.
- `warning`: allows approval only with explicit human signoff.
- `info`: does not block approval.

Initial issue types:

- `schema_invalid`
- `missing_entry_node`
- `missing_terminal_node`
- `missing_edge_source`
- `missing_edge_target`
- `unknown_condition_operator`
- `unparsed_condition`
- `missing_condition_variable`
- `duplicate_priority`
- `missing_outgoing_edge`
- `orphan_node`
- `dead_end`
- `cycle_detected`
- `missing_fallthrough`
- `unreachable_terminal`

### 4. Healing and Recommendation Engine

The healing engine proposes fixes, but it does not decide truth. Human approval remains mandatory.

Responsibilities:

- Generate one or more repair recommendations per issue.
- Explain why each recommendation is plausible.
- Mark recommendations with confidence and required human review.
- Convert approved recommendations into patch operations.
- Log rejected recommendations with rationale.

Example recommendation:

```json
{
  "id": "REC_0001",
  "issue_id": "ISSUE_0001",
  "type": "add_edge",
  "confidence": "medium",
  "rationale": "FD2 appears after D11 in block order and has a universe condition depending on D11.",
  "patch": [
    {
      "op": "add_edge",
      "edge": {
        "id": "E_AUTO_0001",
        "source": "D11",
        "target": "FD2",
        "condition": [">", "D11", 0],
        "condition_text": "D11 > 0",
        "priority": 1,
        "type": "branch"
      }
    }
  ],
  "requires_approval": true
}
```

Recommendation sources:

- Graph structure.
- Block/question order.
- Existing condition references.
- Source evidence from draft importers.
- Optional LLM assistance for explanation and candidate routing, never for final approval.

### 5. Human Approval Workflow

The approval workflow turns graph repair into an auditable process.

Decision states:

- `open`: issue exists and has not been resolved.
- `recommended`: one or more recommendations exist.
- `approved`: a human approved a recommendation.
- `rejected`: a human rejected a recommendation.
- `applied`: an approved patch was applied.
- `verified`: validation confirms the issue is resolved.
- `waived`: a human accepts the issue with rationale.

Decision log fields:

```json
{
  "timestamp": "2026-05-27T00:00:00Z",
  "approver": "human",
  "issue_id": "ISSUE_0001",
  "recommendation_id": "REC_0001",
  "decision": "approved",
  "rationale": "Matches source questionnaire skip instruction on page 12."
}
```

The system should refuse to mark a survey canonical if any `error` issue remains open, rejected without another fix, or applied but not verified.

### 6. Editor Operations

The editor layer should be operation-based. It can start as CLI commands and later power a UI.

Core operations:

- Add, update, or delete a question.
- Add, update, or delete an edge.
- Add or update terminal nodes.
- Edit condition AST and condition text together.
- Reorder edge priorities from a source node.
- Move a question between blocks.
- Mark a branch source as intentionally exhaustive.
- Apply an approved recommendation.
- Re-run validation after every edit batch.

Each operation should produce a before/after diff and append to the decision log when it resolves a validation issue.

### 7. Test Generator

The test generator runs after the graph is structurally valid enough to simulate.

Responsibilities:

- Generate minimal or near-minimal paths for node coverage.
- Generate minimal or near-minimal paths for edge coverage.
- Produce synthetic response states that satisfy each routed path.
- Simulate each path through the DAG.
- Compare expected path to simulated path.
- Report uncovered nodes, uncovered edges, impossible edges, and ambiguous route choices.

Initial output format:

```json
{
  "survey_id": "htops_2025_02",
  "coverage_target": "edge",
  "tests": [
    {
      "id": "TEST_0001",
      "responses": {
        "D11": 0
      },
      "expected_path": ["ADDRESS_CONFIRM", "D11", "FD1", "SURVEY_COMPLETE"],
      "covered_edges": ["E001", "E004", "E099"]
    }
  ],
  "coverage": {
    "node_percent": 100,
    "edge_percent": 100
  }
}
```

### 8. Importers and Extractors

Importers are adapters into the workbench. They produce draft canonical DAGs and evidence, not trusted final output.

Initial importers:

- Canonical JSON loader.
- Legacy v2/v3 converter once schema version is resolved.
- Hand-authored fixture loader for tests.

Future importers:

- PDF text/block extraction.
- LLM-assisted routing proposal extraction.
- Qualtrics QSF import.
- OMB CSV import.

Importer output should include confidence and source evidence where available:

```json
{
  "source_file": "HTOPS_2502_Questionnaire_ENGLISH.pdf",
  "source_locator": {
    "page": 12,
    "text_anchor": "If D11 > 0, continue to FD2"
  },
  "confidence": 0.82
}
```

---

## Proposed Repository Shape

The first implementation can stay small:

```text
survey_dag_extractor/
  __init__.py
  model.py
  validation.py
  issues.py
  healing.py
  patching.py
  testing.py
  reports.py
  cli.py

tests/
  fixtures/
    valid_minimal_survey.json
    orphan_node_survey.json
    missing_fallthrough_survey.json
    cycle_survey.json
  test_validation.py
  test_healing.py
  test_testing.py
```

Suggested command surface:

```bash
survey-dag validate data/extracted/htops_2025_02.json
survey-dag heal data/extracted/htops_2025_02.json --report data/extracted/htops_2025_02_validation.md
survey-dag apply data/extracted/htops_2025_02.json decisions.json
survey-dag test data/extracted/htops_2025_02.json --coverage edge
```

---

## MVP Definition

The MVP should prove the alternate system on small fixtures before HTOPS.

MVP must include:

1. A minimal canonical survey fixture that passes validation.
2. At least four broken fixtures:
   - orphan node
   - missing fallthrough
   - missing edge target
   - cycle
3. Validator that emits typed issues for each broken fixture.
4. Markdown validation report.
5. At least one deterministic healing recommendation.
6. Human approval record format.
7. Patch application for approved recommendations.
8. Re-validation showing the issue is resolved.
9. Test path generation for a valid fixture.

MVP does not need:

- PDF extraction.
- LLM calls.
- Browser UI.
- Full HTOPS extraction.
- Export to Word, OMB CSV, or QSF.

---

## Acceptance Criteria

The alternate system is ready for HTOPS-scale work when:

1. `survey-dag validate` completes in under 5 seconds for a 500-node synthetic survey.
2. Broken fixtures produce stable issue IDs, types, severities, and node/edge references.
3. No `error` issue can be silently waived without decision log rationale.
4. Approved repairs are applied as explicit patch operations.
5. Re-validation marks repaired issues as verified.
6. Test generation reaches 100 percent node coverage and reports edge coverage.
7. Generated test paths simulate deterministically through the DAG.
8. A validation report can be reviewed without reading raw JSON.

---

## Relationship to Existing Requirements

This design keeps the original vision but changes the build order.

Original requirement groups map as follows:

- FR1 Extraction Pipeline becomes an importer/draft-generation layer.
- FR2 Validation Engine becomes the first core milestone.
- FR3 Test Generation becomes the second core milestone.
- FR4 Metrics follows after graph simulation is stable.
- FR5 Export follows after canonical validation and testing are trustworthy.

The key change is that extraction accuracy is no longer the first proof point. The first proof point is whether the system can make correctness visible and repairable.

---

## Recommended Build Order

1. Resolve the active schema version and condition operator vocabulary.
2. Add package/test scaffolding.
3. Implement model loading and graph indexes.
4. Implement validator and typed issue model.
5. Add broken and valid fixtures.
6. Generate Markdown validation reports.
7. Implement deterministic healing recommendations for common structural issues.
8. Add approval log and patch application.
9. Implement route simulation.
10. Implement node and edge coverage test generation.
11. Revisit extraction as a draft importer.

---

## Open Design Decisions

These decisions should be made before implementation planning:

1. Whether v2 or v3 becomes the active canonical schema.
2. Whether condition operators are lower-case (`in`, `not_in`) or upper-case (`IN`, `NOT_IN`).
3. Whether fallthrough is required for every branching source or only when branches are not declared exhaustive.
4. Whether decision logs live inside the survey JSON or next to it as a companion artifact.
5. Whether the first user interface is CLI-only or a small local review app.

---

## Conclusion

The alternate system makes the reliable part of the workflow the foundation. A survey can be incomplete, partially extracted, or manually drafted and still be useful because the system can show exactly what is wrong, recommend repairs, preserve human decisions, and generate tests once the graph is sound.

This is a better foundation for survey work than betting first on perfect extraction.
