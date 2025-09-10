# Survey DAG Extraction Workflow
## High-Level Process Map

### Phase 1: Question Discovery & Database Setup

#### Block 1A: Manual Question Extraction
- **Input**: Survey PDF content (provided by user)
- **Process**: Claude manually extracts all questions from survey
- **Output**: `questions_inventory.json`
- **Data Captured Per Question**:
  - `id` (question identifier: D11, LANG, Q1, etc.)
  - `text` (complete question text)
  - `block` (survey section: demographics, employment, health, etc.)
  - `response_options` (answer choices if applicable)
  - `universe_condition` (ASK IF statements, skip logic conditions)
  - `order_index` (sequential position in survey)
  - `metadata` (additional properties, notes)

#### Block 1B: NetworkX Database Import
- **Input**: `questions_inventory.json`
- **Process**: Python script creates NetworkX graph structure
- **Output**: `survey_graph.pkl` (serialized NetworkX graph)
- **Graph Elements**:
  - All questions as nodes (no edges yet)
  - Basic node properties from JSON
  - Terminal nodes: `END_COMPLETE`, `END_INELIGIBLE`, `SURVEY_COMPLETE`
  - Start node: `Language`

### Phase 2: Block-by-Block Validation

#### Block 2A: Generate Block Review
- **Input**: `survey_graph.pkl`
- **Process**: Extract block data for human validation
- **Output**: `block_[name]_review.json` (per block)
- **Review Data**:
  - Question IDs in block
  - Question text snippets
  - Response domains
  - Universe conditions
  - Missing question flags

#### Block 2B: Human Validation
- **Input**: Block review JSON files
- **Process**: User validates question names, checks completeness
- **Output**: Approved block status
- **Validation Checklist**:
  - Question IDs match survey expectations
  - No missing questions in block
  - Universe conditions properly captured
  - Response domains identified correctly

#### Block 2C: Block Approval
- **Input**: User validation feedback
- **Process**: Mark block as validated, fix any issues
- **Output**: Updated `survey_graph.pkl` with validation status

### Phase 3: Routing Logic Extraction

#### Block 3A: Question-by-Question Routing Analysis
- **Input**: Validated blocks from Phase 2
- **Process**: Extract skip logic for each question individually
- **Output**: Routing rules per question
- **Routing Types**:
  - Sequential flow (question → next question)
  - Conditional branches (D11=0 → EMP1, D11>0 → D12)
  - Block transitions (demographics → employment)
  - Termination conditions (ineligible → END_INELIGIBLE)

#### Block 3B: Edge Creation & Validation
- **Input**: Routing rules from 3A
- **Process**: Create NetworkX edges with predicates
- **Output**: Complete DAG with edges
- **Edge Properties**:
  - Source/target nodes
  - Predicate conditions
  - Edge types (fallthrough, branch, terminate)
  - Priority ordering

#### Block 3C: Graph Validation
- **Input**: Complete DAG
- **Process**: Mathematical validation of graph structure
- **Output**: Validation report, corrected graph
- **Validations**:
  - DAG acyclicity
  - Single start node
  - All terminals reachable
  - Complete coverage (no orphan nodes)

### Phase 4: Final Assembly & Export

#### Block 4A: Schema Compliance
- **Input**: Complete validated DAG
- **Process**: Format according to schema v1.1
- **Output**: `survey_dag_v1.1.json`
- **Schema Elements**:
  - Metadata, graph structure, predicates
  - Validation results, analysis metrics
  - Coverage analysis, optimal paths

#### Block 4B: Export & Documentation
- **Input**: Final survey DAG
- **Process**: Generate exports for different use cases
- **Output**: Multiple format exports
- **Export Formats**:
  - NetworkX format for analysis
  - D3.js format for visualization
  - CSV format for tabular analysis
  - GraphViz format for documentation

---

## Critical Decision Points

### Phase 1 → Phase 2 Gate
- **Criteria**: Complete question inventory extracted and stored
- **Validation**: All survey questions captured with metadata
- **Go/No-Go**: Proceed only if inventory is complete

### Phase 2 → Phase 3 Gate  
- **Criteria**: All blocks validated by human reviewer
- **Validation**: Question names correct, no missing questions
- **Go/No-Go**: Proceed block-by-block as each is approved

### Phase 3 → Phase 4 Gate
- **Criteria**: DAG passes mathematical validation
- **Validation**: Acyclic, complete coverage, proper routing
- **Go/No-Go**: Proceed only if graph structure is valid

## File Dependencies

```
PDF Content → questions_inventory.json → survey_graph.pkl → block_*_review.json
                                    ↓
                        survey_dag_v1.1.json ← routing_rules.json ← validated_blocks/
```

## Recovery Points

Each phase produces discrete files, allowing restart from any point:
- **Phase 1**: Restart extraction if questions_inventory.json is incomplete
- **Phase 2**: Restart validation for specific blocks without affecting others  
- **Phase 3**: Restart routing extraction for specific questions/blocks
- **Phase 4**: Regenerate exports without affecting core DAG

## Success Metrics

- **Phase 1**: 100% question capture (no missing survey questions)
- **Phase 2**: 100% block validation (all blocks approved by reviewer)
- **Phase 3**: Valid DAG structure (passes all mathematical validations)
- **Phase 4**: Schema compliance (validates against v1.1 specification)