#!/usr/bin/env python3
"""
Run semantic variable mapping directly
"""

import sys
import json
from pathlib import Path

# Add agents directory to path
sys.path.append('/Users/brock/Documents/GitHub/survey-dag-extractor/agents')

from variable_agent_semantic import SemanticVariableAgent

def run_semantic_mapping():
    """Run the semantic variable mapping agent."""
    
    print("🚀 Starting Semantic Variable Mapping")
    
    # Set up paths
    project_root = Path('/Users/brock/Documents/GitHub/survey-dag-extractor')
    input_file = project_root / 'data' / 'htops_complete_nodes_minimal.json'
    data_dict_file = project_root / 'data' / 'htops_data_dictionary.json'
    output_dir = project_root / 'semantic_output'
    
    # Load and count questions
    with open(input_file) as f:
        nodes = json.load(f)
    questions = [n for n in nodes if n.get('type') == 'question']
    
    print(f"📊 Survey: {len(nodes)} nodes, {len(questions)} questions")
    
    # Configure for testing with smaller batches
    config = {
        'batch_settings': {'default_batch_size': 10},  # Smaller batches for testing
        'model_settings': {'model': 'gpt-5'}
    }
    
    try:
        # Create and run agent
        agent = SemanticVariableAgent(config)
        result = agent.process_survey(input_file, output_dir, data_dict_file)
        
        print(f"\n✅ Semantic mapping completed!")
        print(f"📄 Results saved to: {output_dir}")
        
        # Show summary
        if 'semantic_summary' in result:
            summary = result['semantic_summary']
            print(f"🎯 Average confidence: {summary.get('avg_confidence', 0):.2f}")
            print(f"🧠 Average semantic score: {summary.get('avg_semantic_score', 0):.2f}")
            print(f"📈 Coverage: {result['metadata']['total_mappings']}/{len(questions)} questions")
            
            # Show confidence distribution
            conf_dist = summary.get('confidence_distribution', {})
            print(f"\n📊 Confidence Distribution:")
            for level, count in conf_dist.items():
                print(f"  {level}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_semantic_mapping()
    sys.exit(0 if success else 1)
