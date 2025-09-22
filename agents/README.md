# Survey Automation Agents

This directory contains automated agents for survey logic processing using LLM analysis.

## Setup & Prerequisites

### 1. Convert Excel Data Dictionary to JSON
```bash
# First, convert the Excel data dictionary to JSON format
python convert_excel.py
# This creates: data/htops_data_dictionary.json
```

### 2. Environment Configuration
The agents use the `.env` file in the project root:
```bash
OPENAI_API_KEY=your_key_here  # Required for LLM processing
```

### 3. Survey PDF Context
The agents automatically load survey context from:
- `data/HTOPS_2502_Questionnaire_ENGLISH.pdf` (survey structure context)
- Provides block organization and flow patterns to LLM

## Overview

The automation agents process survey questions in batches to generate:
- **Routing Logic**: Automated assignment of question routing and skip patterns
- **Variable Mapping**: Assignment of data dictionary variables to questions

## Agents

### 1. Routing Agent (`routing_agent.py`)
Analyzes survey questions to generate routing assignments.

**Input**: Minimal survey nodes JSON (133 questions)  
**Output**: Routing assignments with edges and predicates  
**Batch Size**: 20 questions per LLM call  

**Features:**
- Automatic routing pattern detection (fallthrough, branch, terminate)
- Universe condition generation
- Edge predicate creation
- Priority assignment for alternative routes

**Usage:**
```bash
# Convert Excel data dictionary first
python convert_excel.py

# Run complete automation
python agents/automation_orchestrator.py --input data/htops_complete_nodes_minimal.json --data-dict data/htops_data_dictionary.json

# Run individual agents
python agents/routing_agent.py --input data/htops_complete_nodes_minimal.json
python agents/variable_agent.py --input data/htops_complete_nodes_minimal.json --data-dict data/htops_data_dictionary.json
```

### 2. Variable Agent (`variable_agent.py`)
Maps survey questions to data dictionary variables.

**Input**: Minimal survey nodes + optional data dictionary  
**Output**: Variable assignments with confidence scores  
**Batch Size**: 20 questions per LLM call  

**Features:**
- Variable name assignment following survey conventions
- Data type inference (numeric, categorical, text, multiple_choice)
- Confidence scoring for quality assessment
- Data dictionary integration (when available)

**Usage:**
```bash
python agents/variable_agent.py --input data/htops_complete_nodes_minimal.json --data-dict data/htops_data_dictionary.json
```

### 3. Automation Orchestrator (`automation_orchestrator.py`)
Runs both agents in sequence and merges results.

**Input**: Minimal survey nodes + optional data dictionary  
**Output**: Complete enhanced survey with routing and variables  

**Features:**
- Sequential agent execution
- Result merging and validation
- Quality metrics and recommendations
- Timestamped run management

**Usage:**
```bash
python agents/automation_orchestrator.py --input data/htops_complete_nodes_minimal.json --data-dict data/htops_data_dictionary.json
```

## Output Structure

Each run creates a timestamped directory:
```
output/automation_run_20250917_120000/
├── routing/                          # Routing agent outputs
│   ├── routing_batch_01.json         # Batch results
│   ├── routing_batch_02.json
│   └── routing_assignments_complete.json
├── variables/                        # Variable agent outputs  
│   ├── variable_batch_01.json        # Batch results
│   ├── variable_batch_02.json
│   └── variable_mappings_complete.json
├── complete_automated_survey.json    # Merged results
└── automation_summary.json           # Quality report
```

## Quality Validation

### Gold Standard Comparison
Compare automated routing against manual extraction:
- **Manual Gold Standard**: 24 chunks × 5 questions = 120 routing assignments
- **Location**: `../surveys_db/GoldStandardExtraction-9-11-2025/`
- **Format**: Rich extraction with domain and universe data

### Quality Metrics
- **Routing Coverage**: % of questions with routing assignments
- **Variable Coverage**: % of questions with variable assignments  
- **Confidence Scores**: Variable assignment quality (0.0-1.0)
- **Consistency Checks**: Cross-batch validation
- **Schema Compliance**: Survey DAG v1.1 compatibility

## Schema Integration

### Updated Schema v1.1
Added optional `variable` field to node specification:
```json
{
  "variable": {
    "type": "string", 
    "description": "Optional survey variable name for data dictionary mapping"
  }
}
```

### Enhanced Nodes Format
```json
{
  "id": "D11",
  "type": "question",
  "text": "How many people under 18...",
  "block": "demographics", 
  "order_index": 15,
  "variable": "D11",
  "variable_metadata": {
    "data_type": "numeric",
    "confidence": 0.95,
    "reasoning": "Standard demographic question",
    "description": "Number of children in household"
  },
  "routing_assignments": [
    {
      "source_question": "D11",
      "response_value": "> 0", 
      "target_question": "D12",
      "predicate": "D11 > 0",
      "edge_type": "branch",
      "priority": 0
    }
  ]
}
```

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for LLM analysis

### Command Line Options
- `--input`: Input JSON file (required)
- `--output`: Output directory (default: "output")
- `--batch-size`: Questions per batch (default: 20)
- `--model`: OpenAI model (default: "gpt-4")
- `--data-dict`: Data dictionary file (optional)

## Integration with Survey DAG Extractor

These agents are part of the larger Survey DAG Extraction workflow:

1. **Phase 1**: Manual node extraction → `htops_complete_nodes_minimal.json`
2. **Phase 4.0**: **Automation agents** → Enhanced nodes with routing + variables
3. **Phase 4.1**: Schema export → Survey DAG v1.1 compliant JSON
4. **Phase 4.2**: Validation and analysis → Production-ready survey

The agents bridge the gap between minimal node extraction and complete survey logic, automating what previously required extensive manual work.
