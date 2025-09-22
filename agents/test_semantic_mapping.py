#!/usr/bin/env python3
"""
Test Semantic Variable Mapping

Quick test of the semantic variable mapping agent with a small batch.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path to import the agent
sys.path.append(str(Path(__file__).parent))

from variable_agent_semantic import SemanticVariableAgent

def test_semantic_mapping():
    """Test semantic variable mapping with a small sample."""
    
    print("🧪 Testing Semantic Variable Mapping Agent")
    
    # Set up paths
    project_root = Path(__file__).parent.parent
    input_file = project_root / "data" / "htops_complete_nodes_minimal.json"
    data_dict_file = project_root / "data" / "htops_data_dictionary.json"
    output_dir = project_root / "semantic_test_output"
    
    output_dir.mkdir(exist_ok=True)
    
    # Check files exist
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return
    
    if not data_dict_file.exists():
        print(f"❌ Data dictionary not found: {data_dict_file}")
        return
    
    print(f"📂 Input: {input_file}")
    print(f"📚 Data Dict: {data_dict_file}")
    print(f"📤 Output: {output_dir}")
    
    # Configure agent for small test
    config = {
        'batch_settings': {'default_batch_size': 5},  # Small batch for testing
        'model_settings': {'model': 'gpt-5'}  # Use gpt-5
    }
    
    try:
        # Create and run agent
        agent = SemanticVariableAgent(config)
        result = agent.process_survey(input_file, output_dir, data_dict_file)
        
        print(f"\n✅ Test completed successfully!")
        print(f"📊 Enhanced nodes: {len(result.get('enhanced_nodes', []))}")
        print(f"🏷️  Variable mappings: {result['metadata']['total_mappings']}")
        
        if result['semantic_summary']:
            summary = result['semantic_summary']
            print(f"🎯 Avg confidence: {summary.get('avg_confidence', 0):.2f}")
            print(f"🧠 Avg semantic score: {summary.get('avg_semantic_score', 0):.2f}")
            
            # Show some example mappings
            enhanced_nodes = result.get('enhanced_nodes', [])
            mapped_questions = [n for n in enhanced_nodes if n.get('type') == 'question' and n.get('variable')]
            
            if mapped_questions:
                print(f"\n📋 Sample mappings:")
                for q in mapped_questions[:3]:  # Show first 3 mappings
                    variable = q.get('variable')
                    var_meta = q.get('variable_metadata', {})
                    confidence = var_meta.get('confidence', 0)
                    reasoning = var_meta.get('reasoning', '')
                    
                    print(f"  {q['id']} → {variable} (confidence: {confidence:.2f})")
                    print(f"    Question: {q.get('text', '')[:80]}...")
                    print(f"    Reasoning: {reasoning[:60]}...")
                    print()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_semantic_mapping()
