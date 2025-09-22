# Automated Survey Enhancement Pipeline

**Purpose:** Automate routing assignment and variable mapping for survey DAGs using LLM agents.

## Architecture

### Two-Agent System:

1. **Routing Agent** (`routing_agent.py`)
   - Analyzes survey questions in batches of 20
   - Assigns routing logic (sequential, conditional, terminal)
   - Auto-generates predicate ASTs
   - Creates edges in DAG v1.1 format

2. **Variable Mapping Agent** (`variable_mapping_agent.py`) 
   - Maps survey questions to data dictionary variables
   - Matches question text and IDs to variable names
   - Extracts categorical value mappings
   - Assigns confidence levels

### Complete Pipeline (`survey_enhancement_pipeline.py`)
- Orchestrates both agents
- Processes survey in batches
- Combines results into complete DAG v1.1
- Includes variable metadata and routing logic

## Usage

### Prerequisites
```bash
pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key"
```

### Run Complete Pipeline
```bash
python survey_enhancement_pipeline.py
```

### Input Files Required:
- `../data/htops_complete_nodes_minimal.json` (minimal survey extraction)
- `HTOPS_HPS_2502_DATA_DICTIONARY_PUF.xlsx` (data dictionary)

### Output:
- `htops_enhanced_dag.json` - Complete DAG v1.1 with routing + variables

## What This Replaces

**Instead of:**
- Manual routing validation web app
- 47+ analysis scripts for fixing routing
- Manual variable mapping
- Ad-hoc pickle file corrections

**You get:**
- Automated routing assignment
- Systematic variable mapping
- Complete DAG v1.1 output
- Consistent, reproducible results

## Agent Capabilities

### Routing Agent Identifies:
- Sequential flow patterns (most common)
- Skip logic based on responses
- Early termination routing (ineligibility)
- Branching paths for different respondent types
- Terminal node routing

### Variable Mapping Agent Provides:
- Question → Variable name mapping
- Variable labels and descriptions
- Categorical value mappings (1=English, 2=Spanish)
- Confidence scoring (high/medium/low)
- Match reasoning

## Output Format

Complete survey_dag_schema v1.1 with:
- **Enhanced nodes** with variable metadata
- **Routing edges** with auto-generated predicates
- **Predicate ASTs** in canonical format
- **Variable mappings** integrated into node metadata
- **Validation status** and enhancement metadata

## Benefits

1. **Scalable:** Works for any survey + data dictionary
2. **Consistent:** Standardized routing patterns
3. **Complete:** Self-contained DAG ready for analysis
4. **Auditable:** Includes confidence scores and reasoning
5. **Fast:** Processes 119 questions in ~10-15 minutes

This replaces the manual validation approach with systematic AI enhancement.
