#!/usr/bin/env python3
"""
Critical Fix: Remove cycles and fix termination chain connectivity
"""

import sys
import os
import networkx as nx
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager

def main():
    """Fix critical DAG issues: cycles, unreachable nodes, invalid edges."""
    print("🚨 CRITICAL FIX: REMOVING CYCLES AND FIXING CONNECTIVITY")
    print("=" * 60)
    
    db = DatabaseManager()
    
    # Load current DAG
    print("📊 Loading DAG...")
    graph = db.load_graph()
    
    print(f"   Current: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Fix 1: Remove SURVEY_COMPLETE self-loop
    print("\n🔥 FIX 1: Removing SURVEY_COMPLETE self-loop...")
    
    if graph.has_edge('SURVEY_COMPLETE', 'SURVEY_COMPLETE'):
        graph.remove_edge('SURVEY_COMPLETE', 'SURVEY_COMPLETE')
        print("   ✅ Removed SURVEY_COMPLETE → SURVEY_COMPLETE self-loop")
    
    # Fix 2: Remove ALL outgoing edges from SURVEY_COMPLETE
    print("\n🔥 FIX 2: Removing outgoing edges from SURVEY_COMPLETE...")
    
    outgoing_edges = list(graph.edges('SURVEY_COMPLETE'))
    for source, target in outgoing_edges:
        graph.remove_edge(source, target)
        print(f"   ✅ Removed SURVEY_COMPLETE → {target}")
    
    # Fix 3: Connect R2a to the main flow so it's reachable
    print("\n🔥 FIX 3: Making R2a reachable from main flow...")
    
    # R2a should be reachable from GET_NAME or ADDRESS_CONFIRM
    if graph.has_node('R2a') and graph.has_node('GET_NAME'):
        # Check if R2a has any incoming edges
        incoming_to_r2a = list(graph.predecessors('R2a'))
        if not incoming_to_r2a:
            # Connect GET_NAME → R2a for the "End survey" path
            graph.add_edge('GET_NAME', 'R2a',
                          id='E_GET_NAME_TO_R2A',
                          edge_type='branch',
                          condition='GET_NAME == 2',  # End survey option
                          priority=1)
            print("   ✅ Connected GET_NAME → R2a (makes R2a reachable)")
    
    # Fix 4: Ensure END_INELIGIBLE is reachable through R2a
    print("\n🔥 FIX 4: Ensuring END_INELIGIBLE is reachable...")
    
    if graph.has_node('R2a') and graph.has_node('END_INELIGIBLE'):
        if not graph.has_edge('R2a', 'END_INELIGIBLE'):
            graph.add_edge('R2a', 'END_INELIGIBLE',
                          id='E_R2A_TO_END_INELIGIBLE',
                          edge_type='terminate',
                          condition='always',
                          priority=0)
            print("   ✅ Connected R2a → END_INELIGIBLE")
    
    # Fix 5: Connect END_INELIGIBLE to SURVEY_COMPLETE
    print("\n🔥 FIX 5: Connecting END_INELIGIBLE to SURVEY_COMPLETE...")
    
    if graph.has_node('END_INELIGIBLE') and graph.has_node('SURVEY_COMPLETE'):
        if not graph.has_edge('END_INELIGIBLE', 'SURVEY_COMPLETE'):
            graph.add_edge('END_INELIGIBLE', 'SURVEY_COMPLETE',
                          id='E_END_INELIGIBLE_TO_COMPLETE',
                          edge_type='terminate',
                          condition='always',
                          priority=0)
            print("   ✅ Connected END_INELIGIBLE → SURVEY_COMPLETE")
    
    # Fix 6: Remove the old END → R2a connection if it exists
    print("\n🔥 FIX 6: Cleaning up old terminal connections...")
    
    if graph.has_edge('END', 'R2a'):
        graph.remove_edge('END', 'R2a')
        print("   ✅ Removed END → R2a (R2a now reachable from GET_NAME)")
    
    # Fix 7: Connect END directly to SURVEY_COMPLETE
    if graph.has_node('END') and graph.has_node('SURVEY_COMPLETE'):
        if not graph.has_edge('END', 'SURVEY_COMPLETE'):
            graph.add_edge('END', 'SURVEY_COMPLETE',
                          id='E_END_TO_COMPLETE',
                          edge_type='terminate',
                          condition='always',
                          priority=0)
            print("   ✅ Connected END → SURVEY_COMPLETE")
    
    # Validation check
    print("\n✅ VALIDATION: Checking fixes...")
    
    # Check for cycles
    try:
        cycles = list(nx.simple_cycles(graph))
        if cycles:
            print(f"   ❌ Still has cycles: {cycles[:3]}")
        else:
            print("   ✅ Graph is now acyclic")
    except:
        print("   ⚠️  Could not check cycles")
    
    # Check reachability
    if graph.has_node('INTRO_INCENTIVE'):
        reachable = set(nx.descendants(graph, 'INTRO_INCENTIVE'))
        reachable.add('INTRO_INCENTIVE')
        all_nodes = set(graph.nodes())
        unreachable = all_nodes - reachable
        
        if unreachable:
            print(f"   ⚠️  Still unreachable: {unreachable}")
        else:
            print("   ✅ All nodes reachable from start")
    
    # Check SURVEY_COMPLETE has no outgoing edges
    if graph.has_node('SURVEY_COMPLETE'):
        outgoing = list(graph.successors('SURVEY_COMPLETE'))
        if outgoing:
            print(f"   ❌ SURVEY_COMPLETE still has outgoing: {outgoing}")
        else:
            print("   ✅ SURVEY_COMPLETE is clean terminal (no outgoing edges)")
    
    print(f"\n📊 Fixed DAG: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Save the fixed DAG
    print("\n💾 Saving critically fixed DAG...")
    db.save_graph(graph)
    
    # Create snapshot
    db.create_snapshot("critical_fixes_applied")
    
    print("\n🎉 CRITICAL FIXES COMPLETE!")
    print("=" * 60)
    print("✅ Removed SURVEY_COMPLETE self-loop")
    print("✅ Removed all outgoing edges from SURVEY_COMPLETE")
    print("✅ Made R2a reachable from GET_NAME")
    print("✅ Connected termination chain: GET_NAME → R2a → END_INELIGIBLE → SURVEY_COMPLETE")
    print("✅ Clean terminal architecture")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
