# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

This Python project has no standard package management (no requirements.txt or pyproject.toml). Install dependencies as needed:

```bash
pip install langextract openai python-dotenv jsonschema
```

**Main extraction command:**
```bash
python dag_extract_agents.py --survey data/HTOPS_2502_Questionnaire_ENGLISH.pdf --out-base dag --output-dir output
```

**Other key scripts:**
- `python break_survey.py` - Break survey into sections
- `python compare_dags.py` - Compare different DAG extractions
- `python extract_pdf.py` - Basic PDF text extraction
- `python process_section_1.py` - Process specific survey sections

**No test framework is configured** - the README mentions `python -m pytest tests/` but no tests directory exists.

## Architecture Overview

**Core Pipeline**: PDF → LLM-based Extraction → Schema-Compliant DAG → Mathematical Analysis

### Key Components

**Extraction Agents** (`agents/`):
- `StructureAgent` - Extracts survey structure (nodes, blocks, flow)
- `ContentAgent` - Extracts question content and metadata  
- `QuestionIndexAgent` - Creates question indices
- `SkipAgent` - Handles skip logic patterns
- `ContentOneAgent` - Single-pass content extraction

**Processing Pipeline**:
1. **PDF Input** - Uses `io_utils/pdf_utils.py` for text extraction with span tracking
2. **Chunking** - `chunking/page_windows.py` splits PDFs into overlapping page windows
3. **Multi-Agent Extraction** - Structure and content agents process chunks in parallel
4. **Reduction** - `reducers/chunk_reduce.py` merges chunk outputs into global documents
5. **Validation & Repair** - `validators/` ensure schema compliance and fix common issues
6. **Merging** - `merge/merge_core.py` combines structure + content into final DAG
7. **QC Output** - Quality control reports in JSON and Markdown

**Schema System**:
- `data/survey_dag_schema.json` - Mathematical DAG format (main output)
- `data/survey_structure_schema.json` - Structure extraction schema
- `data/survey_content_schema.json` - Content extraction schema

**Configuration**: `config.py` handles OpenAI API setup, model selection, and path resolution with `.env` support.

### Data Flow

```
PDF → page_windows → [StructureAgent, ContentAgent] → chunk_reduce → repair → merge_to_core → survey_dag_schema.json
```

Output artifacts go to `output/` with timestamped filenames. The final production DAG follows the mathematical `survey_dag_schema.json` format enabling graph analysis, path coverage, and logic validation.

### Key Patterns

- **Multi-pass extraction**: Agents can run multiple passes for improved accuracy
- **Chunk-based processing**: Large PDFs processed in overlapping windows for context preservation  
- **Schema-driven validation**: All outputs validated against JSON schemas
- **Provenance tracking**: Extraction metadata preserved for audit trails
- **Tolerant processing**: Validation warnings don't halt pipeline (use `--strict` to fail fast)

The legacy/ directory contains older extraction approaches that have been superseded by the agent-based architecture.