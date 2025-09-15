# Survey DAG Extraction Backlog

## Current Status: Manual Extraction Complete ✅
- Golden standard created: 133 nodes, 119 with response options, 74 with universe conditions
- Two-stage pipeline working: Progress files → Consolidated database

## Phase 3: Universe Validation & Edge Creation 🔄 NEXT
### Universe Condition Enhancement
- [ ] **Explicit universe conditions**: Add `"universe": {"expression": "always", "dependencies": []}` to nodes without conditions
- [ ] **Universe validation**: Check all ASK IF logic is properly captured
- [ ] **Dependency analysis**: Parse universe expressions to extract actual dependencies
- [ ] **Cross-reference validation**: Ensure universe conditions match routing logic

### Edge Creation from Routing Logic
- [ ] **Parse routing from progress files**: Extract all routing rules from 24 progress files
- [ ] **Create conditional edges**: Convert routing rules to NetworkX edges with predicates
- [ ] **Handle complex routing**: Multi-select questions with specific option branches (e.g., D12 → INF2)
- [ ] **Validate edge completeness**: Ensure all universe conditions have corresponding edges
- [ ] **Add missing routing edges**: Fill gaps found during validation

## Phase 4: DAG Validation & Mathematical Analysis 🔄 PLANNED
### Mathematical Validation
- [ ] **Acyclicity check**: Ensure no circular routing
- [ ] **Reachability analysis**: All nodes reachable from start
- [ ] **Terminal validation**: All paths lead to terminals
- [ ] **Coverage analysis**: Identify unreachable code
- [ ] **Predicate validation**: Ensure all edge conditions are satisfiable

### Schema Compliance
- [ ] **v1.1 export**: Generate final schema-compliant JSON
- [ ] **Predicate compilation**: Convert routing conditions to AST format
- [ ] **Validation gates**: Run all schema validation checks
- [ ] **Analysis metrics**: Generate graph statistics and optimal paths

## Future: Automation Testing 🔄 FUTURE
### API Automation Development
- [ ] **Batch API processing**: Automate 5-question chunks via API
- [ ] **Quality comparison**: Test automation vs golden standard
- [ ] **Error analysis**: Identify where automation fails
- [ ] **Chunk size optimization**: Test 15-20 question chunks
- [ ] **Routing validation**: Compare routing extraction quality

### Pipeline Automation
- [ ] **End-to-end automation**: Full extraction → validation → export
- [ ] **Error recovery**: Handle failed chunks automatically
- [ ] **Quality gates**: Automated validation at each phase
- [ ] **Parallel processing**: Multiple extraction threads

## Technical Debt & Improvements
### Extraction Prompt Enhancement
- [x] **Explicit universe conditions**: Update prompt to require "always" when no conditions
- [ ] **Better routing validation**: Stronger validation rules in prompt
- [ ] **Edge case handling**: Better guidance for complex routing patterns
- [ ] **Error prevention**: More specific validation checkpoints

### Tool Improvements
- [ ] **Better CLI UX**: Improve copy/paste interface
- [ ] **Progress validation**: Real-time validation during extraction
- [ ] **Rollback capability**: Undo bad extractions
- [ ] **Chunk management**: Better chunk selection and retry logic

### Database Architecture
- [ ] **Edge storage**: Store routing edges in progress files
- [ ] **Incremental validation**: Validate during extraction, not just at end
- [ ] **Schema evolution**: Handle schema updates gracefully
- [ ] **Backup/restore**: Better database state management

## Known Issues & Fixes Needed
### Routing Logic Gaps
- [ ] **Multi-select branching**: D12 "includes option 1" → INF2 logic
- [ ] **Sequential fallthrough**: Default routing when no explicit conditions
- [ ] **Terminal routing**: Better handling of END → R2a type connections
- [ ] **Cross-block routing**: Long-distance skips (D11 affects 7+ questions)

### Data Quality
- [ ] **Response option validation**: Ensure all codes/text match PDF exactly
- [ ] **Universe condition parsing**: Better dependency extraction
- [ ] **Routing completeness**: Ensure all response options have routes
- [ ] **Edge case coverage**: Handle unusual question types

## Success Metrics
### Quality Targets
- **Node coverage**: 100% (133/133) ✅
- **Response options**: 100% (119/119 questions) ✅
- **Universe conditions**: 100% explicit (current: 74 explicit + 59 implicit)
- **Routing edges**: Target ~200-300 edges (current: 1)
- **DAG validation**: All mathematical properties valid

### Automation Targets
- **Accuracy**: 95% match with golden standard
- **Completeness**: 90% routing logic captured automatically
- **Efficiency**: 10x faster than manual extraction
- **Reliability**: 99% success rate on chunk processing

## Research Questions
### Survey Logic Analysis
- [ ] **Optimal chunk size**: 5 vs 15 vs 20 questions for automation
- [ ] **Context dependency**: How much context needed for accurate routing?
- [ ] **Error patterns**: What types of routing logic are hardest to extract?
- [ ] **Quality vs speed**: Trade-offs in automated extraction

### Graph Theory Applications
- [ ] **Path optimization**: Shortest survey completion paths
- [ ] **Coverage analysis**: Minimum test cases for full validation
- [ ] **Bottleneck identification**: Critical routing nodes
- [ ] **Complexity metrics**: Survey difficulty measurement
