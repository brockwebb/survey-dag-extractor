#!/usr/bin/env python3
"""
Complete Survey Automation Pipeline

Runs both routing and semantic variable mapping agents in sequence,
using previous results to inform improvements.

Usage:
    python complete_pipeline.py --input data/htops_complete_nodes_minimal.json --batch-size 20
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
import os

# Add agents directory to path
sys.path.append(str(Path(__file__).parent / 'agents'))

from routing_agent import RoutingAgent
from variable_agent_semantic import SemanticVariableAgent

class CompleteSurveyPipeline:
    """Complete survey automation pipeline."""
    
    def __init__(self, batch_size: int = 20, model: str = 'gpt-5'):
        """Initialize pipeline."""
        self.batch_size = batch_size
        self.model = model
        
        # Create timestamped run directory
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(f"pipeline_run_{self.timestamp}")
        self.run_dir.mkdir(exist_ok=True)
        
        print(f"🚀 Complete Survey Automation Pipeline")
        print(f"   Model: {model}")
        print(f"   Batch Size: {batch_size}")
        print(f"   Output: {self.run_dir}")
        
        # Agent configurations
        self.routing_config = {
            'batch_settings': {'default_batch_size': batch_size},
            'model_settings': {'model': model}
        }
        
        self.variable_config = {
            'batch_settings': {'default_batch_size': batch_size},
            'model_settings': {'model': model}
        }
        
        # Track results
        self.routing_results = None
        self.variable_results = None
        self.previous_results = None
        
    def load_previous_results(self) -> Optional[Dict]:
        """Load previous automation results for comparison and improvement."""
        
        # Look for most recent automation run
        output_dir = Path("output")
        if not output_dir.exists():
            print("   📁 No previous results found")
            return None
            
        automation_runs = list(output_dir.glob("automation_run_*"))
        if not automation_runs:
            print("   📁 No previous automation runs found")
            return None
            
        # Get most recent run
        latest_run = max(automation_runs, key=lambda x: x.name)
        results_file = latest_run / "complete_automated_survey.json"
        
        if not results_file.exists():
            print(f"   📁 No complete results in {latest_run}")
            return None
            
        try:
            with open(results_file) as f:
                previous = json.load(f)
            print(f"   📊 Loaded previous results from {latest_run}")
            print(f"      - Routing assignments: {len([n for n in previous if 'routing_assignments' in str(n)])}")
            print(f"      - Variable mappings: {len([n for n in previous if n.get('variable')])}")
            return previous
        except Exception as e:
            print(f"   ⚠️  Error loading previous results: {e}")
            return None
    
    def run_routing_agent(self, input_file: Path, previous_results: Optional[Dict] = None) -> Dict[str, Any]:
        """Run routing agent with improvements based on previous results."""
        
        print(f"\n🔀 Running Routing Agent")
        
        routing_dir = self.run_dir / "routing"
        routing_dir.mkdir(exist_ok=True)
        
        # Enhance routing prompt with previous results context
        if previous_results:
            print("   📊 Using previous routing results for improvement")
            # TODO: Could analyze previous routing patterns here
        
        try:
            routing_agent = RoutingAgent(self.routing_config)
            result = routing_agent.process_survey(input_file, routing_dir)
            
            print(f"   ✅ Routing completed")
            print(f"      - Assignments: {result['metadata'].get('total_routing_assignments', 0)}")
            
            return result
            
        except Exception as e:
            print(f"   ❌ Routing agent failed: {e}")
            raise
    
    def run_variable_agent(self, input_file: Path, data_dict_file: Path) -> Dict[str, Any]:
        """Run semantic variable mapping agent."""
        
        print(f"\n🏷️  Running Semantic Variable Mapping Agent")
        
        variable_dir = self.run_dir / "variables"
        variable_dir.mkdir(exist_ok=True)
        
        try:
            variable_agent = SemanticVariableAgent(self.variable_config)
            result = variable_agent.process_survey(input_file, variable_dir, data_dict_file)
            
            print(f"   ✅ Variable mapping completed")
            print(f"      - Mappings: {result['metadata'].get('total_mappings', 0)}")
            print(f"      - Avg Confidence: {result['semantic_summary'].get('avg_confidence', 0):.2f}")
            print(f"      - Avg Semantic Score: {result['semantic_summary'].get('avg_semantic_score', 0):.2f}")
            
            return result
            
        except Exception as e:
            print(f"   ❌ Variable agent failed: {e}")
            raise
    
    def merge_results(self, input_file: Path, routing_results: Dict, variable_results: Dict) -> Dict[str, Any]:
        """Merge routing and variable mapping results into complete survey."""
        
        print(f"\n🔗 Merging Results")
        
        # Load original survey nodes
        with open(input_file) as f:
            original_nodes = json.load(f)
        
        # Get enhanced nodes from routing results (includes complete extractions)
        enhanced_nodes = routing_results.get('enhanced_nodes', original_nodes)
        
        # Get variable mappings from variable results
        variable_mappings = {}
        if 'enhanced_nodes' in variable_results:
            for node in variable_results['enhanced_nodes']:
                if node.get('variable') or node.get('variables'):
                    variable_mappings[node['id']] = {
                        'variable': node.get('variable'),
                        'variables': node.get('variables'),
                        'variable_metadata': node.get('variable_metadata', {})
                    }
        
        # Merge variable mappings into routing-enhanced nodes
        final_nodes = []
        for node in enhanced_nodes:
            merged_node = node.copy()
            
            # Add variable mappings if available
            if node['id'] in variable_mappings:
                var_data = variable_mappings[node['id']]
                if var_data['variable']:
                    merged_node['variable'] = var_data['variable']
                if var_data['variables']:
                    merged_node['variables'] = var_data['variables']
                if var_data['variable_metadata']:
                    merged_node['variable_metadata'] = var_data['variable_metadata']
                merged_node['has_variables'] = True
            else:
                merged_node['has_variables'] = False
            
            # Check if routing assignments exist
            merged_node['has_routing'] = bool(merged_node.get('routing_assignments'))
            
            final_nodes.append(merged_node)
        
        # Count routing assignments
        total_routing_assignments = sum(len(node.get('routing_assignments', [])) for node in final_nodes)
        
        # Generate comprehensive merged result
        merged_result = {
            "metadata": {
                "pipeline": "CompleteSurveyPipeline",
                "version": "2.0",
                "processed_at": datetime.now().isoformat(),
                "run_id": self.timestamp,
                "total_nodes": len(final_nodes),
                "total_questions": len([n for n in final_nodes if n.get('type') == 'question']),
                "model_used": self.model,
                "batch_size": self.batch_size
            },
            "enhanced_nodes": final_nodes,
            "pipeline_summary": {
                "routing": {
                    "assignments_generated": total_routing_assignments,
                    "questions_with_routing": len([n for n in final_nodes if n.get('has_routing')]),
                    "avg_confidence": routing_results.get('extraction_summary', {}).get('avg_confidence', 0)
                },
                "variables": {
                    "mappings_generated": variable_results['metadata'].get('total_mappings', 0),
                    "questions_with_variables": len([n for n in final_nodes if n.get('has_variables')]),
                    "multi_variable_questions": len([n for n in final_nodes if n.get('variables')]),
                    "avg_confidence": variable_results.get('semantic_summary', {}).get('avg_confidence', 0),
                    "avg_semantic_score": variable_results.get('semantic_summary', {}).get('avg_semantic_score', 0)
                },
                "quality_metrics": {
                    "complete_questions": len([n for n in final_nodes 
                                             if n.get('type') == 'question' and 
                                             n.get('has_variables') and 
                                             n.get('has_routing')]),
                    "routing_coverage": len([n for n in final_nodes if n.get('has_routing')]) / 
                                       max(1, len([n for n in final_nodes if n.get('type') == 'question'])),
                    "variable_coverage": len([n for n in final_nodes if n.get('has_variables')]) / 
                                        max(1, len([n for n in final_nodes if n.get('type') == 'question']))
                }
            },
            "comparison_with_previous": self._compare_with_previous(final_nodes) if self.previous_results else None
        }
        
        # Save merged result
        output_file = self.run_dir / "complete_automated_survey.json"
        with open(output_file, 'w') as f:
            json.dump(merged_result, f, indent=2)
        
        print(f"   ✅ Merged results saved: {output_file}")
        print(f"   📊 Complete questions: {merged_result['pipeline_summary']['quality_metrics']['complete_questions']}")
        
        return merged_result
    
    def _compare_with_previous(self, current_nodes: List[Dict]) -> Dict[str, Any]:
        """Compare current results with previous run."""
        
        if not self.previous_results:
            return None
        
        prev_nodes = self.previous_results if isinstance(self.previous_results, list) else []
        
        # Count improvements
        current_with_vars = len([n for n in current_nodes if n.get('has_variables')])
        current_with_routing = len([n for n in current_nodes if n.get('has_routing')])
        
        prev_with_vars = len([n for n in prev_nodes if n.get('variable')])
        prev_with_routing = len([n for n in prev_nodes if n.get('routing_assignments')])
        
        return {
            "variable_improvement": current_with_vars - prev_with_vars,
            "routing_improvement": current_with_routing - prev_with_routing,
            "current_variable_count": current_with_vars,
            "current_routing_count": current_with_routing,
            "previous_variable_count": prev_with_vars,
            "previous_routing_count": prev_with_routing
        }
    
    def run_complete_pipeline(self, input_file: Path, data_dict_file: Path) -> Dict[str, Any]:
        """Run the complete survey automation pipeline."""
        
        print(f"\n📋 Input Files:")
        print(f"   Survey: {input_file}")
        print(f"   Data Dict: {data_dict_file}")
        
        # Load previous results for improvement
        self.previous_results = self.load_previous_results()
        
        # Run routing agent
        self.routing_results = self.run_routing_agent(input_file, self.previous_results)
        
        # Run variable mapping agent  
        self.variable_results = self.run_variable_agent(input_file, data_dict_file)
        
        # Merge results
        merged_results = self.merge_results(input_file, self.routing_results, self.variable_results)
        
        # Generate final summary
        self.generate_final_summary(merged_results)
        
        return merged_results
    
    def generate_final_summary(self, merged_results: Dict[str, Any]) -> None:
        """Generate final pipeline summary."""
        
        print(f"\n🎯 Complete Pipeline Summary")
        print(f"   Run ID: {self.timestamp}")
        print(f"   Output Directory: {self.run_dir}")
        
        summary = merged_results['pipeline_summary']
        
        print(f"\n📊 Routing Results:")
        print(f"   Assignments: {summary['routing']['assignments_generated']}")
        print(f"   Coverage: {summary['quality_metrics']['routing_coverage']:.1%}")
        
        print(f"\n🏷️  Variable Results:")
        print(f"   Mappings: {summary['variables']['mappings_generated']}")
        print(f"   Multi-variable Questions: {summary['variables']['multi_variable_questions']}")
        print(f"   Coverage: {summary['quality_metrics']['variable_coverage']:.1%}")
        print(f"   Avg Confidence: {summary['variables']['avg_confidence']:.2f}")
        print(f"   Avg Semantic Score: {summary['variables']['avg_semantic_score']:.2f}")
        
        print(f"\n✅ Quality Metrics:")
        print(f"   Complete Questions: {summary['quality_metrics']['complete_questions']} (routing + variables)")
        
        if merged_results.get('comparison_with_previous'):
            comp = merged_results['comparison_with_previous']
            print(f"\n📈 Improvements vs Previous:")
            print(f"   Variable Mappings: +{comp['variable_improvement']}")
            print(f"   Routing Assignments: +{comp['routing_improvement']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Complete Survey Automation Pipeline")
    parser.add_argument("--input", default="data/htops_complete_nodes_minimal.json", 
                       help="Input survey JSON file")
    parser.add_argument("--data-dict", default="data/htops_data_dictionary.json",
                       help="Data dictionary JSON file")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for processing")
    parser.add_argument("--model", default="gpt-5", help="Model to use")
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    data_dict_file = Path(args.data_dict)
    
    # Verify files exist
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return 1
    
    if not data_dict_file.exists():
        print(f"❌ Data dictionary not found: {data_dict_file}")
        return 1
    
    try:
        # Run complete pipeline
        pipeline = CompleteSurveyPipeline(batch_size=args.batch_size, model=args.model)
        result = pipeline.run_complete_pipeline(input_file, data_dict_file)
        
        print(f"\n🎉 Pipeline completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
