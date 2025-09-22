#!/usr/bin/env python3
"""
Debug Survey Flow - Find the ACTUAL survey structure
"""

import sys
import os
import networkx as nx
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager
from config.dag_config import DAGConfig

def debug_survey_flow():
    """Debug the actual survey flow structure."""
    print("🔍 DEBUGGING ACTUAL SURVEY FLOW")
    print("=" * 50)
    
    db = DatabaseManager()
    graph = db.load_graph()
    
    # Step 1: Show the first 20 nodes in survey order
    print("📊 FIRST 20 NODES IN SURVEY ORDER:")
    
    start_node = 'INTRO_INCENTIVE'
    if graph.has_node(start_node):
        # Follow the path manually
        current = start_node
        visited = []
        
        for step in range(20):
            visited.append(current)
            
            node_data = graph.nodes[current]
            node_type = node_data.get('type', 'unknown')
            
            print(f"   {step+1:2d}. {current} ({node_type})")
            
            # Get successors
            successors = list(graph.successors(current))
            if not successors:
                print("      → END (no successors)")
                break
            elif len(successors) == 1:
                current = successors[0]
            else:
                print(f"      → BRANCHES: {successors}")
                # Take first successor for now
                current = successors[0]
    
    # Step 2: Check specific nodes you mentioned
    print(f"\\n🔍 CHECKING SPECIFIC NODES:")
    key_nodes = ['ADDRESS_CONFIRM', 'GET_NAME', 'LANG', 'LANG1_R', 'Q1', 'Language']
    
    for node in key_nodes:
        if graph.has_node(node):
            successors = list(graph.successors(node))
            predecessors = list(graph.predecessors(node))
            node_data = graph.nodes[node]
            node_type = node_data.get('type', 'unknown')
            
            print(f"   ✅ {node} ({node_type})")
            print(f"      From: {predecessors}")
            print(f"      To: {successors}")
            
            # Show edge conditions if branching
            if len(successors) > 1:
                print(f"      Branch conditions:")
                for succ in successors:
                    if graph.has_edge(node, succ):
                        edge_data = graph.edges[node, succ]
                        condition = edge_data.get('condition', 'always')
                        print(f"         → {succ}: {condition}")
        else:
            print(f"   ❌ {node}: NOT FOUND")
    
    # Step 3: Find the actual language routing
    print(f"\\n🗣️ LANGUAGE ROUTING ANALYSIS:")
    
    if graph.has_node('LANG'):
        print("   LANG node found - analyzing routing...")
        
        # Find paths from LANG
        lang_successors = list(graph.successors('LANG'))
        print(f"   LANG branches to: {lang_successors}")
        
        for succ in lang_successors:
            if graph.has_edge('LANG', succ):
                edge_data = graph.edges['LANG', succ]
                condition = edge_data.get('condition', 'always')
                print(f"      → {succ}: {condition}")
    
    # Step 4: Find actual paths to Q1 (mood question)
    print(f"\\n🎯 PATHS TO Q1 (MOOD QUESTION):")
    
    if graph.has_node('Q1'):
        # Find all nodes that lead to Q1
        q1_predecessors = list(graph.predecessors('Q1'))
        print(f"   Nodes that lead to Q1: {q1_predecessors}")
        
        # Try to find different paths to Q1
        for start_candidate in ['ADDRESS_CONFIRM', 'GET_NAME', 'LANG', 'Language']:
            if graph.has_node(start_candidate):
                try:
                    if nx.has_path(graph, start_candidate, 'Q1'):
                        path = nx.shortest_path(graph, start_candidate, 'Q1')
                        print(f"   ✅ {start_candidate} → Q1: {' → '.join(path)}")
                    else:
                        print(f"   ❌ {start_candidate} → Q1: NO PATH")
                except Exception as e:
                    print(f"   ❌ {start_candidate} → Q1: ERROR - {e}")
    else:
        print("   ❌ Q1 node not found!")
    
    # Step 5: Check for multiple paths with language differences
    print(f"\\n🌍 CHECKING FOR LANGUAGE PATH VARIANTS:")
    
    # Look for paths that include LANG1_R (non-English path)
    if graph.has_node('LANG1_R'):
        print("   LANG1_R found - this should be non-English path")
        
        # Find what leads to LANG1_R
        lang1r_predecessors = list(graph.predecessors('LANG1_R'))
        lang1r_successors = list(graph.successors('LANG1_R'))
        
        print(f"      From: {lang1r_predecessors}")
        print(f"      To: {lang1r_successors}")
    else:
        print("   ❌ LANG1_R not found!")
    
    # Step 6: Early exit paths
    print(f"\\n🚪 EARLY EXIT ANALYSIS:")
    
    early_exits = ['END', 'R2a', 'END_INELIGIBLE']
    for exit_node in early_exits:
        if graph.has_node(exit_node):
            predecessors = list(graph.predecessors(exit_node))
            print(f"   ✅ {exit_node} ← {predecessors}")
            
            # Find shortest path from start
            try:
                if nx.has_path(graph, 'INTRO_INCENTIVE', exit_node):
                    path = nx.shortest_path(graph, 'INTRO_INCENTIVE', exit_node)
                    questions = [n for n in path if graph.nodes[n].get('type') == 'question']
                    print(f"      Path: {' → '.join(path[:5])} ... → {exit_node}")
                    print(f"      Questions: {len(questions)} ({questions})")
            except Exception as e:
                print(f"      Path error: {e}")

if __name__ == "__main__":
    debug_survey_flow()
