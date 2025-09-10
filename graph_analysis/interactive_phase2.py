#!/usr/bin/env python3
"""
Interactive Phase 2 Extractor

Work with Claude to extract response options in chunks
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from graph_analysis.schema_compliant_extractor import SchemaCompliantExtractor

def main():
    """Interactive Phase 2 extraction workflow."""
    
    print("HTOPS Survey Phase 2: Response Options Extraction")
    print("=" * 50)
    
    # Initialize extractor
    schema_path = project_root / "data" / "survey_dag_schema_v1.1.json"
    nodes_path = project_root / "data" / "htops_complete_nodes_minimal.json"
    
    try:
        extractor = SchemaCompliantExtractor(schema_path, nodes_path)
        print(f"✓ Loaded {len(extractor.nodes)} nodes")
    except Exception as e:
        print(f"✗ Failed to initialize extractor: {e}")
        return
    
    # Show current status
    extractor.print_status()
    
    print("\nAvailable blocks:")
    blocks = {}
    for node in extractor.nodes:
        block = node.get('block', 'unknown')
        blocks[block] = blocks.get(block, 0) + 1
    
    for block, count in sorted(blocks.items()):
        print(f"  {block}: {count} nodes")
    
    # Get question chunks
    question_chunks = extractor.get_question_chunks(chunk_size=5)
    print(f"\nGenerated {len(question_chunks)} chunks of ~5 questions each")
    
    # Show first chunk for demonstration
    if question_chunks:
        print(f"\nFirst chunk ({len(question_chunks[0])} questions):")
        for i, node in enumerate(question_chunks[0], 1):
            print(f"  {i}. {node['id']}: {node['text'][:60]}...")
    
    print("\n" + "=" * 50)
    print("READY FOR PHASE 2 EXTRACTION")
    print("=" * 50)
    print("\nTo proceed with Phase 2:")
    print("1. Pick a chunk of questions")
    print("2. Extract PDF content for those questions") 
    print("3. Use Claude to identify response options")
    print("4. Update nodes with: extractor.update_node_response_options(node_id, options)")
    print("5. Validate and continue to next chunk")
    
    print(f"\nExtractor object available as 'extractor'")
    print(f"Question chunks available as 'question_chunks'")
    
    return extractor, question_chunks

if __name__ == "__main__":
    extractor, chunks = main()
