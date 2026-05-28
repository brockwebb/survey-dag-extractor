# Document Catalogue

**Last Updated:** 2026-05-28

---

## Project Documentation

| Document | Path | Status | Description |
|----------|------|--------|-------------|
| README | `/README.md` | Active | Project overview and runnable workbench quick start |
| Requirements | `/docs/REQUIREMENTS.md` | Active | System requirements and goals |
| Alternative System Design | `/docs/ALT_SYSTEM_DESIGN.md` | Draft | Validation, healing, editing, and test automation first design |
| Alternative System MVP Plan | `/docs/superpowers/plans/2026-05-27-alt-system-mvp.md` | Draft | MVP implementation plan for the alternate survey DAG workbench |
| Catalogue | `/docs/CATALOGUE.md` | Active | This file |
| Project Evaluation | `/docs/feedback/2026-05-23_project_evaluation.md` | Active | Current project assessment and recommended roadmap |
| Agents | `/AGENTS.md` | Active | Agent instructions and automation rules |
| Schema Redesign | `/handoffs/2026-01-27_schema-redesign.md` | Reference | Analysis of failed approach |

---

## Schema Definitions

| Document | Path | Status | Description |
|----------|------|--------|-------------|
| Canonical Survey DAG Schema | `/schemas/canonical_survey_dag_schema.json` | Active | Formal JSON Schema v2.0 |
| Schema Documentation | `/docs/CANONICAL_SURVEY_DAG_SCHEMA.md` | Active | Human-readable spec with examples |

### Archived Schemas (Reference Only)

| Document | Path | Description |
|----------|------|-------------|
| Old Schema v1.1 | `/restart/data/survey_dag_schema_v1.1.json` | Previous attempt (routing issues) |
| Old HTOPS Schema | `/restart/data/htops_survey_schema_v2.1.json` | Previous HTOPS variant |

---

## Source Materials

| Document | Path | Description |
|----------|------|-------------|
| HTOPS PDF (test file) | `/data/HTOPS_2502_Questionnaire_ENGLISH.pdf` | Source survey for extraction testing |
| HTOPS PDF (archive) | `/restart/data/HTOPS_2502_Questionnaire_ENGLISH.pdf` | Original location |
| HTOPS Markdown | `/restart/data/HTOPS_2502_Questionnaire_ENGLISH.md` | Text conversion of PDF |
| Data Dictionary | `/restart/data/HTOPS_data_dictionary.xlsx` | Variable definitions |
| Data Dictionary JSON | `/restart/data/htops_data_dictionary.json` | Parsed data dictionary |

---

## Archived Work

| Location | Description |
|----------|-------------|
| `/restart/` | All previous extraction attempts, NetworkX graph, Flask validation app |
| `/restart/surveys_db/current_database.pkl` | NetworkX graph (structure correct, serialization broken) |

---

## Infrastructure (Working)

| Component | Location | Description |
|-----------|----------|-------------|
| synth_survey_poc | External | FastAPI routing engine, coverage solver, test runner |

---

## To Be Created

| Document | Path | Purpose |
|----------|------|---------|
| Architecture | `/docs/ARCHITECTURE.md` | System design and data flow |
| Extraction Guide | `/docs/EXTRACTION.md` | How to extract surveys |
| Validation Guide | `/docs/VALIDATION.md` | Human validation workflow |
