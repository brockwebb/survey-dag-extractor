#!/usr/bin/env python3
"""
Universal Gates & Test Coverage Strategy Analysis
"""

import sys
import os
import networkx as nx
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager
from config.dag_config import DAGConfig

def analyze_universal_gates_and_coverage():
    """Find universal gates and optimal test coverage strategy."""
    print("🔍 UNIVERSAL GATES & TEST COVERAGE ANALYSIS")
    print("=" * 60)
    
    db = DatabaseManager()
    config = DAGConfig()
    graph = db.load_graph()
    
    start_node = config.get_start_node()
    completion_terminals = config.get_completion_terminals()
    all_terminals = config.get_all_terminals()
    
    print(f"📊 Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Step 1: Find Universal Gates (nodes ALL paths traverse)
    print("\\n🚪 STEP 1: FINDING UNIVERSAL GATES...")
    
    # Get sample of completion paths for analysis
    print("   Sampling completion paths...")
    completion_paths = []
    for terminal in completion_terminals:
        if graph.has_node(terminal):
            paths = list(nx.all_simple_paths(graph, start_node, terminal, cutoff=200))
            completion_paths.extend(paths[:500])  # Sample for performance
    
    print(f"   Analyzing {len(completion_paths)} completion paths...")
    
    # Count how many paths traverse each node
    node_traversal_count = defaultdict(int)
    total_paths = len(completion_paths)
    
    for path in completion_paths:
        visited_nodes = set(path)
        for node in visited_nodes:
            node_traversal_count[node] += 1
    
    # Find universal gates (nodes in 100% of paths)
    universal_gates = []
    high_frequency_gates = []
    
    for node, count in node_traversal_count.items():
        traversal_percentage = (count / total_paths) * 100
        if traversal_percentage >= 99.5:  # Essentially universal (allowing for sampling variance)
            universal_gates.append((node, traversal_percentage))
        elif traversal_percentage >= 80:  # High frequency gates
            high_frequency_gates.append((node, traversal_percentage))
    
    # Sort by position in typical path
    universal_gates.sort(key=lambda x: get_typical_position_in_path(completion_paths, x[0]))
    high_frequency_gates.sort(key=lambda x: get_typical_position_in_path(completion_paths, x[0]))
    
    print(f"\\n🎯 UNIVERSAL GATES FOUND: {len(universal_gates)}")
    for i, (node, pct) in enumerate(universal_gates[:10]):
        position = get_typical_position_in_path(completion_paths, node)
        node_type = graph.nodes[node].get('type', 'unknown')
        print(f"   {i+1:2d}. {node} ({node_type}) - {pct:.1f}% of paths, ~position {position}")
    
    print(f"\\n📈 HIGH-FREQUENCY GATES: {len(high_frequency_gates)}")
    for i, (node, pct) in enumerate(high_frequency_gates[:10]):
        position = get_typical_position_in_path(completion_paths, node)
        node_type = graph.nodes[node].get('type', 'unknown')
        print(f"   {i+1:2d}. {node} ({node_type}) - {pct:.1f}% of paths, ~position {position}")
    
    # Step 2: Analyze Decision Points (where paths diverge)
    print("\\n🔀 STEP 2: DECISION POINT ANALYSIS...")
    
    decision_points = []
    for node in graph.nodes():
        out_degree = graph.out_degree(node)
        if out_degree > 1:  # Branching node
            successors = list(graph.successors(node))
            
            # Analyze path distribution after this decision point
            path_distributions = analyze_path_distribution_after_node(completion_paths, node, successors)
            
            decision_points.append({
                'node': node,
                'out_degree': out_degree,
                'successors': successors,
                'path_distributions': path_distributions,
                'traversal_pct': node_traversal_count.get(node, 0) / total_paths * 100,
                'position': get_typical_position_in_path(completion_paths, node)
            })
    
    # Sort decision points by importance (traversal % and position)
    decision_points.sort(key=lambda x: (-x['traversal_pct'], x['position']))
    
    print(f"   📊 Found {len(decision_points)} decision points")
    print(f"\\n🔀 TOP DECISION POINTS:")
    for i, dp in enumerate(decision_points[:8]):
        print(f"   {i+1}. {dp['node']} (pos ~{dp['position']}) - {dp['traversal_pct']:.1f}% traversal")
        print(f"      Branches to: {dp['successors']}")
        for successor, dist in dp['path_distributions'].items():
            print(f"         → {successor}: {dist:.1f}% of paths")
        print()
    
    # Step 3: Test Coverage Strategy
    print("🧪 STEP 3: OPTIMAL TEST COVERAGE STRATEGY...")
    
    # Find minimum test cases for 100% edge coverage
    print("   Computing minimum test cases for 100% edge coverage...")
    
    all_edges = set()
    edge_to_paths = defaultdict(set)
    
    # Map edges to paths that traverse them
    for path_idx, path in enumerate(completion_paths[:100]):  # Sample for performance
        path_edges = []
        for i in range(len(path) - 1):
            if graph.has_edge(path[i], path[i + 1]):
                edge = (path[i], path[i + 1])
                path_edges.append(edge)
                all_edges.add(edge)
                edge_to_paths[edge].add(path_idx)
    
    print(f"   Total edges to cover: {len(all_edges)}")
    
    # Greedy set cover algorithm for minimum test paths
    min_test_cases = greedy_set_cover(edge_to_paths, completion_paths[:100])
    
    print(f"\\n🎯 MINIMUM TEST CASES FOR 100% EDGE COVERAGE:")
    print(f"   Required test paths: {len(min_test_cases)}")
    print(f"   Coverage efficiency: {len(all_edges)/len(min_test_cases):.1f} edges per test case")
    
    # Show test case details
    for i, path_idx in enumerate(min_test_cases[:5]):
        path = completion_paths[path_idx]
        print(f"   Test Case {i+1}: {len(path)} nodes")
        print(f"      {path[0]} → ... → {path[-1]}")
    
    # Step 4: Coverage Strategy Recommendations
    print("\\n📋 STEP 4: COVERAGE STRATEGY RECOMMENDATIONS...")
    
    if universal_gates:
        last_universal = universal_gates[-1][0]
        last_universal_pos = get_typical_position_in_path(completion_paths, last_universal)
        
        print(f"✅ UNIVERSAL GATE STRATEGY:")
        print(f"   • Last universal gate: {last_universal} (~position {last_universal_pos})")
        print(f"   • Test thoroughly up to {last_universal}")
        print(f"   • After {last_universal}, paths diverge - use decision point strategy")
    
    print(f"\\n🔀 DECISION POINT STRATEGY:")
    critical_decisions = [dp for dp in decision_points[:5] if dp['traversal_pct'] > 50]
    print(f"   • Focus on {len(critical_decisions)} critical decision points")
    for dp in critical_decisions:
        print(f"   • Test all branches from {dp['node']} ({len(dp['successors'])} branches)")
    
    print(f"\\n🧪 MINIMUM TEST SUITE:")
    print(f"   • {len(min_test_cases)} test cases achieve 100% edge coverage")
    print(f"   • Average test case length: {np.mean([len(completion_paths[i]) for i in min_test_cases]):.1f} nodes")
    print(f"   • This is {(len(min_test_cases)/len(completion_paths))*100:.3f}% of all possible paths")
    
    return {
        'universal_gates': universal_gates,
        'decision_points': decision_points[:10],
        'min_test_cases': min_test_cases,
        'coverage_metrics': {
            'total_paths': len(completion_paths),
            'total_edges': len(all_edges),
            'min_test_cases': len(min_test_cases),
            'efficiency': len(all_edges)/len(min_test_cases) if min_test_cases else 0
        }
    }

def get_typical_position_in_path(paths, node):
    """Get typical position of node in paths (for ordering)."""
    positions = []
    for path in paths[:100]:  # Sample for performance
        if node in path:
            positions.append(path.index(node))
    return np.median(positions) if positions else 999

def analyze_path_distribution_after_node(paths, decision_node, successors):
    """Analyze how paths distribute after a decision node."""
    successor_counts = defaultdict(int)
    total_paths_through_node = 0
    
    for path in paths:
        if decision_node in path:
            total_paths_through_node += 1
            node_idx = path.index(decision_node)
            if node_idx + 1 < len(path):
                next_node = path[node_idx + 1]
                if next_node in successors:
                    successor_counts[next_node] += 1
    
    # Convert to percentages
    distributions = {}
    for successor in successors:
        if total_paths_through_node > 0:
            distributions[successor] = (successor_counts[successor] / total_paths_through_node) * 100
        else:
            distributions[successor] = 0.0
    
    return distributions

def greedy_set_cover(edge_to_paths, paths):
    """Greedy algorithm to find minimum set of paths covering all edges."""
    uncovered_edges = set(edge_to_paths.keys())
    selected_paths = []
    
    while uncovered_edges:
        # Find path that covers the most uncovered edges
        best_path = None
        best_coverage = 0
        
        for path_idx in range(len(paths)):
            if path_idx in selected_paths:
                continue
            
            # Count how many uncovered edges this path covers
            path_edges = get_path_edges(paths[path_idx])
            coverage = len(set(path_edges) & uncovered_edges)
            
            if coverage > best_coverage:
                best_coverage = coverage
                best_path = path_idx
        
        if best_path is not None:
            selected_paths.append(best_path)
            # Remove covered edges
            path_edges = get_path_edges(paths[best_path])
            uncovered_edges -= set(path_edges)
        else:
            break  # No more coverage possible
    
    return selected_paths

def get_path_edges(path):
    """Get edges in a path."""
    edges = []
    for i in range(len(path) - 1):
        edges.append((path[i], path[i + 1]))
    return edges

if __name__ == "__main__":
    results = analyze_universal_gates_and_coverage()
