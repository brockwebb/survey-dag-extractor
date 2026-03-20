# Survey DAG Extractor - Requirements

**Version:** 2.0 (Clean Restart)  
**Date:** 2026-01-27  
**Status:** Draft

---

## Problem Statement

Survey methodologists spend weeks manually validating survey logic in Word documents. Errors slip through to production. There's no single source of truth - logic is scattered across Word docs, Excel trackers, and tribal knowledge. Testing requires human testers running through surveys manually.

---

## Vision

**Convert any paper survey into a mathematical graph that can be programmatically validated, tested, and translated.**

A survey in canonical JSON format becomes:
- Instantly validatable (find bad nodes in seconds, not weeks)
- Automatically testable (generate minimal test scenarios, run via API)
- Translatable (export to Qualtrics, OMB CSV, Word docs, any format)
- Single source of truth (one file, version controlled)

---

## Core Goals

### G1: Extract Survey to Canonical JSON
- Input: Survey PDF (paper questionnaire)
- Output: Complete JSON containing:
  - All questions with text, type, options
  - All routing logic as explicit edges with evaluatable conditions
  - Block structure and ordering
  - Metadata (variables, universe conditions, descriptions)
- Constraint: Human must be able to validate extraction against source PDF

### G2: Validate Survey Logic
- Detect orphaned questions (unreachable nodes)
- Detect dead ends (no path to terminal)
- Detect circular dependencies
- Detect impossible conditions
- Pinpoint exact node/edge with problem
- LLM-powered fix recommendations
- Human validation workflow with decision trace (who approved what, when, why)

### G3: Automate Testing
- Generate minimal covering set (minimum test cases for 100% edge coverage)
- Execute tests via survey API with synthetic respondent profiles
- Compare actual paths vs expected paths
- Report pass/fail with coverage statistics

### G4: Calculate Survey Metrics
- Estimated respondent burden (time to complete)
- Path complexity (number of possible routes)
- Question reachability (% of respondents who see each question)
- Conditional logic density

### G5: Enable Translation
- Export to Word (review format, publish format)
- Export to OMB CSV (government submission)
- Export to QSF (Qualtrics import)
- Export to any format (JSON is the interchange)

---

## Functional Requirements

### FR1: Extraction Pipeline

| ID | Requirement | Priority |
|----|-------------|----------|
| FR1.1 | Accept PDF input (scanned or digital) | Must |
| FR1.2 | Extract all question text verbatim | Must |
| FR1.3 | Identify question types (radio, checkbox, number, text, instruction) | Must |
| FR1.4 | Extract all response options with values | Must |
| FR1.5 | Extract routing logic (skip patterns, branches) | Must |
| FR1.6 | Parse conditions into evaluatable AST format | Must |
| FR1.7 | Assign edge priorities correctly | Must |
| FR1.8 | Identify block boundaries and ordering | Should |
| FR1.9 | Extract universe conditions | Should |
| FR1.10 | Support multi-language surveys | Could |

### FR2: Validation Engine

| ID | Requirement | Priority |
|----|-------------|----------|
| FR2.1 | Validate DAG structure (single entry, reachable terminal) | Must |
| FR2.2 | Identify orphaned nodes | Must |
| FR2.3 | Identify dead-end nodes | Must |
| FR2.4 | Detect circular dependencies | Must |
| FR2.5 | Validate all edge conditions are parseable | Must |
| FR2.6 | Generate validation report with specific node/edge IDs | Must |
| FR2.7 | LLM-powered fix recommendations | Should |
| FR2.8 | Human approval workflow | Should |
| FR2.9 | Decision trace logging | Should |

### FR3: Test Generation

| ID | Requirement | Priority |
|----|-------------|----------|
| FR3.1 | Generate minimal covering set for 100% edge coverage | Must |
| FR3.2 | Output test cases with expected paths | Must |
| FR3.3 | Output response sequences for routing questions | Must |
| FR3.4 | Execute tests via survey API | Should |
| FR3.5 | Compare actual vs expected paths | Should |
| FR3.6 | Generate pass/fail report | Should |

### FR4: Metrics

| ID | Requirement | Priority |
|----|-------------|----------|
| FR4.1 | Calculate total nodes and edges | Must |
| FR4.2 | Calculate path count | Should |
| FR4.3 | Estimate completion time | Could |
| FR4.4 | Calculate per-question reachability | Could |

### FR5: Export

| ID | Requirement | Priority |
|----|-------------|----------|
| FR5.1 | Export to human-readable validation report | Must |
| FR5.2 | Export to Word document | Should |
| FR5.3 | Export to OMB CSV | Should |
| FR5.4 | Export to Qualtrics QSF | Could |

---

## Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR1 | Extraction accuracy | 95%+ questions correctly extracted |
| NFR2 | Validation speed | < 5 seconds for 500-node survey |
| NFR3 | Test generation speed | < 30 seconds for covering set |
| NFR4 | Human validation UX | Side-by-side PDF and JSON comparison |

---

## Schema Requirements

### Canonical JSON Format

The schema must support:

1. **Content** (for human validation + export)
   - Question text, type, options
   - Block structure
   - Metadata

2. **Evaluatable Logic** (for routing engine)
   - Explicit edge list (not scattered across questions/options/logic)
   - AST-format conditions: `[">", "D11", 0]`
   - Priority field on every edge
   - Edge types: branch, fallthrough, terminal

3. **Audit Trail**
   - Extraction confidence scores
   - Human validation status
   - Decision trace

### Edge Condition Format

AST arrays (prefix notation):
```json
["AND", [">", "D11", 0], ["=", "EMP1", 2]]
```

Operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not_in`, `AND`, `OR`, `NOT`

### Priority Convention

Lower number = higher priority. Fallthrough edges get `priority: 999`.

---

## Constraints

1. **Human validation is mandatory** - No automated fixes without human approval
2. **Audit trail required** - Every decision must be logged with rationale
3. **Schema-first** - Update schema before changing extraction code
4. **General purpose** - Must work for any survey, not hardcoded for HTOPS

---

## Success Criteria

1. Extract HTOPS survey with 0 missing questions
2. All 21 test cases from coverage solver pass
3. Validation identifies known issues in test surveys
4. Human can validate extraction in < 2 hours (vs weeks manually)

---

## Out of Scope (v2.0)

- Real-time survey hosting
- Respondent data collection
- Multi-user collaboration
- Survey authoring UI
