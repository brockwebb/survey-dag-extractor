# Survey DAG Extraction Project - Thread Handoff
## Status: Phase 1A Complete Question Extraction Required

### Current Project State

**Location**: `/Users/brock/Documents/GitHub/survey-dag-extractor`

**Completed Work**:
- ✅ Workflow map created (`docs/workflow_map.md`)
- ✅ Schema v1.1 with hybrid terminal architecture (`data/survey_dag_schema_v1.1.json`)
- ✅ Project structure established

**Critical Issue**: Phase 1A extraction must start from scratch. Existing 15-question sample is incorrect and should be discarded.

### Immediate Task: Complete Question Inventory Extraction

**Objective**: Extract ALL 152 questions from HTOPS survey PDF with basic metadata only.

**Input Source**: 36-page survey PDF content (user has full content available)

**Output Required**: Complete `data/questions_inventory.json` file

**Exact Data Format Specification**:

For each question, extract exactly these fields:

1. **`id`**: Question identifier as it appears in PDF (e.g., "D11", "LANG", "Q1", "EMP_Intro")
2. **`text`**: Complete question text exactly as written, including instructions
3. **`block`**: Survey section name (see block list below)
4. **`order_index`**: Sequential number (1, 2, 3... through 152)
5. **`response_options`**: Array of answer choices with exact structure:
   ```json
   [{"value": 1, "label": "Yes"}, {"value": 2, "label": "No"}]
   ```
   For text inputs: `[{"type": "text", "label": "First Name"}]`
   For numbers: `[{"type": "number", "range": {"min": 0, "max": 20}}]`
6. **`universe_condition`**: 
   - If "ASK IF D11 > 0" appears → `"D11 > 0"`
   - If no condition stated → `"always_show"`
   - Extract exactly as written in PDF
7. **`metadata`**: Object with `"type"` field:
   - Questions: `{"type": "question"}`
   - Intro text: `{"type": "intro_text"}`

**DO NOT EXTRACT/INFER**:
- Routing logic, skip patterns, conditional flows
- Response domains, validation rules
- Any relationships between questions

### Exact JSON Output Format

**DISCARD existing `questions_inventory.json` completely. Start fresh with this structure:**

```json
{
  "extraction_metadata": {
    "survey_title": "Household Trends and Outlook Pulse Survey (HTOPS) February 2025",
    "extraction_date": "2025-09-10",
    "extractor": "Claude",
    "source_document": "HTOPS_2502_Questionnaire_ENGLISH.pdf",
    "total_questions": 152,
    "extraction_status": "complete",
    "schema_version": "1.1"
  },
  "questions": [
    {
      "id": "Language",
      "text": "This survey is available in English and Spanish. Please select the language in which you prefer to complete the survey.",
      "block": "entry_validation",
      "order_index": 1,
      "response_options": [
        {"value": 1, "label": "English"},
        {"value": 2, "label": "Español"}
      ],
      "universe_condition": "always_show",
      "metadata": {
        "type": "question"
      }
    }
  ],
  "terminal_nodes": [
    {
      "id": "END",
      "text": "Please close your browser window now. The survey can be continued at a later time using the same link.",
      "block": "survey_conclusion",
      "metadata": {"type": "terminal", "reason": "normal_completion"}
    },
    {
      "id": "R2a", 
      "text": "You are not eligible to complete this survey. Thank you for your time.",
      "block": "survey_conclusion",
      "metadata": {"type": "terminal", "reason": "screening_failure"}
    },
    {
      "id": "SURVEY_COMPLETE",
      "text": "Final survey state reached.",
      "block": "survey_conclusion", 
      "metadata": {"type": "ultimate_terminal"}
    }
  ]
}
```

### Survey Block Structure (16 blocks)

Extract questions from these survey sections:

1. **entry_validation** - Language, Q1, NAME_CORR, ADDRESS_CONFIRM, GET_NAME
2. **language_satisfaction** - LANG, LANG1_R, HOWWELL_R, OECD
3. **demographics** - D11, D12, D13
4. **childcare_employment** - EMP7, EMP8, INF2, INF5, INF6, EMP_Intro, EMP1-EMP4, SPN5_DAYSTW_2
5. **health_disability** - display_HLTH, DIS1-DIS6
6. **mental_health** - HLTH_intro, HLTH1-HLTH4, MH1-MH4
7. **health_insurance** - HLTH8
8. **social_support** - SOC1_first, SOC2_first, SOCnew1, SOCnew2
9. **vaccination** - FALLVAC, RSVVAC
10. **medical_shortages** - SHORTAGE1, SHORTAGE2A
11. **food_security** - FD1, FD2, FD3, FD4, FD6_rev, FD7_new
12. **financial_stress** - SPN4, INFLATE1, INFLATE2, INFLATE4
13. **housing** - HSE1, HSE3, HSE4, HSE6, HSE8-HSE12_rev
14. **transportation** - TRANS1, TRANS2, TRANS3
15. **arts_entertainment** - Arts_Intro, ART1-ART5
16. **trust_government** - Trust1-Trust3
17. **natural_disasters** - NDX1-NDX16, ND5A-ND5HA, NDX11A-NDX11CA
18. **contact_information** - POC_display, Q3, Q6-Q12

### Critical Notes

**Terminal Nodes**: Include these 3 nodes in separate section:
- `END` (normal completion)
- `R2a` (ineligible)  
- `SURVEY_COMPLETE` (ultimate terminal per schema v1.1)

**Universe Conditions**: Extract exactly as written in PDF:
- "ASK IF D11 > 0" → `"universe_condition": "D11 > 0"`
- No explicit condition → `"universe_condition": "always_show"`

**Response Options**: Capture all answer choices with values/labels as shown in PDF.

### Why This Approach

**Strategic Reason**: Questions can skip multiple blocks (D11=0 bypasses childcare → employment). All question IDs must exist in database before routing extraction begins.

**Workflow Dependencies**:
- Phase 1B needs complete inventory for NetworkX import
- Phase 2 needs all questions for block validation
- Phase 3 needs all target IDs for routing extraction

### Next Steps After Completion

Once complete inventory is extracted:

1. **Phase 1B**: Import JSON → NetworkX graph (`survey_graph.pkl`)
2. **Phase 2**: Block-by-block validation with user
3. **Phase 3**: Question-by-question routing extraction

### File Outputs

Save complete extraction to: `/Users/brock/Documents/GitHub/survey-dag-extractor/data/questions_inventory.json`

**Success Criteria**: 
- All 152 questions captured
- No missing survey questions
- No routing logic inferred
- Clean JSON validates against structure

### User Context

User has been systematic about workflow phases and needs complete foundation before proceeding to routing logic. They understand survey domain deeply and will validate completeness before Phase 2.

**Extraction Priority**: Completeness over speed. Better to extract all questions methodically than miss questions that break routing logic later.