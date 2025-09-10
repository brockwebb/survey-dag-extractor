"""
Graph Operations Utilities

Common graph algorithms and operations for survey DAG analysis.
"""

import networkx as nx
from typing import List, Dict, Any, Set, Optional


def find_survey_paths(G: nx.DiGraph, start_node: str, terminal_nodes: List[str]) -> List[List[str]]:
    """Find all possible survey completion paths."""
    all_paths = []
    
    for terminal in terminal_nodes:
        if terminal in G:
            try:
                paths = list(nx.all_simple_paths(G, start_node, terminal))
                all_paths.extend(paths)
            except nx.NetworkXNoPath:
                continue
    
    return all_paths


def identify_unreachable_nodes(G: nx.DiGraph, start_node: str) -> Set[str]:
    """Identify nodes that cannot be reached from the start node."""
    if start_node not in G:
        return set(G.nodes())
    
    reachable = set(nx.descendants(G, start_node))
    reachable.add(start_node)
    
    return set(G.nodes()) - reachable


def find_critical_path(G: nx.DiGraph, start_node: str, terminal_nodes: List[str]) -> Optional[List[str]]:
    """Find the longest path through the survey (critical path)."""
    longest_path = []
    
    for terminal in terminal_nodes:
        if terminal in G:
            try:
                paths = list(nx.all_simple_paths(G, start_node, terminal))
                for path in paths:
                    if len(path) > len(longest_path):
                        longest_path = path
            except nx.NetworkXNoPath:
                continue
    
    return longest_path if longest_path else None


def calculate_branching_factor(G: nx.DiGraph) -> float:
    """Calculate average branching factor of the survey."""
    if G.number_of_nodes() == 0:
        return 0.0
    
    total_out_degree = sum(G.out_degree(node) for node in G.nodes())
    return total_out_degree / G.number_of_nodes()


def identify_decision_points(G: nx.DiGraph) -> List[Dict[str, Any]]:
    """Identify nodes with multiple outgoing edges (decision points)."""
    decision_points = []
    
    for node in G.nodes():
        out_degree = G.out_degree(node)
        if out_degree > 1:
            successors = list(G.successors(node))
            decision_points.append({
                'node': node,
                'out_degree': out_degree,
                'targets': successors
            })
    
    return decision_points


def validate_survey_flow(G: nx.DiGraph, start_node: str, terminal_nodes: List[str]) -> Dict[str, Any]:
    """Comprehensive survey flow validation."""
    validation_results = {
        'is_valid_dag': nx.is_directed_acyclic_graph(G),
        'is_connected': nx.is_weakly_connected(G),
        'start_node_exists': start_node in G,
        'all_terminals_exist': all(t in G for t in terminal_nodes),
        'unreachable_nodes': list(identify_unreachable_nodes(G, start_node)),
        'decision_points': identify_decision_points(G),
        'critical_path_length': len(find_critical_path(G, start_node, terminal_nodes) or []),
        'branching_factor': calculate_branching_factor(G)
    }
    
    # Overall validity
    validation_results['overall_valid'] = (
        validation_results['is_valid_dag'] and
        validation_results['start_node_exists'] and
        validation_results['all_terminals_exist'] and
        len(validation_results['unreachable_nodes']) == 0
    )
    
    return validation_results
