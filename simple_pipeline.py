#!/usr/bin/env python3
"""
Complete Survey Automation Pipeline - Simple Version

Runs routing and semantic variable mapping, focuses on clear reporting.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import sys

# Add agents directory to path
sys.path.append(str(Path(__file__).parent / 'agents'))

from routing_agent import RoutingAgent
from variable_agent_semantic import SemanticVariableAgent

class SimpleSurveyPipeline:
    """Simple survey automation pipeline with clear reporting."""
    
    def __init__(self, batch_size: int = 20, model: str = 'gpt-5'):
        self.batch_size = batch_size
        self.model = model
        
        # Create timestamped run directory
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(f"pipeline_run_{self.timestamp}")
        self.run_dir.mkdir(exist_ok=True)
        
        print(f"🚀 Survey Automation Pipeline")
        print(f"   Output: {self.run_dir}")
        
        # Agent configurations
        self.config = {
            'batch_settings': {'default_batch_size': batch_size if batch_size != 20 else 10},  # Default to 10 for full extraction
            'model_settings': {'model': model}
        }
        
    def run_complete_pipeline(self, input_file: Path, data_dict_file: Path) -> Dict[str, Any]:
        """Run complete pipeline with clear success/failure reporting."""
        
        # Load original survey
        with open(input_file) as f:
            original_nodes = json.load(f)
        questions = [n for n in original_nodes if n.get('type') == 'question']
        
        print(f"📊 Processing {len(questions)} questions from {len(original_nodes)} total nodes")
        
        routing_success = []
        routing_failed = []
        variable_success = []
        variable_failed = []
        
        # Run routing agent
        print(f"\n🔀 Running Routing Agent...")
        try:
            routing_dir = self.run_dir / "routing"
            routing_dir.mkdir(exist_ok=True)
            
            routing_agent = RoutingAgent(self.config)
            routing_results = routing_agent.process_survey(input_file, routing_dir)
            
            # Analyze routing results
            enhanced_routing_nodes = routing_results.get('enhanced_nodes', [])
            for node in enhanced_routing_nodes:
                if node.get('type') == 'question':
                    if node.get('routing_assignments') or node.get('extraction_metadata'):
                        routing_success.append(node['id'])
                    else:
                        routing_failed.append(node['id'])
            
            print(f"   ✅ Routing completed: {len(routing_success)} success, {len(routing_failed)} failed")
            print(f"   📊 Extraction coverage: {routing_results.get('extraction_summary', {}).get('extraction_coverage', 0):.1%}")
            
        except Exception as e:
            print(f"   ❌ Routing agent failed: {e}")
            routing_results = {'enhanced_nodes': original_nodes}
            routing_failed = [q['id'] for q in questions]
        
        # Run semantic variable agent
        print(f"\n🏷️  Running Semantic Variable Mapping...")
        try:
            variable_dir = self.run_dir / "variables"
            variable_dir.mkdir(exist_ok=True)
            
            variable_agent = SemanticVariableAgent(self.config)
            variable_results = variable_agent.process_survey(input_file, variable_dir, data_dict_file)
            
            # Analyze variable results
            enhanced_variable_nodes = variable_results.get('enhanced_nodes', [])
            for node in enhanced_variable_nodes:
                if node.get('type') == 'question':
                    if node.get('variable') or node.get('variables'):
                        variable_success.append(node['id'])
                    else:
                        variable_failed.append(node['id'])
            
            print(f"   ✅ Variable mapping completed: {len(variable_success)} success, {len(variable_failed)} failed")
            
        except Exception as e:
            print(f"   ❌ Variable agent failed: {e}")
            variable_results = {'enhanced_nodes': original_nodes, 'semantic_summary': {}}
            variable_failed = [q['id'] for q in questions]
        
        # Merge results
        print(f"\n🔗 Merging results...")
        final_nodes = self._merge_results(original_nodes, routing_results, variable_results)
        
        # Generate final output
        complete_survey = {
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "run_id": self.timestamp,
                "total_nodes": len(final_nodes),
                "total_questions": len(questions),
                "model_used": self.model,
                "batch_size": self.batch_size
            },
            "enhanced_nodes": final_nodes,
            "extraction_report": {
                "routing": {
                    "successful_questions": routing_success,
                    "failed_questions": routing_failed,
                    "success_count": len(routing_success),
                    "failure_count": len(routing_failed),
                    "success_rate": len(routing_success) / len(questions) if questions else 0
                },
                "variables": {
                    "successful_questions": variable_success,
                    "failed_questions": variable_failed,
                    "success_count": len(variable_success),
                    "failure_count": len(variable_failed),
                    "success_rate": len(variable_success) / len(questions) if questions else 0,
                    "multi_variable_questions": [n['id'] for n in final_nodes if n.get('variables')],
                    "avg_confidence": variable_results.get('semantic_summary', {}).get('avg_confidence', 0),
                    "avg_semantic_score": variable_results.get('semantic_summary', {}).get('avg_semantic_score', 0)
                },
                "overall": {
                    "questions_with_both": len([n for n in final_nodes 
                                               if n.get('type') == 'question' and 
                                               (n.get('variable') or n.get('variables')) and 
                                               n.get('routing_assignments')]),
                    "questions_with_routing_only": len([n for n in final_nodes 
                                                      if n.get('type') == 'question' and 
                                                      n.get('routing_assignments') and 
                                                      not (n.get('variable') or n.get('variables'))]),
                    "questions_with_variables_only": len([n for n in final_nodes 
                                                        if n.get('type') == 'question' and 
                                                        (n.get('variable') or n.get('variables')) and 
                                                        not n.get('routing_assignments')]),
                    "questions_with_neither": len([n for n in final_nodes 
                                                 if n.get('type') == 'question' and 
                                                 not n.get('routing_assignments') and 
                                                 not (n.get('variable') or n.get('variables'))])
                }
            }
        }
        
        # Save final result
        output_file = self.run_dir / "complete_automated_survey.json"
        with open(output_file, 'w') as f:
            json.dump(complete_survey, f, indent=2)
        
        # Generate clear final report
        self._print_final_report(complete_survey)
        
        return complete_survey
    
    def _merge_results(self, original_nodes: List[Dict], routing_results: Dict, variable_results: Dict) -> List[Dict]:
        """Merge routing and variable results."""
        
        # Start with variable-enhanced nodes (has variable mappings)
        enhanced_nodes = variable_results.get('enhanced_nodes', original_nodes)
        
        # Get routing assignments
        routing_assignments = {}
        for node in routing_results.get('enhanced_nodes', []):
            if node.get('routing_assignments'):
                routing_assignments[node['id']] = node['routing_assignments']
        
        # Merge routing into variable-enhanced nodes
        final_nodes = []
        for node in enhanced_nodes:
            merged_node = node.copy()
            
            # Add routing assignments if available
            if node['id'] in routing_assignments:
                merged_node['routing_assignments'] = routing_assignments[node['id']]
            
            final_nodes.append(merged_node)
        
        return final_nodes
    
    def _print_final_report(self, complete_survey: Dict) -> None:
        """Print clear final report."""
        
        report = complete_survey['extraction_report']
        
        print(f"\n📋 EXTRACTION REPORT")
        print(f"   Run ID: {complete_survey['metadata']['run_id']}")
        print(f"   Total Questions: {complete_survey['metadata']['total_questions']}")
        
        print(f"\n🔀 ROUTING RESULTS:")
        print(f"   ✅ Successful: {report['routing']['success_count']} ({report['routing']['success_rate']:.1%})") 
        print(f"   ❌ Failed: {report['routing']['failure_count']}")
        if report['routing']['failed_questions']:
            print(f"   Failed questions: {', '.join(report['routing']['failed_questions'][:10])}{'...' if len(report['routing']['failed_questions']) > 10 else ''}")
        
        print(f"\n🏷️  VARIABLE RESULTS:")
        print(f"   ✅ Successful: {report['variables']['success_count']} ({report['variables']['success_rate']:.1%})")
        print(f"   ❌ Failed: {report['variables']['failure_count']}")
        print(f"   🔢 Multi-variable: {len(report['variables']['multi_variable_questions'])}")
        print(f"   📊 Avg Confidence: {report['variables']['avg_confidence']:.2f}")
        print(f"   🧠 Avg Semantic Score: {report['variables']['avg_semantic_score']:.2f}")
        if report['variables']['failed_questions']:
            print(f"   Failed questions: {', '.join(report['variables']['failed_questions'][:10])}{'...' if len(report['variables']['failed_questions']) > 10 else ''}")
        
        print(f"\n📊 OVERALL SUMMARY:")
        overall = report['overall']
        print(f"   Complete (routing + variables): {overall['questions_with_both']}")
        print(f"   Routing only: {overall['questions_with_routing_only']}")
        print(f"   Variables only: {overall['questions_with_variables_only']}")
        print(f"   Neither: {overall['questions_with_neither']}")
        
        total_extracted = overall['questions_with_both'] + overall['questions_with_routing_only'] + overall['questions_with_variables_only']
        total_questions = complete_survey['metadata']['total_questions']
        extraction_rate = total_extracted / total_questions if total_questions else 0
        
        print(f"\n🎯 EXTRACTION SUCCESS: {total_extracted}/{total_questions} ({extraction_rate:.1%})")
        print(f"💾 Output saved: {self.run_dir}/complete_automated_survey.json")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Simple Survey Automation Pipeline")
    parser.add_argument("--input", default="data/htops_complete_nodes_minimal.json")
    parser.add_argument("--data-dict", default="data/htops_data_dictionary.json")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--model", default="gpt-5")
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    data_dict_file = Path(args.data_dict)
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return 1
    
    if not data_dict_file.exists():
        print(f"❌ Data dictionary not found: {data_dict_file}")
        return 1
    
    try:
        pipeline = SimpleSurveyPipeline(batch_size=args.batch_size, model=args.model)
        pipeline.run_complete_pipeline(input_file, data_dict_file)
        return 0
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
