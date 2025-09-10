# Survey Node Extraction Workflow - Improved Process

## Problem Identified
Previous extractions suffered from incompleteness due to attempting to capture all metadata simultaneously. The "90% complete but missing critical pieces" problem occurred repeatedly.

## Solution: Minimalist Iterative Approach

### Phase 1: Complete Node Coverage (Essential)
Extract minimal structure for ALL nodes in sequential order:
```json
{"id": "NODE_ID", "type": "question|terminal|instruction", "block": "block_name", "order_index": N, "text": "exact_text"}
```

**Critical Success Criteria:**
- ✅ Every single node from PDF captured
- ✅ Correct sequential ordering (order_index reflects actual survey flow)
- ✅ Complete coverage guarantee before adding complexity
- ✅ Clean database foundation established

### Phase 2: Response Options (Questions Only)
Add `response_options` field to question-type nodes only.

### Phase 3: Universe Conditions  
Add `universe_condition` field containing skip logic for each node.

### Phase 4: DAG Validation
Verify mathematical completeness and routing logic.

## Key Workflow Principles

1. **Complete Before Complex**: Get 100% node coverage before adding any metadata
2. **Sequential Ordering**: order_index must reflect actual survey flow, not extraction convenience
3. **Type Separation**: Questions, terminals, instructions are core - routing is metadata
4. **Database-Driven**: Let database handle relationships, not JSON structures
5. **Iterative Verification**: Each phase validated before proceeding

## File Naming Convention
- `survey_name_complete_nodes_minimal.json` - Phase 1 output
- Additional phases append metadata to same records in database

## Node Types
- **question**: Requires respondent input
- **terminal**: Survey endpoints (END, R2a, SURVEY_COMPLETE, FINAL_TERMINATION)  
- **instruction**: Display text, introductions, transitions

## Anti-Patterns to Avoid
- ❌ Creating separate routing nodes (routing is node metadata)
- ❌ Creating separate parameter nodes (parameters are text substitution)
- ❌ Extracting metadata before complete node coverage
- ❌ Wrong order_index sequencing

## Result: HTOPS Extraction
**Total Nodes: 133**
- Questions: 119
- Terminals: 4  
- Instructions: 10

This approach ensures completeness first, then builds complexity incrementally.