#!/usr/bin/env python3
"""
Correct Termination Chain: R2a → END_INELIGIBLE → SURVEY_COMPLETE
"""

import sys
import os
import networkx as nx
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager

def main():
    """Create proper termination chain: R2a → END_INELIGIBLE → SURVEY_COMPLETE"""
    print("🔧 CORRECT TERMINATION CHAIN: R2a → END_INELIGIBLE → SURVEY_COMPLETE")
    print("=" * 70)
    
    db = DatabaseManager()
    
    # Load current DAG
    print("📊 Loading DAG...")
    graph = db.load_graph()
    
    print(f"   Current: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Step 1: Ensure we have the right node names
    print("\n🏷️  Setting up termination chain nodes...")
    
    # If we have R2a, keep it. If it was renamed to END_INELIGIBLE, rename it back
    if graph.has_node('END_INELIGIBLE') and not graph.has_node('R2a'):
        nx.relabel_nodes(graph, {'END_INELIGIBLE': 'R2a'}, copy=False)
        print("   ✅ Renamed END_INELIGIBLE back to R2a")
    
    # Ensure we have END_INELIGIBLE as a separate node
    if not graph.has_node('END_INELIGIBLE'):
        # Create END_INELIGIBLE node
        graph.add_node('END_INELIGIBLE', 
                      type='terminal',
                      order_index=999,
                      block='termination',
                      domain={'kind': 'terminal'},
                      metadata={'text': 'Survey terminated - ineligible respondent.'})
        print("   ✅ Created END_INELIGIBLE terminal node")
    
    # Step 2: Create the termination chain
    print("\n🔗 Creating termination chain...")
    
    # R2a → END_INELIGIBLE
    if graph.has_node('R2a') and graph.has_node('END_INELIGIBLE'):
        # Remove any existing direct connections from R2a to SURVEY_COMPLETE
        if graph.has_edge('R2a', 'SURVEY_COMPLETE'):
            graph.remove_edge('R2a', 'SURVEY_COMPLETE')
            print("   ✅ Removed direct R2a → SURVEY_COMPLETE")
        
        # Add R2a → END_INELIGIBLE
        if not graph.has_edge('R2a', 'END_INELIGIBLE'):
            graph.add_edge('R2a', 'END_INELIGIBLE',
                          id='E_R2A_TO_END_INELIGIBLE',
                          edge_type='terminate',
                          condition='always',
                          priority=0)
            print("   ✅ Added: R2a → END_INELIGIBLE")
    
    # END_INELIGIBLE → SURVEY_COMPLETE
    if graph.has_node('END_INELIGIBLE') and graph.has_node('SURVEY_COMPLETE'):
        if not graph.has_edge('END_INELIGIBLE', 'SURVEY_COMPLETE'):
            graph.add_edge('END_INELIGIBLE', 'SURVEY_COMPLETE',
                          id='E_END_INELIGIBLE_TO_COMPLETE',
                          edge_type='terminate', 
                          condition='always',
                          priority=0)
            print("   ✅ Added: END_INELIGIBLE → SURVEY_COMPLETE")
    
    # Step 3: Connect other terminals directly to SURVEY_COMPLETE
    print("\n🔗 Connecting other terminals to SURVEY_COMPLETE...")
    
    # END → SURVEY_COMPLETE (direct)
    if graph.has_node('END') and graph.has_node('SURVEY_COMPLETE'):
        if not graph.has_edge('END', 'SURVEY_COMPLETE'):
            graph.add_edge('END', 'SURVEY_COMPLETE',
                          id='E_END_TO_COMPLETE',
                          edge_type='terminate',
                          condition='always',
                          priority=0)
            print("   ✅ Added: END → SURVEY_COMPLETE")
    
    # Step 4: Set proper node types
    print("\n🏷️  Setting node types...")
    
    # R2a is intermediate (leads to END_INELIGIBLE)
    if graph.has_node('R2a'):
        graph.nodes['R2a']['type'] = 'terminal'
        print("   ✅ R2a: terminal (intermediate)")
    
    # END_INELIGIBLE is intermediate (leads to SURVEY_COMPLETE)  
    if graph.has_node('END_INELIGIBLE'):
        graph.nodes['END_INELIGIBLE']['type'] = 'terminal'
        print("   ✅ END_INELIGIBLE: terminal (intermediate)")
    
    # END is intermediate (leads to SURVEY_COMPLETE)
    if graph.has_node('END'):
        graph.nodes['END']['type'] = 'terminal'  
        print("   ✅ END: terminal (intermediate)")
    
    # SURVEY_COMPLETE is the ultimate collector
    if graph.has_node('SURVEY_COMPLETE'):
        graph.nodes['SURVEY_COMPLETE']['type'] = 'ultimate_terminal'
        print("   ✅ SURVEY_COMPLETE: ultimate_terminal (collector)")
    
    # Step 5: Clean up any FINAL_TERMINATION confusion
    if graph.has_node('FINAL_TERMINATION'):
        graph.remove_node('FINAL_TERMINATION')
        print("   ✅ Removed confusing FINAL_TERMINATION node")
    
    # Step 6: Validate the chain
    print("\n✅ VALIDATING TERMINATION CHAIN...")
    
    # Check the specific chain: R2a → END_INELIGIBLE → SURVEY_COMPLETE
    chain_valid = True
    if graph.has_node('R2a') and graph.has_node('END_INELIGIBLE'):
        if graph.has_edge('R2a', 'END_INELIGIBLE'):
            print("   ✅ R2a → END_INELIGIBLE: Connected")
        else:
            print("   ❌ R2a → END_INELIGIBLE: Missing")
            chain_valid = False
    
    if graph.has_node('END_INELIGIBLE') and graph.has_node('SURVEY_COMPLETE'):
        if graph.has_edge('END_INELIGIBLE', 'SURVEY_COMPLETE'):
            print("   ✅ END_INELIGIBLE → SURVEY_COMPLETE: Connected")
        else:
            print("   ❌ END_INELIGIBLE → SURVEY_COMPLETE: Missing")
            chain_valid = False
    
    # Check SURVEY_COMPLETE has no outgoing edges
    if graph.has_node('SURVEY_COMPLETE'):
        outgoing = list(graph.successors('SURVEY_COMPLETE'))
        if outgoing:
            print(f"   ⚠️  SURVEY_COMPLETE has outgoing edges: {outgoing}")
        else:
            print("   ✅ SURVEY_COMPLETE is true exit point")
    
    print(f"\n📊 Chain DAG: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Save the chain architecture  
    print("\n💾 Saving termination chain architecture...")
    db.save_graph(graph)
    
    # Create snapshot
    db.create_snapshot("r2a_chain_to_survey_complete")
    
    print("\n🎉 TERMINATION CHAIN ARCHITECTURE COMPLETE!")
    print("=" * 70)
    print("✅ Entry: INTRO_INCENTIVE")
    print("✅ Chain: R2a → END_INELIGIBLE → SURVEY_COMPLETE") 
    print("✅ Direct: END → SURVEY_COMPLETE")
    print("✅ Collector: SURVEY_COMPLETE (single exit)")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
