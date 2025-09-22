#!/usr/bin/env python3
"""
Quick Survey Section Mapper - Understand structure efficiently
"""

import sys
import os
import networkx as nx
from collections import defaultdict, Counter

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.database_manager import DatabaseManager

def quick_survey_map():
    """Quick efficient survey understanding."""
    print("🗺️ QUICK SURVEY MAPPING")
    print("="*40)
    
    graph = DatabaseManager().load_graph()
    
    # 1. Structural overview
    print(f"📊 Structure: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # 2. Node type breakdown
    types = Counter(graph.nodes[n].get('type', 'unknown') for n in graph.nodes())
    print(f"📋 Types: {dict(types)}")
    
    # 3. Survey sections (blocks)
    blocks = defaultdict(list)
    for n in graph.nodes():
        block = graph.nodes[n].get('block', 'unknown')
        if graph.nodes[n].get('type') == 'question':
            blocks[block].append(n)
    
    print(f"\\n📚 Survey Sections:")
    for block, questions in sorted(blocks.items()):
        if questions:  # Only show blocks with questions
            print(f"   {block}: {len(questions)} questions ({questions[0]}...{questions[-1] if len(questions)>1 else ''})")
    
    # 4. Main survey spine
    try:
        spine = nx.shortest_path(graph, 'INTRO_INCENTIVE', 'SURVEY_COMPLETE')
        spine_questions = [n for n in spine if graph.nodes[n].get('type') == 'question']
        print(f"\\n🎯 Main Survey Spine: {len(spine)} nodes, {len(spine_questions)} questions")
        print(f"   Key questions: {spine_questions[:5]} ... {spine_questions[-5:] if len(spine_questions)>10 else spine_questions[5:]}")
    except:
        print("\\n❌ Can't find main spine")
    
    # 5. Real decision points
    print(f"\\n🔀 Decision Points:")
    decisions = 0
    for node in graph.nodes():
        if graph.out_degree(node) > 1:
            successors = list(graph.successors(node))
            conditions = [graph.edges[node, s].get('condition', 'always') for s in successors]
            
            # Only show if conditions are different (real logic)
            if len(set(conditions)) > 1:
                decisions += 1
                print(f"   {node} ({graph.nodes[node].get('type', '?')})")
                for succ, cond in zip(successors, conditions):
                    print(f"      → {succ}: {cond}")
                if decisions >= 5:  # Limit output
                    break
    
    print(f"\\n✅ Found {decisions} real decision points")

if __name__ == "__main__":
    quick_survey_map()
