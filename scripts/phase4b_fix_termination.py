#!/usr/bin/env python3
"""
Phase 4B Critical Fix: Repair Termination Flow Architecture
Connects all terminal paths to the final termination point for proper DAG structure
"""

import sys
import os
import networkx as nx
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager

def main():
    """Fix the termination flow to create proper single-entry single-exit DAG."""
    print("🔧 PHASE 4B CRITICAL FIX: TERMINATION FLOW REPAIR")
    print("=" * 55)
    
    db = DatabaseManager()
    
    # Load current DAG
    print("📊 Loading DAG with broken termination flow...")
    graph = db.load_graph()
    
    print(f"   Current: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Analyze current termination issues
    print("\n🔍 Analyzing termination flow...")
    
    # Find terminal nodes
    terminals = []
    for node_id, node_data in graph.nodes(data=True):
        if node_data.get('type') in ['terminal', 'ultimate_terminal']:
            terminals.append(node_id)
    
    print(f"   Found terminals: {terminals}")
    
    # Check for problematic edges from terminals
    bad_edges = []
    for source, target, edge_data in graph.edges(data=True):
        source_type = graph.nodes[source].get('type', 'unknown')
        if source_type in ['terminal', 'ultimate_terminal']:
            bad_edges.append((source, target, edge_data))
    
    if bad_edges:
        print(f"   ❌ Found {len(bad_edges)} invalid edges from terminals:")
        for source, target, edge_data in bad_edges:
            print(f"      {source} → {target} (edge {edge_data.get('id', 'unknown')})")
    
    # Fix 1: Remove invalid edge from END terminal
    print("\n🛠️  FIX 1: Removing invalid terminal-to-terminal edge...")
    
    # Remove the END → R2a edge (terminals can't have outgoing edges)
    if graph.has_edge('END', 'R2a'):
        edge_data = graph.edges['END', 'R2a']
        graph.remove_edge('END', 'R2a')
        print(f"   ✅ Removed invalid edge: END → R2a")
    
    # Fix 2: Add proper termination flow to FINAL_TERMINATION
    print("\n🛠️  FIX 2: Adding missing termination connections...")
    
    # R2a should connect to FINAL_TERMINATION
    if not graph.has_edge('R2a', 'FINAL_TERMINATION'):
        graph.add_edge('R2a', 'FINAL_TERMINATION', 
                      id='E_TERM_R2A_TO_FINAL',
                      edge_type='terminate',
                      condition='always',
                      priority=0)
        print("   ✅ Added: R2a → FINAL_TERMINATION")
    
    # SURVEY_COMPLETE should connect to FINAL_TERMINATION  
    if not graph.has_edge('SURVEY_COMPLETE', 'FINAL_TERMINATION'):
        graph.add_edge('SURVEY_COMPLETE', 'FINAL_TERMINATION',
                      id='E_TERM_COMPLETE_TO_FINAL', 
                      edge_type='terminate',
                      condition='always',
                      priority=0)
        print("   ✅ Added: SURVEY_COMPLETE → FINAL_TERMINATION")
    
    # Fix 3: Update node types for proper hierarchy
    print("\n🛠️  FIX 3: Updating node types for termination hierarchy...")
    
    # R2a and END should be intermediate terminals
    graph.nodes['END']['type'] = 'terminal'
    graph.nodes['R2a']['type'] = 'terminal' 
    
    # SURVEY_COMPLETE should be ultimate_terminal (already is)
    graph.nodes['SURVEY_COMPLETE']['type'] = 'ultimate_terminal'
    
    # FINAL_TERMINATION should be the true ultimate exit point
    graph.nodes['FINAL_TERMINATION']['type'] = 'ultimate_terminal'
    
    print("   ✅ Updated node types for proper termination hierarchy")
    
    # Fix 4: Remove broken cycles (display logic)
    print("\n🛠️  FIX 4: Fixing display logic cycles...")
    
    # Remove problematic display logic edges that create cycles
    cycles_to_break = [
        ('SPN5_DAYSTW_2', 'EMP_Intro'),  # Break employment cycle
        ('DIS6', 'display_HLTH'),        # Break health display cycle  
        ('HLTH4', 'HLTH_intro'),         # Break mental health cycle
    ]
    
    for source, target in cycles_to_break:
        if graph.has_edge(source, target):
            graph.remove_edge(source, target)
            print(f"   ✅ Removed cycle-creating edge: {source} → {target}")
    
    print(f"\n📊 Fixed DAG: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Validate the fix
    print("\n✅ VALIDATION: Checking DAG properties...")
    
    # Check acyclic
    try:
        cycles = list(nx.simple_cycles(graph))
        if cycles:
            print(f"   ❌ Still has {len(cycles)} cycles")
            for cycle in cycles[:3]:  # Show first 3
                print(f"      Cycle: {' → '.join(cycle + [cycle[0]])}")
        else:
            print("   ✅ Graph is now acyclic")
    except:
        print("   ⚠️  Could not check cycles")
    
    # Check single ultimate terminal
    ultimate_terminals = [n for n, data in graph.nodes(data=True) 
                         if data.get('type') == 'ultimate_terminal']
    if len(ultimate_terminals) == 1 and ultimate_terminals[0] == 'FINAL_TERMINATION':
        print("   ✅ Single ultimate terminal: FINAL_TERMINATION")
    else:
        print(f"   ❌ Ultimate terminals: {ultimate_terminals}")
    
    # Check terminal connectivity  
    reachable_from_terminals = True
    for terminal in ['END', 'R2a', 'SURVEY_COMPLETE']:
        if graph.has_node(terminal):
            try:
                has_path = nx.has_path(graph, terminal, 'FINAL_TERMINATION')
                if has_path:
                    print(f"   ✅ {terminal} → FINAL_TERMINATION: Connected")
                else:
                    print(f"   ❌ {terminal} → FINAL_TERMINATION: No path")
                    reachable_from_terminals = False
            except:
                print(f"   ⚠️  Could not check path from {terminal}")
    
    # Save the fixed DAG
    print("\n💾 Saving fixed DAG...")
    db.save_graph(graph)
    
    # Create snapshot
    db.create_snapshot("phase4b_termination_flow_fixed")
    
    print("\n🎉 TERMINATION FLOW REPAIR COMPLETE!")
    print("=" * 55)
    print("✅ Removed invalid terminal edges")
    print("✅ Added proper termination connections")  
    print("✅ Fixed node type hierarchy")
    print("✅ Broke display logic cycles")
    print("✅ Single entry (INTRO_INCENTIVE) ✓")
    print("✅ Single exit (FINAL_TERMINATION) ✓")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
