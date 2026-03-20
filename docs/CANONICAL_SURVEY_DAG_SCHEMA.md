# Canonical Survey DAG Schema

**Version:** 2.0  
**Date:** 2026-01-27  
**Status:** Draft

---

## Overview

The canonical survey DAG schema is the single source of truth for survey definition. It captures:
- **Content**: Questions, options, blocks, text (for human validation and export)
- **Structure**: Explicit edge list with evaluatable conditions (for routing engine)

One file, two concerns, joined by question ID.

---

## Top-Level Structure

```json
{
  "survey": {
    "id": "htops_2025_02",
    "title": "Household Trends and Outlook Pulse Survey",
    "version": "2025-02",
    "metadata": { ... },
    "blocks": { ... },
    "questions": { ... },
    "terminal_nodes": { ... },
    "dag": { ... }
  }
}
```

---

## Sections

### `metadata`

Survey-level information.

```json
"metadata": {
  "created_date": "2025-02-01T00:00:00Z",
  "source_file": "HTOPS_2502_Questionnaire_ENGLISH.pdf",
  "extraction_method": "llm-assisted",
  "extraction_date": "2026-01-27T00:00:00Z",
  "total_questions": 113,
  "total_blocks": 20,
  "estimated_duration_minutes": 15
}
```

### `blocks`

Logical groupings of questions.

```json
"blocks": {
  "demographics": {
    "id": "demographics",
    "title": "Demographics",
    "order": 1,
    "questions": ["D11", "D12", "D13"],
    "description": "Household composition questions"
  }
}
```

### `questions`

Question content only. **No routing here.**

```json
"questions": {
  "D11": {
    "id": "D11",
    "type": "number",
    "text": "How many children under 18 currently live in your household?",
    "required": true,
    "validation": {
      "min": 0,
      "max": 20
    }
  },
  "EMP1": {
    "id": "EMP1",
    "type": "radio",
    "text": "Last week, did you do any work for pay?",
    "required": true,
    "options": [
      {"value": 1, "text": "Yes"},
      {"value": 2, "text": "No"}
    ]
  }
}
```

#### Question Types

| Type | Description |
|------|-------------|
| `radio` | Single choice from options |
| `checkbox` | Multiple choice from options |
| `number` | Numeric input |
| `text` | Free text input |
| `instruction` | Display only, no response |
| `table` | Grid/matrix question |
| `multi_field` | Multiple related inputs (e.g., name fields) |

### `terminal_nodes`

Survey exit points.

```json
"terminal_nodes": {
  "SURVEY_COMPLETE": {
    "id": "SURVEY_COMPLETE",
    "type": "terminal",
    "text": "Thank you for completing the survey.",
    "is_final": true
  },
  "INELIGIBLE": {
    "id": "INELIGIBLE",
    "type": "terminal",
    "text": "Based on your responses, you are not eligible for this survey.",
    "is_final": false
  }
}
```

### `dag`

**The authoritative routing specification.**

```json
"dag": {
  "entry_node": "ADDRESS_CONFIRM",
  "terminal_nodes": ["SURVEY_COMPLETE", "INELIGIBLE"],
  "edges": [
    {
      "id": "E001",
      "source": "D11",
      "target": "FD2",
      "condition": [">", "D11", 0],
      "condition_text": "D11 > 0",
      "priority": 1,
      "type": "branch"
    },
    {
      "id": "E002",
      "source": "D11",
      "target": "D12",
      "condition": null,
      "condition_text": "otherwise",
      "priority": 999,
      "type": "fallthrough"
    }
  ]
}
```

---

## Edge Specification

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique edge identifier |
| `source` | string | yes | Source question/node ID |
| `target` | string | yes | Target question/node ID |
| `condition` | array\|null | yes | AST condition or null for fallthrough |
| `condition_text` | string | yes | Human-readable condition |
| `priority` | integer | yes | Evaluation order (lower = first) |
| `type` | string | yes | Edge type |

### Edge Types

| Type | Description |
|------|-------------|
| `branch` | Conditional routing based on response |
| `fallthrough` | Default path when no branch conditions match |
| `terminal` | Routes to a terminal node |

### Priority Convention

- Lower number = higher priority
- Branch conditions: 1, 2, 3, ...
- Fallthrough: 999 (always evaluated last)

Routing engine evaluates edges from source node in priority order, takes first match.

---

## Condition AST Format

Conditions are prefix-notation arrays (Lisp-style). Null means unconditional (fallthrough).

### Comparison Operators

```json
["=", "D11", 0]           // D11 equals 0
["!=", "EMP1", 2]         // EMP1 not equals 2
[">", "D11", 0]           // D11 greater than 0
["<", "AGE", 18]          // AGE less than 18
[">=", "D11", 1]          // D11 greater than or equal to 1
["<=", "D11", 5]          // D11 less than or equal to 5
```

### Set Operators

```json
["in", "STATE", [1, 2, 3]]       // STATE in [1, 2, 3]
["not_in", "STATE", [4, 5]]      // STATE not in [4, 5]
["contains", "D12", 1]           // D12 (checkbox) contains value 1
```

### Logical Operators

```json
["AND", [">", "D11", 0], ["=", "EMP1", 2]]     // D11 > 0 AND EMP1 = 2
["OR", ["=", "A", 1], ["=", "B", 1]]           // A = 1 OR B = 1
["NOT", ["=", "EMP1", 1]]                       // NOT (EMP1 = 1)
```

### Nested Conditions

```json
["AND", 
  [">", "D11", 0],
  ["OR", 
    ["=", "EMP1", 1],
    ["=", "EMP1", 2]
  ]
]
// D11 > 0 AND (EMP1 = 1 OR EMP1 = 2)
```

### Special Values

```json
null                      // Fallthrough (no condition)
["TRUE"]                  // Always true (explicit)
["FALSE"]                 // Always false (dead edge, validation error)
```

---

## Validation Rules

### DAG Integrity

1. **Single entry**: Exactly one node with no incoming edges (entry_node)
2. **Reachable terminal**: All paths eventually reach a terminal node
3. **No orphans**: Every question is reachable from entry_node
4. **No cycles**: Graph is acyclic
5. **Complete routing**: Every non-terminal node has at least one outgoing edge
6. **Fallthrough exists**: Every branching node has a fallthrough edge

### Edge Validation

1. **Source exists**: source references valid question or node
2. **Target exists**: target references valid question or terminal
3. **Condition parseable**: AST is valid or null
4. **Priority unique per source**: No two edges from same source share priority
5. **Variables exist**: Variables in conditions reference valid question IDs

---

## Example: Complete Survey Fragment

```json
{
  "survey": {
    "id": "example_survey",
    "title": "Example Survey",
    "version": "2025-01",
    "metadata": {
      "created_date": "2025-01-01T00:00:00Z",
      "total_questions": 3,
      "total_blocks": 1
    },
    "blocks": {
      "main": {
        "id": "main",
        "title": "Main Questions",
        "order": 1,
        "questions": ["Q1", "Q2", "Q3"]
      }
    },
    "questions": {
      "Q1": {
        "id": "Q1",
        "type": "radio",
        "text": "Do you have children?",
        "options": [
          {"value": 1, "text": "Yes"},
          {"value": 2, "text": "No"}
        ]
      },
      "Q2": {
        "id": "Q2",
        "type": "number",
        "text": "How many children do you have?"
      },
      "Q3": {
        "id": "Q3",
        "type": "text",
        "text": "Any additional comments?"
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
          "condition": ["=", "Q1", 1],
          "condition_text": "Q1 = Yes",
          "priority": 1,
          "type": "branch"
        },
        {
          "id": "E002",
          "source": "Q1",
          "target": "Q3",
          "condition": null,
          "condition_text": "otherwise",
          "priority": 999,
          "type": "fallthrough"
        },
        {
          "id": "E003",
          "source": "Q2",
          "target": "Q3",
          "condition": null,
          "condition_text": "continue",
          "priority": 999,
          "type": "fallthrough"
        },
        {
          "id": "E004",
          "source": "Q3",
          "target": "SURVEY_COMPLETE",
          "condition": null,
          "condition_text": "end survey",
          "priority": 999,
          "type": "terminal"
        }
      ]
    }
  }
}
```

---

## Generating Human-Readable Views

Join `questions` and `dag.edges` on question ID:

```
Q1: "Do you have children?" (radio)
  Options: Yes (1), No (2)
  Routing:
    [1] IF Q1 = Yes → Q2
    [999] OTHERWISE → Q3

Q2: "How many children do you have?" (number)
  Routing:
    [999] → Q3

Q3: "Any additional comments?" (text)
  Routing:
    [999] → SURVEY_COMPLETE (end)
```

This view is generated by tooling, not stored in the schema.

---

## Migration from v1.x

1. Keep `questions`, `blocks`, `metadata`, `terminal_nodes` as-is
2. Delete `Question.routing` property
3. Delete `Option.skip_to` property  
4. Delete `SurveyLogic.skip_patterns` and `SurveyLogic.branching_rules`
5. Add `dag` section with explicit edge list
6. Parse string conditions into AST format
7. Assign priorities to all edges
