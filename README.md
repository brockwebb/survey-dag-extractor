# Survey DAG Extractor

Automated extraction of survey PDFs into mathematical directed acyclic graphs (DAGs) for comprehensive logic analysis and validation.

## Overview

Transform any survey instrument—even legacy paper-based PDFs—into machine-readable JSON format that's highly portable and mathematically analyzable.

## Key Benefits

**Universal Survey Digitization**
- Convert any survey PDF into standardized, portable JSON format
- Recover logic from legacy instruments lacking digital documentation
- Enable cross-survey comparison through consistent data structure

**Mathematical Survey Analysis**
- **Complete survey verification** - ensure no orphaned questions or unreachable blocks
- **Path analysis** - identify all possible routes through survey logic  
- **Universe enumeration** - catalog all conditional logic and dependencies
- **Optimal test coverage** - generate minimal test paths for 100% question coverage
- **Logic debugging** - quickly identify circular dependencies or impossible conditions

**Visual Analysis**
- **D3 force-directed network graphs** with interactive filtering
- **Survey documentation** - auto-generate comprehensive logic documentation
- **Survey archaeology** - recover and visualize complex legacy survey flows

## Architecture

```
PDF Survey → LangExtract → Canonical DAG → Mathematical Analysis → Visualization
```

- **Input**: Survey questionnaire PDFs (any format, any age)
- **Processing**: LLM-based extraction with semantic pattern recognition
- **Output**: `survey_dag_schema.json` compliant mathematical graph
- **Analysis**: Graph theory algorithms for completeness and optimization
- **Visualization**: Interactive D3 network diagrams

## Installation

```bash
pip install langextract
git clone https://github.com/your-org/survey-dag-extractor
cd survey-dag-extractor
```

## Quick Start

```python
from survey_dag_extractor import SchemaCompliantDAGExtractor

# Initialize extractor
extractor = SchemaCompliantDAGExtractor(model="gpt-4o")

# Extract survey to canonical DAG format
dag = extractor.extract_to_dag(
    pdf_path="survey_questionnaire.pdf",
    output_path="survey_dag.json"
)

# Validate survey completeness
validation_report = dag.validate_survey_logic()
print(f"Survey completeness: {validation_report['coverage_percentage']}%")
```

## Output Format

The extractor produces a canonical JSON structure following the `survey_dag_schema.json`:

```json
{
  "survey_dag": {
    "metadata": {
      "id": "survey_2025_01",
      "title": "Example Survey",
      "version": "1.0"
    },
    "graph": {
      "start": "Q1",
      "terminals": ["END_SURVEY", "END_INELIGIBLE"],
      "nodes": [
        {
          "id": "Q1",
          "type": "question",
          "domain": {"kind": "enum", "values": [1, 2, 3]},
          "universe": {"expression": "always_show"},
          "metadata": {"text": "What is your age group?"}
        }
      ],
      "edges": [
        {
          "id": "E_Q1_TO_Q2",
          "source": "Q1",
          "target": "Q2", 
          "predicate": "P_Q1_EQ_1",
          "kind": "branch"
        }
      ]
    },
    "predicates": {
      "P_Q1_EQ_1": {
        "ast": ["==", "Q1", 1],
        "text": "Q1 == 1 (Age group 18-25)"
      }
    }
  }
}
```

## Mathematical Analysis

Once extracted, the DAG enables powerful mathematical analysis:

### Path Coverage Analysis
```python
from survey_analyzer import PathAnalyzer

analyzer = PathAnalyzer(dag)

# Find minimal test paths for 100% coverage
optimal_paths = analyzer.find_minimal_covering_set()
print(f"Complete coverage with {len(optimal_paths)} test paths")

# Identify unreachable questions
orphans = analyzer.find_orphaned_nodes()
if orphans:
    print(f"Warning: {len(orphans)} unreachable questions found")
```

### Logic Validation
```python
# Check for circular dependencies
cycles = analyzer.detect_cycles()

# Validate all universe conditions
universe_validation = analyzer.validate_universes()

# Generate survey documentation
documentation = analyzer.generate_logic_documentation()
```

### Interactive Visualization
```python
from survey_visualizer import D3NetworkGraph

# Create interactive force-directed graph
visualizer = D3NetworkGraph(dag)
visualizer.generate_interactive_html("survey_network.html")

# Filter by question type, block, or universe conditions
visualizer.add_filters(['question_type', 'block', 'universe'])
```

## Use Cases

**Survey Quality Assurance**
- Validate survey logic before field deployment
- Ensure all questions are reachable through some path
- Identify redundant or impossible conditional logic

**Survey Documentation** 
- Auto-generate comprehensive routing documentation
- Create visual survey flow diagrams for stakeholders
- Document universe conditions and dependencies

**Survey Methodology Research**
- Compare survey structures across studies
- Analyze routing complexity and respondent burden
- Study question ordering effects through path analysis

**Legacy Survey Recovery**
- Digitize paper-based survey instruments
- Recover logic from PDFs lacking source documentation
- Convert proprietary formats to open, portable JSON

## Schema Compliance

All output strictly follows the `survey_dag_schema.json` specification, ensuring:
- **Mathematical rigor** - Proper DAG structure with validated nodes/edges
- **Semantic preservation** - Original variable names and conditions maintained
- **Provenance tracking** - Full extraction audit trail
- **Portability** - Standard JSON format for any downstream tool

## Contributing

We welcome contributions! The extractor is designed to be survey-agnostic while capturing survey-specific semantics.

```bash
# Run tests
python -m pytest tests/

# Validate against schema
python validate_schema.py survey_output.json

# Generate test coverage report
python analyze_coverage.py survey_dag.json
```

## License

MIT License - See LICENSE file for details
