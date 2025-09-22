#!/usr/bin/env python3
"""
Debug Path Generation - Find out why we're only getting 3 paths
"""

import sys
import os
import networkx as nx
from pathlib import Path
from collections import defaultdict

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager
from config.dag_config import DAGConfig

def debug_path_generation():
    """Debug why path generation is failing."""
    print("🔍 DEBUGGING PATH GENERATION")
    print("=" * 50)
    
    db = DatabaseManager()
    config = DAGConfig()
    graph = db.load_graph()
    
    start_node = config.get_start_node()
    terminals = config.get_all_terminals()
    
    print(f"📊 Graph Stats:")
    print(f"   Nodes: {graph.number_of_nodes()}")
    print(f"   Edges: {graph.number_of_edges()}")
    print(f"   Start: {start_node}")
    print(f"   Terminals: {terminals}")
    
    # Check start node connectivity
    print(f"\\n🔍 Start Node Analysis:")
    if graph.has_node(start_node):
        successors = list(graph.successors(start_node))
        print(f"   {start_node} successors: {successors}")
    else:
        print(f"   ❌ START NODE '{start_node}' NOT FOUND!")
        return
    
    # Check terminal reachability
    print(f"\\n🎯 Terminal Reachability:")
    for terminal in terminals:
        if graph.has_node(terminal):
            try:
                has_path = nx.has_path(graph, start_node, terminal)
                if has_path:
                    shortest = nx.shortest_path(graph, start_node, terminal)
                    print(f"   ✅ {terminal}: reachable ({len(shortest)} nodes)")
                else:
                    print(f"   ❌ {terminal}: NOT REACHABLE")
            except Exception as e:
                print(f"   ❌ {terminal}: ERROR - {e}")
        else:
            print(f"   ❌ {terminal}: NODE NOT FOUND")
    
    # Analyze graph connectivity
    print(f"\\n🕸️  Graph Connectivity:")
    if nx.is_weakly_connected(graph):
        print("   ✅ Graph is weakly connected")
    else:
        components = list(nx.weakly_connected_components(graph))
        print(f"   ❌ Graph has {len(components)} disconnected components")
        for i, comp in enumerate(components):
            print(f"      Component {i}: {len(comp)} nodes")
            if len(comp) < 10:  # Show small components
                print(f"         {list(comp)}")
    
    # Try simple DFS manually
    print(f"\\n🚶 Manual DFS Test:")
    paths_found = []
    
    def simple_dfs(current, path, depth=0):
        if depth > 50:
            print(f"   ⚠️  Hit depth limit at {current}")
            return
        
        path = path + [current]
        
        if current in terminals:
            paths_found.append(path.copy())
            print(f"   ✅ Found path to {current}: {len(path)} nodes")
            return
        
        successors = list(graph.successors(current))
        if not successors:
            print(f"   🛑 Dead end at {current} (not terminal)")
            return
        
        for successor in successors:
            if successor not in path:  # Simple cycle detection
                simple_dfs(successor, path, depth + 1)
    
    simple_dfs(start_node, [])
    print(f"\\n📊 Manual DFS Results: {len(paths_found)} paths found")
    
    # Show the paths found
    for i, path in enumerate(paths_found[:5]):  # First 5 paths
        print(f"   Path {i+1}: {path[0]} → ... → {path[-1]} ({len(path)} nodes)")
    
    # Check for cycles
    print(f"\\n🔄 Cycle Analysis:")
    try:
        cycles = list(nx.simple_cycles(graph))
        print(f"   Found {len(cycles)} cycles")
        for cycle in cycles[:3]:  # Show first 3
            print(f"      Cycle: {' → '.join(cycle + [cycle[0]])}")
    except Exception as e:
        print(f"   Error checking cycles: {e}")
    
    # Analyze out-degree distribution
    print(f"\\n📈 Node Out-Degree Analysis:")
    out_degrees = [graph.out_degree(node) for node in graph.nodes()]
    print(f"   Nodes with 0 out-edges (terminals): {sum(1 for d in out_degrees if d == 0)}")
    print(f"   Nodes with 1 out-edge: {sum(1 for d in out_degrees if d == 1)}")
    print(f"   Nodes with 2+ out-edges (branches): {sum(1 for d in out_degrees if d >= 2)}")
    print(f"   Max out-degree: {max(out_degrees) if out_degrees else 0}")
    
    # Find high out-degree nodes
    high_degree_nodes = [(node, graph.out_degree(node)) for node in graph.nodes() 
                        if graph.out_degree(node) > 3]
    print(f"   High-degree nodes: {high_degree_nodes[:5]}")

if __name__ == "__main__":
    debug_path_generation()
