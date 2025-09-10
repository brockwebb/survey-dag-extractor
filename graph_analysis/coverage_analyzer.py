"""
Coverage Analyzer

Generates optimal test paths for survey coverage analysis.
Calculates minimum sets of survey paths needed to test all routing logic.
"""

import networkx as nx
from typing import Dict, List, Any, Set, Tuple
from itertools import combinations

from .utils.graph_operations import find_survey_paths, identify_decision_points


class CoverageAnalyzer:
    """Analyzes survey DAG for optimal test coverage."""
    
    def __init__(self):
        self.coverage_objectives = ['node', 'edge', 'path', 'condition']
    
    def analyze_coverage_requirements(self, graph: nx.DiGraph, start_node: str,
                                    terminal_nodes: List[str], 
                                    objective: str = 'edge') -> Dict[str, Any]:
        """Analyze coverage requirements for the survey DAG."""
        
        if objective not in self.coverage_objectives:
            raise ValueError(f"Invalid objective. Must be one of: {self.coverage_objectives}")
        
        # Basic graph analysis
        all_paths = find_survey_paths(graph, start_node, terminal_nodes)
        decision_points = identify_decision_points(graph)
        
        # Coverage universe (what needs to be covered)
        coverage_universe = self._get_coverage_universe(graph, objective)
        
        # Calculate optimal paths
        optimal_paths = self._calculate_optimal_paths(
            graph, all_paths, coverage_universe, objective
        )
        
        # Coverage metrics
        metrics = self._calculate_coverage_metrics(
            optimal_paths, coverage_universe, all_paths
        )
        
        return {
            'objective': objective,
            'coverage_universe': coverage_universe,
            'total_paths': len(all_paths),
            'optimal_paths': optimal_paths,
            'decision_points': decision_points,
            'metrics': metrics,
            'recommendations': self._generate_coverage_recommendations(metrics, decision_points)
        }
    
    def _get_coverage_universe(self, graph: nx.DiGraph, objective: str) -> Dict[str, Set[str]]:
        """Get the universe of elements that need coverage."""
        
        universe = {
            'nodes': set(graph.nodes()),
            'edges': set(f"{s}->{t}" for s, t in graph.edges()),
            'conditions': set(),  # Would be populated from predicates
            'blocks': set()  # Would be populated from node metadata
        }
        
        # Add block information if available
        for node, data in graph.nodes(data=True):
            block = data.get('block')
            if block:
                universe['blocks'].add(block)
        
        # Add condition information if available
        for _, _, edge_data in graph.edges(data=True):
            condition = edge_data.get('condition')
            if condition and condition != 'always':
                universe['conditions'].add(condition)
        
        return universe
    
    def _calculate_optimal_paths(self, graph: nx.DiGraph, all_paths: List[List[str]], 
                               coverage_universe: Dict[str, Set[str]], 
                               objective: str) -> List[Dict[str, Any]]:
        """Calculate optimal paths for coverage objective."""
        
        if not all_paths:
            return []
        
        # Calculate coverage for each path
        path_coverage = []
        for i, path in enumerate(all_paths):
            coverage = self._calculate_path_coverage(graph, path, coverage_universe, objective)
            path_coverage.append({
                'id': f"path_{i:03d}",
                'nodes': path,
                'length': len(path),
                'coverage': coverage,
                'coverage_count': len(coverage[objective]) if objective in coverage else 0,
                'probability': 1.0 / len(all_paths),  # Assume uniform for now
                'explanation': f"Covers {len(coverage.get(objective, []))} {objective}s"
            })
        
        # Sort by coverage efficiency (coverage per path length)
        path_coverage.sort(
            key=lambda p: (p['coverage_count'] / p['length'] if p['length'] > 0 else 0, 
                          -p['length']), 
            reverse=True
        )
        
        # Select optimal set using greedy algorithm
        optimal_paths = self._select_optimal_path_set(
            path_coverage, coverage_universe[objective] if objective in coverage_universe else set()
        )
        
        return optimal_paths
    
    def _calculate_path_coverage(self, graph: nx.DiGraph, path: List[str], 
                               coverage_universe: Dict[str, Set[str]], 
                               objective: str) -> Dict[str, Set[str]]:
        """Calculate what a specific path covers."""
        
        coverage = {
            'nodes': set(path),
            'edges': set(),
            'conditions': set(),
            'blocks': set()
        }
        
        # Edge coverage
        for i in range(len(path) - 1):
            edge_id = f"{path[i]}->{path[i+1]}"
            coverage['edges'].add(edge_id)
        
        # Block coverage
        for node in path:
            if node in graph:
                block = graph.nodes[node].get('block')
                if block:
                    coverage['blocks'].add(block)
        
        # Condition coverage (would need predicate information)
        for i in range(len(path) - 1):
            if graph.has_edge(path[i], path[i+1]):
                condition = graph.edges[path[i], path[i+1]].get('condition')
                if condition and condition != 'always':
                    coverage['conditions'].add(condition)
        
        return coverage
    
    def _select_optimal_path_set(self, path_coverage: List[Dict[str, Any]], 
                                universe: Set[str]) -> List[Dict[str, Any]]:
        """Select minimum set of paths that covers the universe."""
        
        if not universe:
            return path_coverage[:1] if path_coverage else []
        
        selected_paths = []
        covered_elements = set()
        remaining_universe = universe.copy()
        
        # Greedy selection
        while remaining_universe and path_coverage:
            # Find path that covers most remaining elements
            best_path = None
            best_new_coverage = 0
            
            for path in path_coverage:
                path_elements = path['coverage'].get('edges', set())  # Default to edge coverage
                new_coverage = len(path_elements & remaining_universe)
                
                if new_coverage > best_new_coverage:
                    best_new_coverage = new_coverage
                    best_path = path
            
            if best_path and best_new_coverage > 0:
                selected_paths.append(best_path)
                path_elements = best_path['coverage'].get('edges', set())
                covered_elements.update(path_elements)
                remaining_universe -= path_elements
                path_coverage.remove(best_path)
            else:
                break  # No more useful paths
        
        return selected_paths
    
    def _calculate_coverage_metrics(self, optimal_paths: List[Dict[str, Any]], 
                                  coverage_universe: Dict[str, Set[str]], 
                                  all_paths: List[List[str]]) -> Dict[str, Any]:
        """Calculate coverage metrics."""
        
        total_universe_size = len(coverage_universe.get('edges', set()))
        
        if not optimal_paths:
            return {
                'coverage_percentage': 0.0,
                'path_count': 0,
                'efficiency': 0.0,
                'total_universe_size': total_universe_size
            }
        
        # Calculate total coverage
        total_covered = set()
        for path in optimal_paths:
            path_coverage = path['coverage'].get('edges', set())
            total_covered.update(path_coverage)
        
        coverage_percentage = (len(total_covered) / total_universe_size * 100) if total_universe_size > 0 else 0
        
        # Calculate efficiency (coverage per path)
        avg_coverage_per_path = len(total_covered) / len(optimal_paths) if optimal_paths else 0
        
        return {
            'coverage_percentage': coverage_percentage,
            'path_count': len(optimal_paths),
            'efficiency': avg_coverage_per_path,
            'total_universe_size': total_universe_size,
            'covered_elements': len(total_covered),
            'uncovered_elements': total_universe_size - len(total_covered),
            'path_reduction': len(all_paths) - len(optimal_paths)
        }
    
    def _generate_coverage_recommendations(self, metrics: Dict[str, Any], 
                                         decision_points: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations for improving coverage."""
        
        recommendations = []
        
        coverage_pct = metrics.get('coverage_percentage', 0)
        if coverage_pct < 80:
            recommendations.append(f"Coverage is only {coverage_pct:.1f}% - add more routing paths")
        
        if metrics.get('path_count', 0) == 1:
            recommendations.append("Only one test path needed - survey may be too linear")
        
        if not decision_points:
            recommendations.append("No decision points found - add conditional routing")
        elif len(decision_points) > 20:
            recommendations.append("Many decision points - consider simplifying survey logic")
        
        uncovered = metrics.get('uncovered_elements', 0)
        if uncovered > 0:
            recommendations.append(f"{uncovered} elements uncovered - review unreachable routing")
        
        efficiency = metrics.get('efficiency', 0)
        if efficiency < 5:
            recommendations.append("Low path efficiency - consider consolidating similar routes")
        
        return recommendations
    
    def generate_test_scenarios(self, graph: nx.DiGraph, start_node: str, 
                              terminal_nodes: List[str]) -> Dict[str, Any]:
        """Generate concrete test scenarios for survey testing."""
        
        coverage_analysis = self.analyze_coverage_requirements(
            graph, start_node, terminal_nodes, 'edge'
        )
        
        optimal_paths = coverage_analysis['optimal_paths']
        
        test_scenarios = []
        for i, path_info in enumerate(optimal_paths, 1):
            scenario = {
                'scenario_id': f"test_scenario_{i:02d}",
                'name': f"Coverage Path {i}",
                'description': path_info['explanation'],
                'survey_path': path_info['nodes'],
                'required_responses': self._generate_required_responses(graph, path_info['nodes']),
                'expected_coverage': list(path_info['coverage'].get('edges', set())),
                'estimated_duration': len(path_info['nodes']) * 30  # 30 seconds per question
            }
            test_scenarios.append(scenario)
        
        return {
            'total_scenarios': len(test_scenarios),
            'estimated_total_time': sum(s['estimated_duration'] for s in test_scenarios),
            'coverage_percentage': coverage_analysis['metrics']['coverage_percentage'],
            'test_scenarios': test_scenarios,
            'summary': {
                'objective': 'Achieve maximum edge coverage with minimum test paths',
                'method': 'Greedy path selection algorithm',
                'universe_size': coverage_analysis['metrics']['total_universe_size']
            }
        }
    
    def _generate_required_responses(self, graph: nx.DiGraph, path: List[str]) -> List[Dict[str, Any]]:
        """Generate required responses to follow a specific path."""
        
        required_responses = []
        
        for i, node in enumerate(path):
            if node in graph:
                node_data = graph.nodes[node]
                
                # Determine required response based on next node in path
                next_node = path[i + 1] if i + 1 < len(path) else None
                
                response_info = {
                    'question_id': node,
                    'question_type': node_data.get('type', 'question'),
                    'required_response': 'Any',  # Default
                    'next_question': next_node
                }
                
                # Try to determine specific response from edge data
                if next_node and graph.has_edge(node, next_node):
                    edge_data = graph.edges[node, next_node]
                    condition = edge_data.get('condition', 'always')
                    
                    if condition != 'always':
                        response_info['required_response'] = condition
                        response_info['routing_logic'] = f"If {condition}, go to {next_node}"
                
                required_responses.append(response_info)
        
        return required_responses
