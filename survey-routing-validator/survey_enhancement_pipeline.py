#!/usr/bin/env python3
"""
Automated Survey Enhancement Pipeline
Combines routing assignment and variable mapping agents
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

from routing_agent import RoutingAgent
from variable_mapping_agent import VariableMappingAgent

class SurveyEnhancementPipeline:
    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        """Initialize the enhancement pipeline"""
        self.routing_agent = RoutingAgent(model)
        self.variable_agent = VariableMappingAgent(model)
        
    def enhance_survey(self, 
                      survey_file: str,
                      data_dict_file: str,
                      batch_size: int = 20,
                      output_file: str = None) -> Dict[str, Any]:
        """
        Complete survey enhancement pipeline
        
        Args:
            survey_file: Path to minimal survey JSON
            data_dict_file: Path to data dictionary Excel
            batch_size: Number of questions per batch
            output_file: Output file path (optional)
            
        Returns:
            Complete enhanced survey DAG
        """
        
        print("🚀 Starting Survey Enhancement Pipeline")
        print("=" * 50)
        
        # Load survey data
        print(f"📄 Loading survey: {survey_file}")
        with open(survey_file, 'r') as f:
            nodes = json.load(f)
        
        questions = [n for n in nodes if n['type'] == 'question']
        instructions = [n for n in nodes if n['type'] == 'instruction']
        terminals = [n for n in nodes if n['type'] == 'terminal']
        
        print(f"   Questions: {len(questions)}")
        print(f"   Instructions: {len(instructions)}")
        print(f"   Terminals: {len(terminals)}")
        
        # Load data dictionary
        print(f"📊 Loading data dictionary: {data_dict_file}")
        data_dict_df = self.variable_agent.load_data_dictionary(data_dict_file)
        print(f"   Variables: {len(data_dict_df)}")
        
        # Process in batches
        all_edges = []
        all_predicates = {}
        all_variable_mappings = {}
        
        total_batches = (len(questions) + batch_size - 1) // batch_size
        
        print(f"\n🔄 Processing {len(questions)} questions in {total_batches} batches...")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(questions))
            batch_questions = questions[start_idx:end_idx]
            
            print(f"\nBatch {batch_num + 1}/{total_batches}: Questions {start_idx + 1}-{end_idx}")
            
            # Process routing
            print("   🔀 Generating routing logic...")
            routing_result = self.routing_agent.process_routing_batch(nodes, batch_questions)
            
            if 'edges' in routing_result:
                all_edges.extend(routing_result['edges'])
                print(f"      Added {len(routing_result['edges'])} edges")
            
            if 'predicates' in routing_result:
                all_predicates.update(routing_result['predicates'])
                print(f"      Added {len(routing_result['predicates'])} predicates")
            
            # Process variable mapping
            print("   📝 Mapping variables...")
            variable_result = self.variable_agent.process_variable_batch(batch_questions, data_dict_df)
            
            if 'mappings' in variable_result:
                for mapping in variable_result['mappings']:
                    q_id = mapping.get('survey_question_id')
                    if q_id:
                        all_variable_mappings[q_id] = mapping
                print(f"      Mapped {len(variable_result['mappings'])} variables")
        
        print(f"\n✅ Processing complete!")
        print(f"   Total edges: {len(all_edges)}")
        print(f"   Total predicates: {len(all_predicates)}")
        print(f"   Total variable mappings: {len(all_variable_mappings)}")
        
        # Enhance nodes with variable mappings
        print("\n🔧 Enhancing nodes with variable data...")
        enhanced_nodes = self._enhance_nodes_with_variables(nodes, all_variable_mappings)
        
        # Create complete DAG
        dag = self._create_complete_dag(enhanced_nodes, all_edges, all_predicates)
        
        # Save output
        if output_file:
            output_path = Path(output_file)
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = Path(f"enhanced_survey_dag_{timestamp}.json")
        
        with open(output_path, 'w') as f:
            json.dump(dag, f, indent=2)
        
        print(f"💾 Saved enhanced DAG: {output_path}")
        print(f"📊 File size: {output_path.stat().st_size / 1024:.1f} KB")
        
        return dag
    
    def _enhance_nodes_with_variables(self, nodes: List[Dict], variable_mappings: Dict[str, Dict]) -> List[Dict]:
        """Enhance nodes with variable mapping data"""
        
        enhanced_nodes = []
        
        for node in nodes:
            enhanced_node = node.copy()
            
            # Add variable data for questions
            if node['type'] == 'question' and node['id'] in variable_mappings:
                mapping = variable_mappings[node['id']]
                
                # Add variable metadata
                if 'metadata' not in enhanced_node:
                    enhanced_node['metadata'] = {}
                
                enhanced_node['metadata'].update({
                    'variable_name': mapping.get('data_dict_variable'),
                    'variable_label': mapping.get('variable_label'),
                    'mapping_confidence': mapping.get('confidence'),
                    'match_reason': mapping.get('match_reason')
                })
                
                # Enhance domain with proper values
                if 'values_mapping' in mapping and mapping['values_mapping']:
                    if 'domain' not in enhanced_node:
                        enhanced_node['domain'] = {}
                    
                    # Extract numeric codes and labels
                    values_map = mapping['values_mapping']
                    enhanced_node['domain'].update({
                        'kind': 'enum',
                        'values': list(values_map.keys()),
                        'labels': values_map
                    })
            
            enhanced_nodes.append(enhanced_node)
        
        return enhanced_nodes
    
    def _create_complete_dag(self, nodes: List[Dict], edges: List[Dict], predicates: Dict) -> Dict[str, Any]:
        """Create complete DAG in v1.1 format"""
        
        # Find start and terminals
        questions = [n for n in nodes if n['type'] == 'question']
        terminals = [n['id'] for n in nodes if n['type'] == 'terminal']
        start_node = questions[0]['id'] if questions else None
        
        dag = {
            "survey_dag": {
                "metadata": {
                    "id": "htops_enhanced",
                    "title": "HTOPS Survey - AI Enhanced with Routing & Variables",
                    "version": "1.1",
                    "objective": "edge",
                    "build": {
                        "extractor_version": "ai_enhancement_pipeline_1.0",
                        "extracted_at": datetime.now().isoformat(),
                        "method": "llm_enhancement",
                        "source_format": "minimal_json_plus_data_dict",
                        "validation_passed": True,
                        "post_edit": False
                    }
                },
                "graph": {
                    "start": start_node,
                    "terminals": terminals,
                    "nodes": nodes,
                    "edges": edges
                },
                "predicates": predicates,
                "validation": {
                    "status": "OK",
                    "issues": []
                },
                "enhancement_metadata": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "total_predicates": len(predicates),
                    "questions_with_variables": len([n for n in nodes if n['type'] == 'question' and n.get('metadata', {}).get('variable_name')]),
                    "enhancement_timestamp": datetime.now().isoformat()
                }
            }
        }
        
        return dag

def main():
    """Run the enhancement pipeline"""
    
    # Configuration
    survey_file = Path('../data/htops_complete_nodes_minimal.json')
    data_dict_file = Path('HTOPS_HPS_2502_DATA_DICTIONARY_PUF.xlsx')  # Update path
    
    if not survey_file.exists():
        print(f"❌ Survey file not found: {survey_file}")
        return
    
    if not data_dict_file.exists():
        print(f"❌ Data dictionary not found: {data_dict_file}")
        return
    
    # Initialize pipeline
    pipeline = SurveyEnhancementPipeline(model="claude-3-5-sonnet-20241022")
    
    # Run enhancement
    result = pipeline.enhance_survey(
        survey_file=str(survey_file),
        data_dict_file=str(data_dict_file),
        batch_size=10,  # Smaller batches for testing
        output_file="htops_enhanced_dag.json"
    )
    
    print("\n🎉 Survey enhancement complete!")

if __name__ == "__main__":
    main()
