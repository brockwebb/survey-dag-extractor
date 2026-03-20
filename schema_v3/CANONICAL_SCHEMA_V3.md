# Canonical Survey DAG Schema v3.0

## Design Principle

**Separation of Concerns:**
- `questions`: Content only (text, type, options) — no routing
- `dag.edges`: Authoritative routing with AST conditions

This separation ensures:
1. Content can be edited without touching routing logic
2. Routing is machine-evaluatable (no string parsing at runtime)
3. Human-readable descriptions preserved alongside AST

---

## Schema Structure

```json
{
  "survey": {
    "id": "htops_2025_02",
    "title": "Household Trends and Outlook Pulse Survey",
    "version": "3.0",
    "metadata": { ... },
    "blocks": { ... },
    "questions": { ... },
    "dag": {
      "edges": [ ... ]
    }
  }
}
```

---

## Questions (Content Only)

Questions contain **no routing information**. Routing lives exclusively in `dag.edges`.

```json
{
  "D11": {
    "id": "D11",
    "text": "How many people under 18 years-old currently live in your household?",
    "type": "number",
    "subtype": "numeric",
    "required": true,
    "options": [],
    "variable_name": "D11_CHILDREN_SURV",
    "validation": {
      "type": "min_value",
      "value": 0
    }
  }
}
```

### Question Types
| Type | Subtype | Description |
|------|---------|-------------|
| `radio` | `single_select` | Single choice |
| `checkbox` | `multi_select` | Multiple choice |
| `number` | `numeric` | Numeric input |
| `text` | `short_text`, `email`, `phone` | Text input |
| `instruction` | `section_intro`, `display` | Display only |
| `table` | `matrix` | Grid/matrix questions |

---

## DAG Edges (Routing Only)

All routing is expressed as directed edges with AST conditions.

### Edge Structure

```json
{
  "id": "E001",
  "source": "D11",
  "target": "D12",
  "condition": [">", "D11", 0],
  "condition_text": "D11 > 0",
  "priority": 1,
  "type": "branch"
}
```

### Edge Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique edge identifier (E001, E002, ...) |
| `source` | string | yes | Source node ID |
| `target` | string | yes | Target node ID |
| `condition` | array\|null | yes | AST condition (null = unconditional) |
| `condition_text` | string | yes | Human-readable condition |
| `priority` | integer | yes | Lower = higher priority. Fallthrough = 999 |
| `type` | string | yes | `branch`, `fallthrough`, `terminate` |

### Priority Rules

When multiple edges share the same source:
1. Evaluate edges in priority order (lowest first)
2. First edge whose condition evaluates `true` is taken
3. `priority: 999` is convention for fallthrough/default

Example:
```json
[
  {"source": "D11", "target": "D12", "condition": [">", "D11", 0], "priority": 1},
  {"source": "D11", "target": "FD1", "condition": null, "priority": 999}
]
```
If D11 > 0 → go to D12. Otherwise → go to FD1.

---

## Condition AST Specification

Conditions use **prefix notation** (operator first, then operands).

### Literals and References

```json
5                    // Integer literal
"hello"              // String literal  
"D11"                // When used as operand in comparison, references variable D11
```

### Comparison Operators

```json
[">", "D11", 0]           // D11 > 0
[">=", "D11", 5]          // D11 >= 5
["<", "D11", 10]          // D11 < 10
["<=", "D11", 3]          // D11 <= 3
["=", "EMP1", 2]          // EMP1 == 2
["!=", "Q3", 1]           // Q3 != 1
```

### Logical Operators

```json
["AND", [...], [...]]     // Both conditions must be true
["OR", [...], [...]]      // Either condition must be true
["NOT", [...]]            // Negation
```

### Set Operations (for checkbox/multi-select)

```json
["IN", "D12", 1]          // D12 includes option 1
["NOT_IN", "D12", 3]      // D12 does not include option 3
["ANY", "D12", [1, 2]]    // D12 includes any of [1, 2]
["ALL", "D12", [1, 2]]    // D12 includes all of [1, 2]
```

### Special Values

```json
null                      // Unconditional (always true)
["ALWAYS"]                // Explicit always-true
["NEVER"]                 // Explicit always-false (dead edge)
```

### Complex Examples

```json
// D11 > 0 AND EMP1 = 2
["AND", [">", "D11", 0], ["=", "EMP1", 2]]

// (D11 > 0 AND D12 includes 1) OR HSE1 = 3
["OR", 
  ["AND", [">", "D11", 0], ["IN", "D12", 1]], 
  ["=", "HSE1", 3]
]

// NOT (EMP2 = 1)
["NOT", ["=", "EMP2", 1]]
```

---

## AST Evaluation (Reference Implementation)

```python
def evaluate(condition, state: dict) -> bool:
    """
    Evaluate an AST condition against respondent state.
    
    Args:
        condition: AST array or null
        state: dict mapping question_id -> response value
    
    Returns:
        bool: whether condition is satisfied
    """
    if condition is None:
        return True
    
    if not isinstance(condition, list):
        # Literal value - shouldn't happen at top level
        return bool(condition)
    
    op = condition[0]
    
    # Comparison operators
    if op == ">":
        return state.get(condition[1], 0) > condition[2]
    if op == ">=":
        return state.get(condition[1], 0) >= condition[2]
    if op == "<":
        return state.get(condition[1], 0) < condition[2]
    if op == "<=":
        return state.get(condition[1], 0) <= condition[2]
    if op == "=":
        return state.get(condition[1]) == condition[2]
    if op == "!=":
        return state.get(condition[1]) != condition[2]
    
    # Logical operators
    if op == "AND":
        return evaluate(condition[1], state) and evaluate(condition[2], state)
    if op == "OR":
        return evaluate(condition[1], state) or evaluate(condition[2], state)
    if op == "NOT":
        return not evaluate(condition[1], state)
    
    # Set operations (for multi-select)
    if op == "IN":
        val = state.get(condition[1], [])
        if isinstance(val, list):
            return condition[2] in val
        return val == condition[2]
    if op == "NOT_IN":
        val = state.get(condition[1], [])
        if isinstance(val, list):
            return condition[2] not in val
        return val != condition[2]
    if op == "ANY":
        val = state.get(condition[1], [])
        if isinstance(val, list):
            return any(v in val for v in condition[2])
        return val in condition[2]
    if op == "ALL":
        val = state.get(condition[1], [])
        if isinstance(val, list):
            return all(v in val for v in condition[2])
        return False
    
    # Special
    if op == "ALWAYS":
        return True
    if op == "NEVER":
        return False
    
    raise ValueError(f"Unknown operator: {op}")
```

---

## Edge Generation Rules

### From Universe Conditions

Each question's universe condition generates incoming edges:

```
Question D12 has universe: "D11 > 0"
→ Edge from D11 to D12 with condition [">", "D11", 0]
```

### Block Sequential Flow

Questions within a block flow sequentially unless universe says otherwise:

```
Block: [Q1, Q2, Q3]
→ Edge Q1 → Q2 (fallthrough)
→ Edge Q2 → Q3 (fallthrough)
```

### Fallthrough Edges

When a question has no explicit next target, add fallthrough to next in sequence:

```json
{"source": "Q1", "target": "Q2", "condition": null, "priority": 999, "type": "fallthrough"}
```

### Terminal Nodes

Survey endpoints get no outgoing edges:
- END, SUBMIT, R2a (ineligible), etc.

---

## Validation Rules

A valid DAG must satisfy:

1. **All targets exist**: Every edge target must be a valid node ID
2. **All sources exist**: Every edge source must be a valid node ID  
3. **No orphans**: Every non-entry node must have at least one incoming edge
4. **Reachability**: All nodes reachable from START
5. **No cycles**: DAG must be acyclic (survey can't loop forever)
6. **Priority uniqueness**: Edges from same source should have unique priorities
7. **AST validity**: All conditions must be well-formed AST

---

## File Naming Convention

```
{survey_id}_v{version}.json

Examples:
htops_2025_02_v3.json
htops_2025_03_v3.json
```

---

## Migration from v2.0

Key changes:
1. Remove `universe` from questions
2. Add `dag.edges` array
3. Convert string expressions to AST arrays
4. Add priority to all edges
5. Add edge IDs

Conversion handled by `convert_v2_to_v3.py`
