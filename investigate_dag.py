#!/usr/bin/env python3
"""
Quick diagnostic script to investigate remaining DAG issues
"""

import sys
import pickle
from pathlib import Path
import networkx as nx

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

def investigate_dag_issues():
    """Investigate remaining DAG connectivity issues."""
    
    project_root = Path(__file__).parent
    db_path = project_root / "surveys_db" / "phase3_output" / "phase3_working_database.pkl"
    
    print("DAG ISSUE INVESTIGATION")
    print("=" * 40)
    
    # Load database
    with open(db_path, 'rb') as f:
        extractor = pickle.load(f)
    
    print(f"📊 Database: {len(extractor.nodes)} nodes, {extractor.graph.number_of_edges()} edges")
    
    # Find unreachable nodes
    questions = [n for n in extractor.nodes if n['type'] == 'question']
    start_node = min(questions, key=lambda x: x.get('order_index', 0))['id'] if questions else None
    
    if start_node:
        reachable = set(nx.descendants(extractor.graph, start_node))
        reachable.add(start_node)
        
        unreachable_nodes = [n['id'] for n in extractor.nodes if n['id'] not in reachable]
        
        print(f"\\n🔍 UNREACHABLE NODES: {len(unreachable_nodes)}")
        
        for node_id in unreachable_nodes:
            node = next((n for n in extractor.nodes if n['id'] == node_id), None)
            if node:
                print(f"\\n📝 {node_id}:")
                print(f"   Type: {node['type']}")
                print(f"   Text: {node.get('text', 'No text')[:80]}...")
                print(f"   Order: {node.get('order_index', 'No order')}")
                
                # Check connections
                predecessors = list(extractor.graph.predecessors(node_id))
                successors = list(extractor.graph.successors(node_id))
                
                print(f"   Incoming edges: {predecessors}")
                print(f"   Outgoing edges: {successors}")
                
                # Check if it's truly isolated or just unreachable
                if not predecessors and not successors:
                    print(f"   🔴 ISOLATED - No connections at all")
                elif predecessors and not successors:
                    print(f"   🟡 TERMINAL - Has incoming but no outgoing")
                elif not predecessors and successors:
                    print(f"   🟡 SOURCE - Has outgoing but no incoming") 
                else:
                    print(f"   🟢 CONNECTED - Has both incoming and outgoing")
    
    # Check components
    components = list(nx.weakly_connected_components(extractor.graph))
    print(f"\\n🔗 COMPONENTS: {len(components)}")
    
    for i, component in enumerate(components):
        print(f"   Component {i+1}: {len(component)} nodes")
        if len(component) < 5:  # Show small components
            component_nodes = []
            for node_id in component:
                node = next((n for n in extractor.nodes if n['id'] == node_id), None)
                if node:
                    component_nodes.append(f"{node_id}({node['type']})")
            print(f"      {', '.join(component_nodes)}")
    
    # Specific investigations
    print(f"\\n🎯 SPECIFIC CHECKS:")
    
    # Check survey completion path
    if extractor.graph.has_node('RECONTACT') and extractor.graph.has_node('SURVEY_COMPLETE'):
        has_completion_path = nx.has_path(extractor.graph, 'RECONTACT', 'SURVEY_COMPLETE')
        print(f"   RECONTACT → SURVEY_COMPLETE: {'✅' if has_completion_path else '❌'}")
    
    # Check if FINAL_TERMINATION is reachable
    if extractor.graph.has_node('FINAL_TERMINATION'):
        ft_predecessors = list(extractor.graph.predecessors('FINAL_TERMINATION'))
        print(f"   FINAL_TERMINATION incoming: {ft_predecessors}")
        if start_node:
            ft_reachable = nx.has_path(extractor.graph, start_node, 'FINAL_TERMINATION') if start_node != 'FINAL_TERMINATION' else True
            print(f"   FINAL_TERMINATION reachable: {'✅' if ft_reachable else '❌'}")
    
    print(f"\\n" + "=" * 40)

if __name__ == "__main__":
    investigate_dag_issues()
