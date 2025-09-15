# Directory Cleanup & Organization Plan

## Current State Issues:
- 20+ temporary script files in root directory
- Mixed debugging/testing/production code  
- Hard to find actual tools vs one-off scripts
- No clear separation of phases
- Existing directories: src/, legacy/, graph_analysis/, docs/, data/, surveys_db/

## Proposed Clean Structure:

```
survey-dag-extractor/
├── README.md                          # Project overview
├── requirements.txt                   # Dependencies
│
├── core/                              # Core production tools
│   ├── __init__.py
│   ├── database_manager.py            # Move from root
│   ├── schema_exporter.py             # Phase 4A tool
│   ├── dag_validator.py               # Phase 4B tool
│   └── coverage_analyzer.py           # Phase 4C tool
│
├── data/                              # Source data (keep as-is)
│   ├── HTOPS_2502_Questionnaire_ENGLISH.pdf
│   ├── htops_complete_nodes_minimal.json
│   ├── survey_dag_schema.json
│   ├── survey_dag_schema_v1.1.json
│   ├── survey_content_schema.json
│   └── survey_structure_schema.json
│
├── surveys_db/                        # Database files (keep as-is)
│   ├── current_database.pkl
│   ├── snapshots/
│   └── exports/
│
├── docs/                              # Documentation (keep as-is)
│   ├── workflow_map.md
│   ├── thread_handoff.md
│   └── improved_extraction_workflow.md
│
├── scripts/                           # Phase 4 execution scripts
│   ├── phase4_batch1.py               # Schema export + validation
│   ├── phase4_batch2.py               # Coverage analysis
│   └── phase4_batch3.py               # Visualization + documentation
│
├── tests/                             # Testing and validation
│   ├── connectivity_test.py           # Keep useful tests
│   ├── test_database_manager.py       # Database verification
│   ├── test_fixed_db.py              # Database tests
│   └── quick_connectivity_check.py    # Lightweight tests
│
├── archive/                           # Historical debugging scripts
│   ├── phase3_fixes/
│   │   ├── fix_final_nodes.py
│   │   ├── fix_r2a.py
│   │   ├── fix_poc_*.py
│   │   └── hunt_final_node.py
│   └── debugging/
│       ├── investigate_dag.py
│       ├── investigate_r2a.py
│       ├── debug_db.py
│       ├── sanity_check.py
│       ├── verify_single_source.py
│       ├── consolidate_database.py
│       ├── setup_graph_database.py
│       ├── extract_rich_comprehensive.py
│       └── phase3_processor_hardcoded_DELETE.py
│
└── exports/                           # Phase 4 outputs
    ├── htops_survey_dag_v1.1.json     # Final schema export
    ├── validation_report.json         # Mathematical validation
    ├── coverage_analysis.json         # Test path analysis
    └── visualization_data.json        # D3.js export
```

## Cleanup Actions:

1. **Create directory structure** (core/, scripts/, tests/, archive/, exports/)
2. **Move production tools** → `core/` (database_manager.py and any Phase 4 tools)
3. **Move test files** → `tests/` (connectivity_test.py, test_*.py, quick_connectivity_check.py)
4. **Archive debugging scripts** → `archive/debugging/` and `archive/phase3_fixes/`
5. **Create Phase 4 scaffolding** → `scripts/`
6. **Update imports** in moved files
7. **Clean root directory** (keep only essential files)
8. **Account for existing directories** (src/, legacy/, graph_analysis/ remain as-is)

## Benefits:
- ✅ Clear separation of production vs debugging code
- ✅ Easy to find Phase 4 tools
- ✅ Historical scripts preserved but organized
- ✅ Clean foundation for final export phase
- ✅ Professional project structure

## Ready to execute?
This will create a clean, organized foundation for Phase 4 execution.
