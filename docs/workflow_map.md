# Survey DAG Extraction Workflow
## High-Level Process Map

### Phase 1: Question Discovery & Database Setup ✅ COMPLETED

#### Block 1A: Minimal Node Extraction ✅ COMPLETED
- **Input**: Survey PDF content (provided by user)
- **Process**: Claude manually extracts all questions from survey with minimal metadata
- **Output**: `htops_complete_nodes_minimal.json` ✅ 
- **Data Captured Per Question**:
  - `id` (question identifier: D11, LANG, Q1, etc.) ✅
  - `text` (complete question text) ✅
  - `block` (survey section: demographics, employment, health, etc.) ✅
  - `type` (question, instruction, terminal) ✅
  - `order_index` (sequential position in survey) ✅
  - ~~`response_options`~~ → Phase 2
  - ~~`universe_condition`~~ → Phase 3

**Results**: 133 nodes extracted (119 questions + 10 instructions + 4 terminals)

#### Block 1B: Graph Database Setup & Ingest ✅ COMPLETED
- **Input**: `htops_complete_nodes_minimal.json` ✅
- **Process**: NetworkX graph database initialization with v1.1 schema compliance ✅
- **Output**: `surveys_db/htops_graph_database.pkl` ✅
- **Graph Elements**:
  - All 133 nodes loaded as NetworkX nodes ✅
  - v1.1 schema compliance (ultimate terminal architecture) ✅
  - Terminal classification: 3 intermediate + 1 ultimate ✅
  - Ultimate terminal edge: SURVEY_COMPLETE → FINAL_TERMINATION ✅
  - Mathematical validation framework ready ✅

**Current State**: 133 nodes, 1 edge, 131 isolated nodes (expected - routing comes in Phase 3)

---

### Phase 2: Response Options Enhancement 🔄 IN PROGRESS

#### Block 2A: Interactive Response Options Extraction
- **Input**: Graph database + PDF content chunks
- **Process**: Work with Claude in batches to extract response options
- **Batch Size**: 5-10 questions per iteration
- **Workflow**:
  1. Get question chunk from extractor
  2. Claude extracts response options from PDF
  3. Validate options with human reviewer
  4. Update graph database with options
  5. Mathematical validation check
  6. Proceed to next chunk

- **Output**: Enhanced nodes with response domains
- **Data Enhanced Per Question**:
  - `domain.kind` (enum, set, number, text, boolean)
  - `domain.values` (actual response choices)

#### Block 2B: Validation & Quality Control  
- **Input**: Questions with response options added
- **Process**: Validate response option accuracy and completeness
- **Output**: Approved response options
- **Validation Checklist**:
  - Response options match PDF exactly
  - Domain type correctly classified (single choice vs multi-choice)
  - Special cases handled (numeric input, text input)
  - No missing response categories

---

### Phase 3: Universe Validation & Edge Creation ✅ COMPLETED

#### Block 3A: Automated Universe Enhancement ✅ COMPLETED
- **Input**: Consolidated database from Phase 2
- **Process**: Generic Phase 3 processor automated universe conditions and edge creation
- **Output**: Phase 3 database with 135 edges, explicit universe conditions
- **Results**: 120/133 nodes reachable, 13 connected components, basic DAG structure

#### Block 3B: Collaborative DAG Fixing ✅ COMPLETED
- **Input**: Phase 3A database with connectivity issues
- **Process**: Interactive fixing with Claude assistance + domain expertise
- **Workflow**:
  1. **3B.1: Structural Connectivity (automated)** ✅ - Generic edge creation, isolated node fixing
  2. **3B.2: Logic-Based Fixing (Claude-assisted)** ✅ - Universe condition analysis, complex routing
  3. **3B.3: Domain Logic Validation (human-required)** ✅ - Survey methodology validation
  4. Validate improvements incrementally ✅
  5. Iterate until perfect connectivity achieved ✅

- **Final Results**: Perfect connected DAG with proper survey flow ✅
  - ✅ **133/133 nodes reachable** (100% connectivity)
  - ✅ **1 connected component** (fully unified)
  - ✅ **0 isolated nodes** (perfect connectivity)
  - ✅ **154 edges** (complete survey flow)

**Phase 3B.3: Domain Logic Validation** ✅ COMPLETED - CRITICAL WORKFLOW ADDITION

**Purpose**: Validate graph structure matches intended business/domain logic beyond pure connectivity

**Process**:
- **Semantic Flow Analysis**: Does graph start where it should logically start?
- **Business Logic Cross-Reference**: Do universe conditions match actual graph edges?
- **Domain Pattern Recognition**: Missing intro sequences, broken exit paths
- **Survey Methodology Validation**: Intended user journeys vs actual graph structure

**Issues Found & Fixed**:
1. **Missing Intro Sequence**: `INTRO_INCENTIVE` → `Continue` → `PRA` → `Language`
   - *Problem*: Graph started at `Language`, missing welcome/legal intro
   - *Root Cause*: Sequential order indices not connected properly
   - *Solution*: Connected intro chain based on survey methodology best practices

2. **Isolated R2a Terminal**: `END` → `R2a` (ineligible completion path)
   - *Problem*: R2a had universe condition `"ASK IF END reached"` but no connection from END
   - *Root Cause*: Automated tools missed semantic meaning of universe condition
   - *Solution*: Connected END terminal to R2a for proper exit flow

3. **Unreachable Contact Section**: `NDX16` → `POC_display` (contact info flow)
   - *Problem*: Contact information section disconnected from survey end
   - *Root Cause*: Missing sequential progression in final survey blocks
   - *Solution*: Connected based on order_index analysis

**Why Automated Tools Missed These**:
- **Structural connectivity** focused on graph components, not semantic meaning
- **Universe condition parsing** didn't interpret business logic implications
- **Sequential flow assumptions** missed survey methodology requirements

**Key Insight**: **Domain expertise cannot be automated** - requires human understanding of:
- Survey methodology best practices (intro → main → contact → complete)
- Business requirement interpretation (exit paths, ineligible termination)
- User experience flow logic (logical survey progression)
- Cross-reference validation (conditions vs actual structure)

**When to Include Phase 3B.3**:
- Graph passes structural connectivity but fails domain logic review
- Start node doesn't match expected survey entry point
- Exit paths seem incomplete or illogical
- Universe conditions don't align with actual graph structure
- Business stakeholders identify flow issues

**This is a "human-in-the-loop" quality gate ensuring mathematical connectivity serves actual business requirements.**

**Collaborative Automation Approach:**
- Generic tools handle 80% (universe conditions, basic routing)
- Human + Claude collaboration for remaining 20% (complex connectivity)
- Targeted problem-solving rather than generic inference
- Maintains two-stage approach with validation

---

### Phase 4: Final Export & Analysis 🔄 PLANNED

### Phase 4: Final Export & Analysis 🔄 IN PROGRESS

**Input**: Perfect DAG (133 nodes, 154 edges, 100% connectivity)  
**Goal**: Production-ready exports and comprehensive analysis  
**Output**: Schema-compliant JSON, validation reports, test coverage, documentation

#### Block 4A: Schema v1.1 Compliant Export
- **Input**: Perfect NetworkX DAG from Phase 3B
- **Process**: Transform NetworkX graph to canonical JSON format
- **Complexity**: Medium
- **Steps**:
  1. Extract graph data from NetworkX format
  2. Transform nodes → schema-compliant node objects (with domains, universe conditions)
  3. Transform edges → schema-compliant edge objects (with predicates)
  4. Generate predicates from edge conditions
  5. Validate against v1.1 schema
  6. Export `htops_survey_dag_v1.1.json`
- **Success Criteria**:
  - ✅ Valid JSON structure
  - ✅ Schema v1.1 compliance (passes validation)
  - ✅ All 133 nodes present with complete metadata
  - ✅ All 154 edges present with proper predicates
  - ✅ Proper terminal architecture (ultimate_terminal)

#### Block 4B: Mathematical Validation Report
- **Input**: Schema-compliant export from 4A
- **Process**: Comprehensive DAG validation and quality assurance
- **Complexity**: Low
- **Steps**:
  1. Run comprehensive DAG validation
  2. Verify graph properties (acyclic, single start, reachability)
  3. Validate edge/predicate consistency
  4. Check universe condition logic
  5. Generate validation report
- **Success Criteria**:
  - ✅ All mathematical validation gates pass
  - ✅ Comprehensive issue report (should be empty)
  - ✅ Graph topology metrics
  - ✅ Quality assurance documentation

#### Block 4C: Coverage Analysis & Test Paths
- **Input**: Valid DAG from 4B
- **Process**: Generate optimal test paths using graph algorithms
- **Complexity**: High
- **Steps**:
  1. Define coverage universe (nodes vs edges vs predicates)
  2. Generate optimal test paths using graph algorithms
  3. Calculate coverage percentages
  4. Create test scenario documentation
  5. Export path specifications
- **Success Criteria**:
  - ✅ Optimal test path set (minimal paths for maximum coverage)
  - ✅ Coverage analysis report (% nodes/edges covered)
  - ✅ Test scenario documentation
  - ✅ Path probability analysis

#### Block 4D: Visualization Data Export
- **Input**: Schema export and analysis results
- **Process**: Prepare data for interactive survey visualization
- **Complexity**: Medium
- **Steps**:
  1. Generate D3.js-compatible data format
  2. Calculate node positions (force-directed layout)
  3. Create interactive visualization data
  4. Export for survey logic analyzer
  5. Generate static visualization images
- **Success Criteria**:
  - ✅ D3.js JSON format
  - ✅ Node positioning data
  - ✅ Interactive features data
  - ✅ Ready for web visualization

#### Block 4E: Documentation & Handoff
- **Input**: All exports and analysis complete
- **Process**: Final project documentation and archival
- **Complexity**: Low
- **Steps**:
  1. Generate final project summary
  2. Create handoff documentation
  3. Update workflow documentation
  4. Archive project files
  5. Document lessons learned
- **Success Criteria**:
  - ✅ Complete project documentation
  - ✅ Clear handoff instructions
  - ✅ Archived project state
  - ✅ Reproducible workflow

**Phase 4 Execution Plan**:
- **Batch 1: Core Export (4A + 4B)** - Schema export + validation
- **Batch 2: Analysis (4C)** - Test coverage + optimal paths
- **Batch 3: Visualization & Documentation (4D + 4E)** - D3 export + handoff

**Tool Readiness**:
- ✅ Available: schema definition, validator, database manager
- 🔧 Needs building: schema export function, predicate generator, coverage analyzer updates, D3 export

**Success Metrics**:
- ✅ Schema v1.1 compliance (passes validation)
- ✅ 100% mathematical validation (all gates pass)
- ✅ Optimal test coverage (minimal path set)
- ✅ Production-ready survey DAG with complete documentation

---

## Current Workflow Status

### ✅ Completed Tasks
- [x] 133 nodes extracted with minimal metadata
- [x] Graph database initialized with NetworkX
- [x] v1.1 schema compliance implemented  
- [x] Terminal architecture properly configured
- [x] Mathematical validation framework ready

### 🔄 Current Task: Phase 4 - Final Export & Analysis
**Phase 3B Complete:** Perfect connectivity achieved (133/133 nodes reachable)
**Next Steps:**
1. Run schema v1.1 compliant export
2. Generate mathematical validation report
3. Create optimal test path coverage
4. Export D3 visualization data
5. Complete Phase 4 analysis

### 🔄 Upcoming: Phase 3 - Universe Conditions & Routing
### 🔄 Upcoming: Phase 4 - Final Export & Analysis

---

## Interactive Extraction Workflow

### Batch Processing Pattern:
```
1. Get question chunk (5-10 questions)
2. Extract PDF content for those questions  
3. Claude identifies response options
4. Human validates accuracy
5. Update graph database
6. Run mathematical validation
7. Proceed to next chunk
```

### Quality Gates:
- **Phase 1 → Phase 2**: Complete node inventory ✅
- **Phase 2 → Phase 3**: All questions have response options
- **Phase 3 → Phase 4**: DAG passes mathematical validation

### Recovery Points:
- Any batch can be re-processed
- Graph database maintains state between sessions
- Mathematical validation catches errors early

---

## **Lessons Learned: Collaborative Automation + Domain Validation**

### **What Worked Excellently**
- **Two-stage pipeline** (progress files → consolidated database)
- **Chunk-based extraction** (5-question chunks with Claude)
- **Generic + specific tools** (80% automation + 20% human expertise)
- **Incremental validation** (validate after each step)
- **Domain logic validation** (Phase 3B.3 human-in-the-loop quality gate)
- **Single source of truth database** (eliminated file confusion)

### **Enhanced Collaborative Automation Pattern**
```
Generic Tools (80%) + Human + Claude (20%) + Domain Validation = Production Quality
```
- Use automation for repetitive, pattern-based work (structural connectivity)
- Use human+Claude for complex logic requiring domain expertise (universe conditions)
- **CRITICAL**: Include domain logic validation step for business requirement compliance
- Validate incrementally, not just at the end
- Maintain clear database management (single working file + snapshots)

### **Phase 3B.3: Domain Logic Validation - Critical Discovery**

**What it catches that pure automation misses:**
- **Semantic flow validation**: Graph structure vs intended user journey
- **Business logic consistency**: Universe conditions vs actual implementation
- **Domain pattern recognition**: Survey methodology best practices
- **Cross-reference validation**: Multi-source data consistency

**Real examples from HTOPS:**
- **Missing intro sequence**: Automated tools connected questions but missed welcome flow
- **Isolated exit terminals**: Structural connectivity didn't understand termination logic
- **Sequential gaps**: Order indices didn't automatically create proper flow

**Why this can't be automated (currently):**
- Requires **survey methodology expertise** (intro → main → contact → complete patterns)
- Needs **business requirement interpretation** (what universe conditions actually mean)
- Demands **user experience understanding** (logical survey progression)
- Involves **stakeholder perspective** (intended vs actual implementation)

**When to include Phase 3B.3:**
- Graph passes all structural tests but feels "wrong" to domain experts
- Start node doesn't match expected survey entry point
- Exit paths incomplete or don't match business logic
- Universe conditions don't align with actual graph edges
- Stakeholders identify flow issues during review

**This is a "human-in-the-loop" quality gate that ensures mathematical perfection serves real business needs.**

## File Structure Status

```
data/
  ├── htops_complete_nodes_minimal.json ✅ 133 nodes
  └── survey_dag_schema_v1.1.json ✅ Schema

surveys_db/
  └── htops_graph_database.pkl ✅ NetworkX database

graph_analysis/
  ├── schema_compliant_extractor.py ✅ Main tool
  ├── interactive_phase2.py ✅ Ready for use
  ├── dag_validator.py ✅ Validation
  └── coverage_analyzer.py ✅ Analysis

setup_graph_database.py ✅ Initialization complete
```
