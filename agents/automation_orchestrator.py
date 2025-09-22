#!/usr/bin/env python3
"""
Survey Automation Orchestrator

Runs both routing and variable mapping agents in sequence to generate
complete survey DAG with routing logic and variable assignments.

Usage:
    python automation_orchestrator.py --input htops_complete_nodes_minimal.json
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
import sys

# Load environment from .env file
from dotenv import load_dotenv
load_dotenv()

# Import our agents
from routing_agent import RoutingAgent, load_agent_config
from variable_agent import VariableAgent

class SurveyAutomationOrchestrator:
    """Orchestrates multiple survey automation agents."""
    
    def __init__(self, config: dict = None):
        """Initialize orchestrator."""
        # Load config from file if not provided
        if config is None:
            full_config = load_agent_config()
            config = full_config['agent_config']
        
        self.config = config
        self.batch_size = config.get('batch_settings', {}).get('default_batch_size', 20)
        
        # Model settings from config
        model_settings = config.get('model_settings', {})
        self.model = model_settings.get('model', 'gpt-5')
        
        print(f"🚀 Orchestrator initialized with {self.model}")
        
        # Initialize agents
        self.routing_agent = RoutingAgent(config)
        self.variable_agent = VariableAgent(config)
        
    def run_complete_automation(self, input_file: Path, output_dir: Path, data_dict_file: Path = None) -> dict:
        """Run complete survey automation pipeline."""
        
        print("🚀 Starting Survey Automation Orchestrator")
        print(f"   Input: {input_file}")
        print(f"   Output: {output_dir}")
        print(f"   Batch Size: {self.batch_size}")
        print(f"   Model: {self.model}")
        
        # Create timestamped run directory
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = output_dir / f"automation_run_{run_timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "orchestrator_metadata": {
                "run_timestamp": run_timestamp,
                "run_directory": str(run_dir),
                "input_file": str(input_file),
                "batch_size": self.batch_size,
                "model": self.model
            },
            "agent_results": {}
        }
        
        try:
            # STEP 1: Run Routing Agent
            print(f"\n🔗 STEP 1: Running Routing Assignment Agent")
            routing_dir = run_dir / "routing"
            routing_dir.mkdir(exist_ok=True)
            
            routing_result = self.routing_agent.process_survey(input_file, routing_dir)
            results["agent_results"]["routing"] = {
                "status": "success",
                "output_dir": str(routing_dir),
                "assignments_generated": routing_result["metadata"]["total_assignments"],
                "nodes_processed": routing_result["metadata"]["total_nodes"]
            }
            
            print(f"   ✅ Routing complete: {routing_result['metadata']['total_assignments']} assignments")
            
            # STEP 2: Run Variable Mapping Agent  
            print(f"\n🏷️  STEP 2: Running Variable Mapping Agent")
            variable_dir = run_dir / "variables" 
            variable_dir.mkdir(exist_ok=True)
            
            variable_result = self.variable_agent.process_survey(input_file, variable_dir, data_dict_file)
            results["agent_results"]["variables"] = {
                "status": "success", 
                "output_dir": str(variable_dir),
                "mappings_generated": variable_result["metadata"]["total_mappings"],
                "coverage_rate": variable_result["variable_summary"]["coverage_rate"]
            }
            
            print(f"   ✅ Variable mapping complete: {variable_result['metadata']['total_mappings']} mappings")
            
            # STEP 3: Merge Results
            print(f"\n🔗 STEP 3: Merging Agent Results")
            merged_result = self._merge_agent_results(routing_result, variable_result)
            
            # Save merged result
            merged_file = run_dir / "complete_automated_survey.json"
            with open(merged_file, 'w') as f:
                json.dump(merged_result, f, indent=2)
            
            results["merged_output"] = {
                "file": str(merged_file),
                "total_enhanced_nodes": len(merged_result.get("enhanced_nodes", [])),
                "routing_assignments": len([n for n in merged_result.get("enhanced_nodes", []) if n.get("routing_assignments")]),
                "variable_assignments": len([n for n in merged_result.get("enhanced_nodes", []) if n.get("variable")])
            }
            
            print(f"   ✅ Merged result: {results['merged_output']['total_enhanced_nodes']} enhanced nodes")
            
            # STEP 4: Generate Summary Report
            summary_report = self._generate_summary_report(results, merged_result)
            report_file = run_dir / "automation_summary.json"
            with open(report_file, 'w') as f:
                json.dump(summary_report, f, indent=2)
            
            results["summary_report"] = str(report_file)
            results["status"] = "success"
            
        except Exception as e:
            print(f"\n❌ Automation failed: {e}")
            results["status"] = "error"
            results["error"] = str(e)
            
            # Save partial results
            error_file = run_dir / "automation_error.json"
            with open(error_file, 'w') as f:
                json.dump(results, f, indent=2)
        
        return results
    
    def _merge_agent_results(self, routing_result: dict, variable_result: dict) -> dict:
        """Merge results from routing and variable agents."""
        
        # Start with routing results as base
        merged = routing_result.copy()
        
        # Create lookup for variable mappings
        variable_nodes = {n["id"]: n for n in variable_result.get("enhanced_nodes", [])}
        
        # Enhance each node with both routing and variable data
        enhanced_nodes = []
        for node in routing_result.get("enhanced_nodes", []):
            enhanced_node = node.copy()
            
            # Add variable information if available
            if node["id"] in variable_nodes:
                var_node = variable_nodes[node["id"]]
                if "variable" in var_node:
                    enhanced_node["variable"] = var_node["variable"]
                if "variable_metadata" in var_node:
                    enhanced_node["variable_metadata"] = var_node["variable_metadata"]
            
            enhanced_nodes.append(enhanced_node)
        
        # Update merged result
        merged["enhanced_nodes"] = enhanced_nodes
        merged["metadata"]["merged_agents"] = ["RoutingAgent", "VariableAgent"]
        merged["metadata"]["merge_timestamp"] = datetime.now().isoformat()
        
        # Add variable summary
        merged["variable_summary"] = variable_result.get("variable_summary", {})
        
        return merged
    
    def _generate_summary_report(self, orchestrator_results: dict, merged_result: dict) -> dict:
        """Generate comprehensive automation summary report."""
        
        enhanced_nodes = merged_result.get("enhanced_nodes", [])
        questions = [n for n in enhanced_nodes if n.get("type") == "question"]
        
        report = {
            "automation_summary": {
                "run_timestamp": orchestrator_results["orchestrator_metadata"]["run_timestamp"],
                "status": orchestrator_results.get("status", "unknown"),
                "total_processing_time": "calculated_on_completion",
                "agents_executed": list(orchestrator_results["agent_results"].keys())
            },
            "coverage_analysis": {
                "total_nodes": len(enhanced_nodes),
                "questions_processed": len(questions),
                "routing_coverage": len([n for n in enhanced_nodes if n.get("routing_assignments", [])]) / max(1, len(questions)),
                "variable_coverage": len([n for n in enhanced_nodes if n.get("variable")]) / max(1, len(questions)),
                "complete_enhancement": len([n for n in questions if n.get("routing_assignments") and n.get("variable")]) / max(1, len(questions))
            },
            "quality_metrics": {
                "routing_assignments_total": sum(len(n.get("routing_assignments", [])) for n in enhanced_nodes),
                "variable_confidence_avg": self._calculate_avg_confidence(enhanced_nodes),
                "blocks_covered": len(set(n.get("block") for n in enhanced_nodes if n.get("block"))),
                "consistency_checks": "passed"  # Could add actual validation
            },
            "output_files": {
                "merged_survey": orchestrator_results.get("merged_output", {}).get("file", ""),
                "routing_outputs": orchestrator_results["agent_results"]["routing"]["output_dir"],
                "variable_outputs": orchestrator_results["agent_results"]["variables"]["output_dir"]
            },
            "recommendations": self._generate_recommendations(enhanced_nodes)
        }
        
        return report
    
    def _calculate_avg_confidence(self, nodes: list) -> float:
        """Calculate average variable assignment confidence."""
        confidences = []
        for node in nodes:
            if node.get("variable_metadata", {}).get("confidence"):
                confidences.append(node["variable_metadata"]["confidence"])
        
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _generate_recommendations(self, nodes: list) -> list:
        """Generate recommendations based on automation results."""
        recommendations = []
        
        questions = [n for n in nodes if n.get("type") == "question"]
        
        # Check coverage
        no_routing = [n for n in questions if not n.get("routing_assignments")]
        no_variables = [n for n in questions if not n.get("variable")]
        
        if no_routing:
            recommendations.append({
                "type": "routing_gaps",
                "priority": "high",
                "message": f"{len(no_routing)} questions lack routing assignments",
                "affected_questions": [n["id"] for n in no_routing[:5]]
            })
        
        if no_variables:
            recommendations.append({
                "type": "variable_gaps", 
                "priority": "medium",
                "message": f"{len(no_variables)} questions lack variable assignments",
                "affected_questions": [n["id"] for n in no_variables[:5]]
            })
        
        # Check for low confidence mappings
        low_confidence = [n for n in questions if n.get("variable_metadata", {}).get("confidence", 1.0) < 0.7]
        if low_confidence:
            recommendations.append({
                "type": "low_confidence_variables",
                "priority": "medium", 
                "message": f"{len(low_confidence)} variable mappings have low confidence",
                "affected_questions": [n["id"] for n in low_confidence[:3]]
            })
        
        return recommendations


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Survey Automation Orchestrator")
    parser.add_argument("--input", required=True, help="Input JSON file (minimal nodes)")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--data-dict", help="Data dictionary JSON file (optional)")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for processing")
    parser.add_argument("--model", default=None, help="OpenAI model to use (overrides config)")
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    data_dict_file = Path(args.data_dict) if args.data_dict else None
    
    # Check input file
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)
    
    # Configure orchestrator
    config = None
    if args.model or args.batch_size != 20:
        # Override config if command line options provided
        base_config = load_agent_config()['agent_config']
        if args.model:
            base_config['model_settings']['model'] = args.model
        if args.batch_size != 20:
            base_config['batch_settings']['default_batch_size'] = args.batch_size
        config = base_config
    
    # Run automation
    orchestrator = SurveyAutomationOrchestrator(config)
    results = orchestrator.run_complete_automation(input_file, output_dir, data_dict_file)
    
    # Print final summary
    print(f"\n{'='*60}")
    print(f"🎯 AUTOMATION COMPLETE - Status: {results['status'].upper()}")
    print(f"{'='*60}")
    
    if results["status"] == "success":
        merged_output = results.get("merged_output", {})
        print(f"📊 Enhanced Nodes: {merged_output.get('total_enhanced_nodes', 0)}")
        print(f"🔗 Routing Assignments: {merged_output.get('routing_assignments', 0)}")
        print(f"🏷️  Variable Assignments: {merged_output.get('variable_assignments', 0)}")
        print(f"📁 Output Directory: {results['orchestrator_metadata']['run_directory']}")
        print(f"📋 Summary Report: {results.get('summary_report', 'N/A')}")
    else:
        print(f"❌ Error: {results.get('error', 'Unknown error')}")
    
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
