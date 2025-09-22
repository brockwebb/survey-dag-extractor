#!/usr/bin/env python3
"""
Survey Logic Fixer - Fix broken survey paths in real-time
"""

import sys
import os
import networkx as nx

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.database_manager import DatabaseManager

def debug_address_confirm_logic():
    """Debug the ADDRESS_CONFIRM branching logic."""
    print("DEBUGGING ADDRESS_CONFIRM LOGIC")
    print("=" * 40)
    
    graph = DatabaseManager().load_graph()
    
    if not graph.has_node('ADDRESS_CONFIRM'):
        print("ADDRESS_CONFIRM node not found!")
        return
    
    # Show current logic
    print("CURRENT LOGIC:")
    successors = list(graph.successors('ADDRESS_CONFIRM'))
    print(f"ADDRESS_CONFIRM branches to: {successors}")
    
    for successor in successors:
        if graph.has_edge('ADDRESS_CONFIRM', successor):
            edge_data = graph.edges['ADDRESS_CONFIRM', successor]
            condition = edge_data.get('condition', 'always')
            print(f"  → {successor}: condition = '{condition}'")
    
    # What SHOULD happen
    print(f"\nWHAT SHOULD HAPPEN:")
    print(f"  Answer = 1 (Yes) → Continue to GET_NAME")
    print(f"  Answer = 2 (No) → Go to END_INELIGIBLE")
    
    # Check if END_INELIGIBLE exists and is reachable
    if graph.has_node('END_INELIGIBLE'):
        print(f"\nEND_INELIGIBLE node exists")
        predecessors = list(graph.predecessors('END_INELIGIBLE'))
        print(f"Nodes that lead to END_INELIGIBLE: {predecessors}")
    else:
        print(f"\nEND_INELIGIBLE node MISSING!")
    
    return graph

def fix_address_confirm_logic(graph):
    """Fix the ADDRESS_CONFIRM logic."""
    print(f"\nFIXING ADDRESS_CONFIRM LOGIC...")
    
    db = DatabaseManager()
    
    # Remove existing edges from ADDRESS_CONFIRM
    successors = list(graph.successors('ADDRESS_CONFIRM'))
    for successor in successors:
        graph.remove_edge('ADDRESS_CONFIRM', successor)
        print(f"Removed edge: ADDRESS_CONFIRM → {successor}")
    
    # Add correct edges
    # Yes (1) → GET_NAME
    if graph.has_node('GET_NAME'):
        graph.add_edge('ADDRESS_CONFIRM', 'GET_NAME',
                      id='E_ADDRESS_CONFIRM_YES',
                      edge_type='branch',
                      condition='ADDRESS_CONFIRM == 1',
                      priority=1)
        print(f"Added: ADDRESS_CONFIRM → GET_NAME (condition: ADDRESS_CONFIRM == 1)")
    
    # No (2) → END_INELIGIBLE
    if graph.has_node('END_INELIGIBLE'):
        graph.add_edge('ADDRESS_CONFIRM', 'END_INELIGIBLE',
                      id='E_ADDRESS_CONFIRM_NO',
                      edge_type='terminate',
                      condition='ADDRESS_CONFIRM == 2',
                      priority=2)
        print(f"Added: ADDRESS_CONFIRM → END_INELIGIBLE (condition: ADDRESS_CONFIRM == 2)")
    else:
        print(f"ERROR: END_INELIGIBLE node doesn't exist!")
        return False
    
    # Save the fixed graph
    db.save_graph(graph)
    db.create_snapshot("fixed_address_confirm_logic")
    
    print(f"\nFIX COMPLETE!")
    print(f"ADDRESS_CONFIRM now correctly routes:")
    print(f"  Yes (1) → GET_NAME (continue survey)")
    print(f"  No (2) → END_INELIGIBLE (terminate - wrong address)")
    
    return True

def main():
    """Debug and fix ADDRESS_CONFIRM logic."""
    
    # First, debug the current state
    graph = debug_address_confirm_logic()
    
    print(f"\nDo you want to fix this logic? (y/n): ", end="")
    response = input().strip().lower()
    
    if response == 'y':
        success = fix_address_confirm_logic(graph)
        if success:
            print(f"\nLogic fixed! Try the simulator again:")
            print(f"python survey_simulator.py")
        else:
            print(f"\nFix failed. Check the graph structure.")
    else:
        print(f"No changes made.")

if __name__ == "__main__":
    main()
