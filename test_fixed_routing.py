#!/usr/bin/env python3
"""
Test the fixed routing agent on a small sample
"""

import sys
from pathlib import Path

# Add to path
sys.path.append(str(Path(__file__).parent))

from routing_agent_fixed import RoutingAgentFixed

def test_fixed_agent():
    """Test the fixed routing agent."""
    
    input_file = Path("data/htops_complete_nodes_minimal.json")
    output_dir = Path("test_fixed_output")
    output_dir.mkdir(exist_ok=True)
    
    # Test with very small batch size
    config = {
        'batch_settings': {'default_batch_size': 3},  # Very small for testing
        'model_settings': {'model': 'gpt-5'}
    }
    
    print("🧪 Testing Fixed Routing Agent")
    
    agent = RoutingAgentFixed(config)
    result = agent.process_survey(input_file, output_dir)
    
    return result

if __name__ == "__main__":
    result = test_fixed_agent()
    print(f"\n🎯 Test Results:")
    print(f"   Extractions: {result['metadata']['total_extractions']}")
    print(f"   Coverage: {result['extraction_summary']['extraction_coverage']:.1%}")
