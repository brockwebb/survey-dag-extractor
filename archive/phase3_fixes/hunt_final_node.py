#!/usr/bin/env python3
"""
Final Node Hunter - Find and Fix the Last Unreachable Node

Uses single source of truth database to identify and correct
the remaining connectivity issue.
"""

import sys
from pathlib import Path
import networkx as nx

sys.path.append(str(Path(__file__).parent))
from database_manager import DatabaseManager

def analyze_final_issue(graph):
    """Detailed analysis of the remaining connectivity problem."""
    print("🔍 HUNTING THE ROGUE NODE")
    print("=" * 40)
    
    # Basic connectivity
    print(f"📊 Graph Stats:")
    print(f"   Nodes: {graph.number_of_nodes()}")
    print(f"   Edges: {graph.number_of_edges()}")
    print(f"   Components: {nx.number_weakly_connected_components(graph)}")
    
    # Find isolated nodes
    isolated = list(nx.isolates(graph))
    print(f"   Isolated: {len(isolated)}")
    if isolated:
        print(f"   Isolated nodes: {isolated}")
    
    # Find start node and trace reachability
    all_nodes = list(graph.nodes())
    question_nodes = [(n, graph.nodes[n].get('order_index', 999)) 
                     for n in all_nodes 
                     if graph.nodes[n].get('type') == 'question']
    
    if question_nodes:
        start_node = min(question_nodes, key=lambda x: x[1])[0]
        print(f"   Start node: {start_node}")
        
        reachable = set(nx.descendants(graph, start_node))
        reachable.add(start_node)
        unreachable = [n for n in all_nodes if n not in reachable]
        
        print(f"   Reachable: {len(reachable)}/{len(all_nodes)}")
        print(f"   Unreachable: {len(unreachable)}")
        
        if unreachable:
            print(f"\n🎯 UNREACHABLE NODES:")
            for node in unreachable:
                node_data = graph.nodes[node]
                node_type = node_data.get('type', 'unknown')
                order_idx = node_data.get('order_index', 'N/A')
                text_preview = node_data.get('text', '')[:50] + '...' if len(node_data.get('text', '')) > 50 else node_data.get('text', '')
                
                print(f"   {node} ({node_type}, order:{order_idx})")
                print(f"      Text: {text_preview}")
                
                # Check what points to it
                predecessors = list(graph.predecessors(node))
                successors = list(graph.successors(node))
                print(f"      In-edges: {len(predecessors)} {predecessors}")
                print(f"      Out-edges: {len(successors)} {successors}")
                print()
        
        return {
            'start_node': start_node,
            'unreachable': unreachable,
            'isolated': isolated,
            'components': nx.number_weakly_connected_components(graph)
        }
    
    return {'unreachable': [], 'isolated': isolated}

def suggest_fix(graph, analysis):
    """Suggest specific fix for the unreachable node(s)."""
    unreachable = analysis.get('unreachable', [])
    
    if not unreachable:
        print("✅ No unreachable nodes found!")
        return None
    
    print("💡 SUGGESTED FIXES:")
    print("=" * 40)
    
    fixes = []
    
    for node in unreachable:
        node_data = graph.nodes[node]
        node_type = node_data.get('type', 'unknown')
        order_idx = node_data.get('order_index', 999)
        
        print(f"\n🔧 Node: {node} ({node_type})")
        
        if node_type == 'question':
            # Find the previous question by order_index
            all_questions = [(n, graph.nodes[n].get('order_index', 999)) 
                           for n in graph.nodes() 
                           if graph.nodes[n].get('type') == 'question' and n != node]
            
            # Find closest preceding question
            preceding = [q for q in all_questions if q[1] < order_idx]
            if preceding:
                prev_question = max(preceding, key=lambda x: x[1])[0]
                fixes.append({
                    'source': prev_question,
                    'target': node,
                    'condition': 'always',
                    'type': 'fallthrough',
                    'reason': f'Sequential flow: Q{order_idx-1} -> Q{order_idx}'
                })
                print(f"   → Connect from previous question: {prev_question}")
            
        elif node_type == 'instruction':
            # Instructions should connect to next question in same block
            block = node_data.get('block', '')
            next_questions = [(n, graph.nodes[n].get('order_index', 999)) 
                            for n in graph.nodes() 
                            if (graph.nodes[n].get('type') == 'question' 
                                and graph.nodes[n].get('block') == block
                                and graph.nodes[n].get('order_index', 999) > order_idx)]
            
            if next_questions:
                next_question = min(next_questions, key=lambda x: x[1])[0]
                fixes.append({
                    'source': node,
                    'target': next_question,
                    'condition': 'always', 
                    'type': 'fallthrough',
                    'reason': f'Instruction header to first question in {block} block'
                })
                print(f"   → Connect to next question in block: {next_question}")
        
        elif node_type in ['terminal', 'ultimate_terminal']:
            # Terminals should be reachable from some question
            print(f"   → Terminal should be connected from completion path")
            # This might be intentionally unreachable (like error terminals)
    
    return fixes

def apply_fix(graph, fix):
    """Apply a single fix to the graph."""
    source = fix['source']
    target = fix['target']
    condition = fix['condition']
    edge_type = fix['type']
    
    if not graph.has_node(source):
        print(f"   ❌ Source node {source} not found")
        return False
    if not graph.has_node(target):
        print(f"   ❌ Target node {target} not found") 
        return False
    
    # Generate edge ID
    edge_count = graph.number_of_edges()
    edge_id = f"E_{edge_count:08d}"
    
    # Add edge
    graph.add_edge(source, target,
                  id=edge_id,
                  condition=condition,
                  edge_type=edge_type)
    
    print(f"   ✅ Added: {source} → {target} ({condition})")
    return True

def main():
    """Hunt down and fix the final unreachable node."""
    print("FINAL NODE HUNTER")
    print("=" * 50)
    
    # Load current database
    db = DatabaseManager()
    
    try:
        graph = db.load_graph()
        print(f"✅ Loaded current database")
    except Exception as e:
        print(f"❌ Failed to load database: {e}")
        return
    
    # Create checkpoint before hunting
    db.create_snapshot("before_final_fix")
    
    # Analyze the issue
    analysis = analyze_final_issue(graph)
    
    # Suggest fixes
    fixes = suggest_fix(graph, analysis)
    
    if not fixes:
        print("\n🎉 Graph appears to be fully connected!")
        return
    
    print(f"\n🔧 APPLYING FIXES:")
    print("=" * 40)
    
    fixes_applied = 0
    for fix in fixes:
        print(f"\nFix {fixes_applied + 1}: {fix['reason']}")
        if apply_fix(graph, fix):
            fixes_applied += 1
    
    if fixes_applied > 0:
        # Save updated graph
        db.save_graph(graph)
        print(f"\n💾 Saved {fixes_applied} fixes to database")
        
        # Re-analyze to verify fix
        print(f"\n🔍 VERIFICATION:")
        print("=" * 40)
        new_analysis = analyze_final_issue(graph)
        
        if len(new_analysis.get('unreachable', [])) == 0:
            print(f"\n🎉 SUCCESS! All nodes are now reachable!")
            db.create_snapshot("fully_connected_final")
        else:
            print(f"\n⚠️  Still have {len(new_analysis['unreachable'])} unreachable nodes")
            print("Additional manual investigation may be needed")
    else:
        print(f"\n⚠️  No fixes could be applied automatically")

if __name__ == "__main__":
    main()
