#!/usr/bin/env python3
\"\"\"
Phase 2 Demo: Interactive Response Options Extraction

Demonstrates how to work in chunks to extract response options
for survey questions using the SchemaCompliantExtractor.
\"\"\"

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from graph_analysis.schema_compliant_extractor import SchemaCompliantExtractor


def demo_phase2_extraction():
    \"\"\"Demo Phase 2: Response options extraction in chunks.\"\"\"
    
    # Initialize paths
    project_root = Path(__file__).parent.parent
    schema_path = project_root / \"data\" / \"survey_dag_schema.json\"
    nodes_path = project_root / \"data\" / \"htops_complete_nodes_minimal.json\"
    
    # Check files exist
    if not schema_path.exists():
        print(f\"ERROR: Schema file not found: {schema_path}\")
        return False
        
    if not nodes_path.exists():
        print(f\"ERROR: Nodes file not found: {nodes_path}\")
        return False
    
    # Initialize extractor
    print(\"Initializing Schema-Compliant Extractor...\")
    extractor = SchemaCompliantExtractor(schema_path, nodes_path)
    extractor.print_status()
    
    # Show Phase 2 workflow
    print(\"\\n\" + \"=\"*50)
    print(\"Phase 2: Response Options Extraction Demo\")
    print(\"=\"*50)
    
    # Get first chunk of questions for demo
    question_chunks = extractor.get_question_chunks(chunk_size=5)
    if not question_chunks:
        print(\"No question nodes found!\")
        return False
    
    first_chunk = question_chunks[0]
    print(f\"\\nFirst chunk has {len(first_chunk)} questions:\")
    
    for i, node in enumerate(first_chunk, 1):
        print(f\"  {i}. {node['id']}: {node['text'][:80]}...\")
    
    # Demo: Manually add response options (simulating extraction)
    print(\"\\n\" + \"-\"*40)
    print(\"DEMO: Adding response options to first few questions\")
    print(\"-\"*40)
    
    # Example response options (would normally come from PDF extraction)
    demo_response_options = {
        \"Language\": [\"English\", \"Spanish\"],
        \"Q1\": [\"Yes\", \"No\"],
        \"ADDRESS_CONFIRM\": [\"Yes\", \"No\"],
        \"LANG\": [\"Yes\", \"No\"],
        \"LANG1_R\": [\"English\", \"Spanish\", \"Chinese\", \"Vietnamese\", \"Tagalog\", \"Arabic\", \"French\", \"Other\"]
    }
    
    # Update nodes with response options
    updated_count = 0
    for node_id, options in demo_response_options.items():
        if extractor.update_node_response_options(node_id, options):
            updated_count += 1
    
    print(f\"\\nUpdated {updated_count} nodes with response options\")
    
    # Show validation after updates
    print(\"\\n\" + \"-\"*40)
    print(\"Validation after Phase 2 updates:\")
    print(\"-\"*40)
    
    validation = extractor.validate_current_state()
    node_counts = validation['node_counts']
    graph_props = validation['graph_properties']
    
    print(f\"Nodes with response options: {updated_count}\")
    print(f\"Total nodes: {node_counts['total']}\")
    print(f\"Graph is DAG: {graph_props['is_dag']}\")
    print(f\"Graph is connected: {graph_props['is_connected']}\")
    
    # Show what Phase 3 would look like
    print(\"\\n\" + \"=\"*50)
    print(\"Phase 3 Preview: Universe Conditions\")
    print(\"=\"*50)
    
    # Demo universe condition (would normally be extracted)
    print(\"DEMO: Adding universe condition to LANG1_R (language question)\")
    extractor.update_node_universe_condition(
        \"LANG1_R\", 
        \"LANG == Yes\", 
        dependencies=[\"LANG\"]
    )
    
    # Demo conditional edge (would normally be extracted)
    print(\"DEMO: Adding conditional edge (LANG -> LANG1_R if LANG==Yes)\")
    extractor.add_conditional_edge(\"LANG\", \"LANG1_R\", \"LANG == Yes\", \"branch\")
    
    # Final status
    print(\"\\n\" + \"=\"*50)
    print(\"Final Status After Demo Enhancements\")
    print(\"=\"*50)
    extractor.print_status()
    
    # Export enhanced DAG
    output_path = project_root / \"graph_analysis\" / \"enhanced_dag_demo.json\"
    dag = extractor.export_schema_compliant_dag(output_path)
    
    print(f\"\\n✓ Demo complete. Enhanced DAG saved to: {output_path}\")
    
    return True


if __name__ == \"__main__\":
    print(\"HTOPS Survey Phase 2 Extraction Demo\")
    print(\"=====================================\\n\")
    
    success = demo_phase2_extraction()
    
    if success:
        print(\"\\n✓ Demo completed successfully\")
        print(\"\\nNext steps for real Phase 2 extraction:\")
        print(\"  1. Load PDF sections in chunks\")
        print(\"  2. Extract response options for each question\")
        print(\"  3. Update nodes interactively\")
        print(\"  4. Validate graph properties after each chunk\")
    else:
        print(\"\\n✗ Demo failed - check error messages above\")
