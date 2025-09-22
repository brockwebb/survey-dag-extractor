#!/usr/bin/env python3
"""
Proper Survey Analysis - Questions vs Nodes, Universe Grouping
"""

import sys
import os
import networkx as nx
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager
from config.dag_config import DAGConfig

def analyze_survey_properly():
    """Analyze actual questions vs nodes, and universe combinations."""
    print("🔍 PROPER SURVEY ANALYSIS: QUESTIONS VS NODES")
    print("=" * 60)
    
    db = DatabaseManager()
    config = DAGConfig()
    graph = db.load_graph()
    
    start_node = config.get_start_node()
    completion_terminals = config.get_completion_terminals()
    
    # Step 1: Classify node types
    print("📊 ANALYZING NODE TYPES...")
    node_classifications = {
        'questions': [],
        'instructions': [], 
        'intro_sections': [],
        'navigation': [],
        'terminals': [],
        'other': []
    }
    
    for node_id in graph.nodes():
        node_data = graph.nodes[node_id]
        node_type = node_data.get('type', 'unknown')
        block = node_data.get('block', 'unknown').lower()
        
        # Classify based on type and block
        if node_type == 'question':
            node_classifications['questions'].append(node_id)
        elif node_type in ['terminal', 'ultimate_terminal']:
            node_classifications['terminals'].append(node_id)
        elif any(keyword in block for keyword in ['intro', 'incentive', 'welcome']):
            node_classifications['intro_sections'].append(node_id)
        elif any(keyword in block for keyword in ['instruction', 'info', 'display']):
            node_classifications['instructions'].append(node_id)
        elif any(keyword in node_id.lower() for keyword in ['continue', 'next', 'nav']):
            node_classifications['navigation'].append(node_id)
        else:
            node_classifications['other'].append(node_id)
    
    # Print node type breakdown
    print("\\n📋 NODE TYPE BREAKDOWN:")
    total_nodes = sum(len(nodes) for nodes in node_classifications.values())
    for category, nodes in node_classifications.items():
        pct = (len(nodes) / total_nodes) * 100 if total_nodes > 0 else 0
        print(f"   {category.capitalize()}: {len(nodes)} nodes ({pct:.1f}%)")
        if len(nodes) <= 10:  # Show small categories
            print(f"      {nodes}")
    
    # Step 2: Analyze paths with question-only counts
    print("\\n🎯 ANALYZING COMPLETION PATHS (QUESTION COUNT ONLY)...")
    
    completion_paths = []
    for terminal in completion_terminals:
        if graph.has_node(terminal):
            paths = list(nx.all_simple_paths(graph, start_node, terminal, cutoff=200))
            completion_paths.extend(paths)
    
    print(f"   Found {len(completion_paths)} completion paths")
    
    # Count questions only in each path
    question_counts = []
    path_details = []
    
    for i, path in enumerate(completion_paths[:1000]):  # Limit to first 1000 for performance
        questions_in_path = [node for node in path if node in node_classifications['questions']]
        question_count = len(questions_in_path)
        question_counts.append(question_count)
        
        path_details.append({
            'path_id': i,
            'total_nodes': len(path),
            'question_nodes': question_count,
            'intro_nodes': len([n for n in path if n in node_classifications['intro_sections']]),
            'instruction_nodes': len([n for n in path if n in node_classifications['instructions']]),
            'navigation_nodes': len([n for n in path if n in node_classifications['navigation']]),
            'other_nodes': len([n for n in path if n in node_classifications['other']]),
            'first_5_nodes': path[:5],
            'last_5_nodes': path[-5:] if len(path) > 5 else path
        })
    
    if question_counts:
        q_counts = np.array(question_counts)
        print(f"\\n📊 ACTUAL QUESTION COUNT ANALYSIS (Sample of {len(question_counts)} paths):")
        print(f"   📏 Question counts:")
        print(f"      Mean: {np.mean(q_counts):.2f} questions")
        print(f"      Std Dev: {np.std(q_counts):.2f} questions")
        print(f"      Std Error: {np.std(q_counts)/np.sqrt(len(q_counts)):.3f} questions")
        print(f"      Min: {np.min(q_counts)} questions")
        print(f"      Max: {np.max(q_counts)} questions")
        print(f"      Median: {np.median(q_counts):.2f} questions")
        
        # Estimated time based on questions only (30 seconds per question)
        times_minutes = q_counts * 0.5  # 30 seconds = 0.5 minutes
        print(f"   ⏱️  Estimated completion times (30 sec/question):")
        print(f"      Mean: {np.mean(times_minutes):.2f} ± {np.std(times_minutes):.2f} minutes")
        print(f"      Range: {np.min(times_minutes):.2f} - {np.max(times_minutes):.2f} minutes")
        
        # Show most common question counts
        q_counter = Counter(question_counts)
        print(f"\\n📈 Most common question counts:")
        for count, frequency in q_counter.most_common(5):
            pct = (frequency / len(question_counts)) * 100
            print(f"      {count} questions: {frequency} paths ({pct:.1f}%)")
    
    # Step 3: Universe Analysis - Group paths by skip logic patterns
    print("\\n🌐 UNIVERSE ANALYSIS - GROUPING BY SKIP LOGIC...")
    
    # For universe analysis, we need to look at the conditional edges/nodes
    universe_signatures = defaultdict(list)
    
    # Sample paths for universe analysis (performance)
    sample_size = min(1000, len(completion_paths))
    sample_paths = completion_paths[:sample_size]
    
    for i, path in enumerate(sample_paths):
        # Create universe signature based on branching nodes in path
        universe_signature = create_universe_signature(graph, path)
        universe_signatures[universe_signature].append(i)
    
    print(f"   📊 Universe analysis (sample of {sample_size} paths):")
    print(f"   🌍 Unique universes found: {len(universe_signatures)}")
    
    # Show universe distribution
    universe_sizes = [len(paths) for paths in universe_signatures.values()]
    universe_sizes_array = np.array(universe_sizes)
    
    print(f"\\n📈 Universe size distribution:")
    print(f"   Mean paths per universe: {np.mean(universe_sizes_array):.2f}")
    print(f"   Largest universe: {np.max(universe_sizes_array)} paths")
    print(f"   Smallest universe: {np.min(universe_sizes_array)} paths")
    
    # Show top universes
    sorted_universes = sorted(universe_signatures.items(), key=lambda x: len(x[1]), reverse=True)
    print(f"\\n🏆 TOP 5 UNIVERSES (by path count):")
    for i, (signature, path_indices) in enumerate(sorted_universes[:5]):
        path_count = len(path_indices)
        pct = (path_count / sample_size) * 100
        print(f"      Universe {i+1}: {path_count} paths ({pct:.1f}%)")
        print(f"         Signature: {signature[:100]}...")  # Truncate long signatures
        
        # Show question count stats for this universe
        universe_q_counts = [question_counts[j] for j in path_indices if j < len(question_counts)]
        if universe_q_counts:
            print(f"         Questions: {np.mean(universe_q_counts):.1f} ± {np.std(universe_q_counts):.1f}")
    
    # Step 4: Path composition analysis
    print("\\n📋 PATH COMPOSITION ANALYSIS (Sample paths):")
    
    if path_details:
        # Average composition
        avg_total = np.mean([p['total_nodes'] for p in path_details])
        avg_questions = np.mean([p['question_nodes'] for p in path_details])
        avg_intro = np.mean([p['intro_nodes'] for p in path_details])
        avg_instructions = np.mean([p['instruction_nodes'] for p in path_details])
        avg_navigation = np.mean([p['navigation_nodes'] for p in path_details])
        avg_other = np.mean([p['other_nodes'] for p in path_details])
        
        print(f"   📊 Average path composition:")
        print(f"      Total nodes: {avg_total:.1f}")
        print(f"      Questions: {avg_questions:.1f} ({(avg_questions/avg_total)*100:.1f}%)")
        print(f"      Intro sections: {avg_intro:.1f} ({(avg_intro/avg_total)*100:.1f}%)")
        print(f"      Instructions: {avg_instructions:.1f} ({(avg_instructions/avg_total)*100:.1f}%)")
        print(f"      Navigation: {avg_navigation:.1f} ({(avg_navigation/avg_total)*100:.1f}%)")
        print(f"      Other: {avg_other:.1f} ({(avg_other/avg_total)*100:.1f}%)")
        
        # Show a few example path breakdowns
        print(f"\\n🛤️  EXAMPLE PATH BREAKDOWNS:")
        for i, details in enumerate(path_details[:3]):
            print(f"      Path {i+1} ({details['total_nodes']} total nodes):")
            print(f"         Questions: {details['question_nodes']}")
            print(f"         Start: {' → '.join(details['first_5_nodes'])}")
            print(f"         End: {' → '.join(details['last_5_nodes'])}")

def create_universe_signature(graph, path):
    """Create a signature for universe grouping based on branching decisions."""
    signature_parts = []
    
    # Look for key branching nodes and their conditions
    for i, node in enumerate(path[:-1]):  # Exclude terminal
        next_node = path[i + 1]
        
        if graph.has_edge(node, next_node):
            edge_data = graph.edges[node, next_node]
            condition = edge_data.get('condition', 'always')
            
            # Only include non-trivial conditions for signature
            if condition != 'always' and condition != 'true':
                signature_parts.append(f"{node}:{condition}")
        
        # Also consider nodes with high out-degree (decision points)
        if graph.out_degree(node) > 2:
            signature_parts.append(f"BRANCH_{node}_{next_node}")
    
    # Create signature string
    if signature_parts:
        return "|".join(signature_parts[:10])  # Limit signature length
    else:
        return "default_universe"

if __name__ == "__main__":
    analyze_survey_properly()
