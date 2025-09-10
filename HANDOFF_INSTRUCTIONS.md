# Survey Skip-First Extraction Test

## Context
We have a survey PDF with complex skip logic that needs to be extracted into a mathematical graph structure. The current chunked approach only extracts 1 edge out of 123 nodes (0.8% connectivity), missing almost all skip logic.

## Test the Simple Approach
Try extracting the survey structure directly from the full PDF text in a single pass, focusing specifically on skip logic patterns.

## Files Needed
1. **PDF**: `/Users/brock/Documents/GitHub/survey-dag-extractor/data/HTOPS_2502_Questionnaire_ENGLISH.pdf` (33K characters, 36 pages)
2. **Schema**: Use this target structure:

```json
{
  "survey_dag_structure": {
    "nodes": [
      {"id": "Q1", "type": "question", "text": "...", "response_domain": ["Yes", "No"]},
      {"id": "Q2", "type": "question", "text": "...", "response_domain": ["1", "2", "3", "4", "5"]},
      {"id": "END_COMPLETE", "type": "terminal"}
    ],
    "edges": [
      {"source": "Q1", "target": "Q2", "condition": "always"},
      {"source": "Q1", "target": "Q15", "condition": "Q1 == No", "skip_logic": true},
      {"source": "Q2", "target": "Q3", "condition": "always"}
    ],
    "start": "Q1",
    "terminals": ["END_COMPLETE"]
  }
}
```

## Key Patterns to Extract
- **Sequential flow**: Q1 → Q2 → Q3 (default)
- **Skip patterns**: "If No, skip to Q15", "If Yes, go to Q8", "Skip to demographics"
- **Conditional branches**: "If [condition], then [action]"
- **Terminal conditions**: "End survey if..."

## Expected Results
- **Current approach**: 123 nodes, 1 edge (broken)
- **Target**: 123 nodes, 50-100+ edges (captures skip logic)

## Test Method
1. Extract full PDF text 
2. Single LLM call focused on skip logic structure
3. Parse into node/edge graph
4. Compare edge count to current approach

The hypothesis: **Single-pass extraction will capture skip logic that chunking destroys**.

Can you test this approach and see what edge connectivity you achieve?
