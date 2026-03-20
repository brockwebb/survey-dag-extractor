# AGENTS.md

Instructions for AI agents working on this project.

---

## Documentation Rules

### Auto-Update Catalogue
When creating or modifying files in `/docs/` or `/schemas/`:
1. Update `/docs/CATALOGUE.md` with the new/changed file
2. Set appropriate status (Active, Draft, Deprecated, Reference)
3. Update "Last Updated" date

### Handoff Documents
When ending a session with incomplete work:
1. Create `/handoffs/YYYY-MM-DD_<topic>.md`
2. Document: current state, decisions made, blockers, next steps
3. Add to catalogue

---

## Code Standards

### Schema Changes
1. Update `/schemas/canonical_survey_dag_schema.json` first
2. Update `/docs/CANONICAL_SURVEY_DAG_SCHEMA.md` to match
3. Validate existing extractions against new schema

### File Locations
| Type | Location |
|------|----------|
| Source PDFs (test files) | `/data/` |
| Extracted JSON | `/data/extracted/` |
| Schema definitions | `/schemas/` |
| Documentation | `/docs/` |
| Scripts | `/scripts/` |
| Archived/deprecated | `/restart/` |

---

## Extraction Pipeline

### Input
- Survey PDF in `/data/`
- Schema: `/schemas/canonical_survey_dag_schema.json`

### Output
- Extracted JSON in `/data/extracted/<survey_id>.json`
- Validation report in `/data/extracted/<survey_id>_validation.md`

### Process
1. Extract content (questions, options, blocks)
2. Extract routing as explicit edges
3. Parse conditions into AST format
4. Assign priorities
5. Validate against schema
6. Human validation checkpoint

---

## Validation Workflow

Human validation is mandatory. Agents recommend, humans approve.

1. Agent identifies issue (orphan node, missing edge, unparseable condition)
2. Agent recommends fix with rationale
3. Human reviews and approves/rejects
4. Decision logged with timestamp, rationale, approver

---

## Context Management

### Session Efficiency
- Offload grunt work to Claude Code
- Conserve context window
- Reference documents by path, don't paste full contents unnecessarily

### Avoid Drift
- Check schema before extraction
- Check catalogue before creating files
- Check requirements before adding features
