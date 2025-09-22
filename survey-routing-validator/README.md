# Survey Routing Validator

Simple Flask web app for systematic survey routing validation and DAG export.

## Purpose

Replace ad-hoc scripts with systematic human-in-the-loop validation of survey routing logic extracted from PDF documents.

## Features

- **Question-by-question validation**: Walk through every survey question systematically
- **Categorical encoding validation**: Ensure proper domain specification for each question
- **Visual routing editor**: Simple interface to define where each response leads
- **Auto-generated predicates**: System creates predicate ASTs automatically
- **Terminal node creation**: Easy addition of new terminal nodes (e.g., INELIGIBLE)
- **DAG v1.1 export**: Complete survey_dag_schema v1.1 output ready for NetworkX

## Installation

```bash
cd survey-routing-validator
pip install flask
```

## Usage

1. **Start the web app:**
   ```bash
   python app.py
   ```

2. **Open browser:** http://localhost:5001

3. **Load survey:** Select from available minimal JSON files

4. **Validate routing:** For each question:
   - Define response options (categorical encoding)
   - Specify where each response routes
   - Add terminal nodes as needed

5. **Export:** Generate complete DAG v1.1 JSON file

## Input Format

Expects minimal JSON extraction files like `htops_complete_nodes_minimal.json`:

```json
[
  {
    "id": "Q1", 
    "type": "question", 
    "block": "entry_validation", 
    "order_index": 5, 
    "text": "Is this correct?"
  }
]
```

## Output Format

Exports complete survey_dag_schema v1.1 with:

- **Nodes**: Complete metadata including domain specifications
- **Edges**: All routing edges with auto-generated predicates  
- **Predicates**: AST format like `["==", "Q1", "Yes"]`
- **Validation**: Mathematical DAG validation status
- **Provenance**: Build and extraction metadata

## Key Design Principles

- **No over-engineering**: Simple, focused workflow
- **Human verification**: Surface implicit routing decisions from PDFs
- **Auto-generation**: System creates predicates, don't require manual AST editing
- **Session persistence**: Don't lose progress during long validation sessions
- **Complete output**: Self-contained DAG ready for production use

## Replaces

This tool replaces the scattered collection of 47+ analysis scripts with one systematic validation workflow.
