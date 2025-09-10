"""
DAG Validator

Mathematical validation of survey DAG properties using NetworkX.
Ensures graph theoretic correctness and survey logic validity.
"""

import networkx as nx
from typing import Dict, List, Any, Tuple, Optional

from .utils.graph_operations import validate_survey_flow


class DAGValidator:
    """Mathematical validator for survey DAGs."""
    
    def __init__(self):
        self.validation_rules = [
            self._validate_dag_property,
            self._validate_connectivity, 
            self._validate_reachability,
            self._validate_terminal_accessibility,
            self._validate_no_orphan_nodes,
            self._validate_proper_start_node
        ]
    
    def validate_complete_dag(self, graph: nx.DiGraph, start_node: str, 
                            terminal_nodes: List[str]) -> Tuple[bool, List[str]]:
        """Run complete mathematical validation of the survey DAG."""
        
        errors = []
        
        # Run all validation rules
        for rule in self.validation_rules:
            try:
                is_valid, rule_errors = rule(graph, start_node, terminal_nodes)
                if not is_valid:
                    errors.extend(rule_errors)
            except Exception as e:
                errors.append(f"Validation rule failed: {str(e)}")
        
        return len(errors) == 0, errors
    
    def _validate_dag_property(self, graph: nx.DiGraph, start_node: str, 
                              terminal_nodes: List[str]) -> Tuple[bool, List[str]]:
        """Validate that the graph is a proper DAG (no cycles)."""
        errors = []
        
        if not nx.is_directed_acyclic_graph(graph):
            cycles = list(nx.simple_cycles(graph))
            errors.append(f"Graph contains {len(cycles)} cycles")
            for i, cycle in enumerate(cycles[:5]):  # Show first 5 cycles
                errors.append(f"  Cycle {i+1}: {' -> '.join(cycle + [cycle[0]])}")
        
        return len(errors) == 0, errors
    
    def _validate_connectivity(self, graph: nx.DiGraph, start_node: str,
                              terminal_nodes: List[str]) -> Tuple[bool, List[str]]:
        """Validate graph connectivity properties."""
        errors = []
        
        if not nx.is_weakly_connected(graph):
            components = list(nx.weakly_connected_components(graph))
            errors.append(f"Graph has {len(components)} disconnected components")
            
            # Identify which nodes are isolated
            main_component = max(components, key=len)
            isolated_components = [c for c in components if c != main_component]
            
            for i, component in enumerate(isolated_components):
                errors.append(f"  Isolated component {i+1}: {list(component)}")
        
        return len(errors) == 0, errors
    
    def _validate_reachability(self, graph: nx.DiGraph, start_node: str,
                              terminal_nodes: List[str]) -> Tuple[bool, List[str]]:
        """Validate that all nodes are reachable from start node."""
        errors = []
        
        if start_node not in graph:
            errors.append(f"Start node '{start_node}' not found in graph")
            return False, errors
        
        # Find all reachable nodes
        reachable = set(nx.descendants(graph, start_node))
        reachable.add(start_node)
        
        # Find unreachable nodes
        unreachable = set(graph.nodes()) - reachable
        
        if unreachable:
            errors.append(f"{len(unreachable)} nodes unreachable from start node")
            errors.append(f"  Unreachable nodes: {list(unreachable)}")
        
        return len(errors) == 0, errors
    
    def _validate_terminal_accessibility(self, graph: nx.DiGraph, start_node: str,
                                        terminal_nodes: List[str]) -> Tuple[bool, List[str]]:
        """Validate that all terminal nodes are accessible."""
        errors = []
        
        if start_node not in graph:
            return False, ["Start node not found"]
        
        reachable_terminals = []
        unreachable_terminals = []
        
        for terminal in terminal_nodes:
            if terminal not in graph:
                errors.append(f"Terminal node '{terminal}' not found in graph")
                continue
                
            try:
                if nx.has_path(graph, start_node, terminal):
                    reachable_terminals.append(terminal)
                else:
                    unreachable_terminals.append(terminal)
            except nx.NetworkXNoPath:
                unreachable_terminals.append(terminal)
        
        if unreachable_terminals:
            errors.append(f"{len(unreachable_terminals)} terminal nodes unreachable")
            errors.append(f"  Unreachable terminals: {unreachable_terminals}")
        
        if not reachable_terminals:
            errors.append("No terminal nodes are reachable - survey cannot complete")
        
        return len(errors) == 0, errors
    
    def _validate_no_orphan_nodes(self, graph: nx.DiGraph, start_node: str,
                                 terminal_nodes: List[str]) -> Tuple[bool, List[str]]:
        """Validate that there are no orphaned nodes (no incoming or outgoing edges)."""
        errors = []
        
        isolated_nodes = list(nx.isolates(graph))
        
        if isolated_nodes:
            errors.append(f"{len(isolated_nodes)} isolated nodes found")
            errors.append(f"  Isolated nodes: {isolated_nodes}")
        
        return len(errors) == 0, errors
    
    def _validate_proper_start_node(self, graph: nx.DiGraph, start_node: str,
                                   terminal_nodes: List[str]) -> Tuple[bool, List[str]]:
        """Validate start node properties."""
        errors = []
        
        if start_node not in graph:
            errors.append(f"Start node '{start_node}' not found in graph")
            return False, errors
        
        # Start node should have no incoming edges (except possibly from itself)
        incoming = list(graph.predecessors(start_node))
        non_self_incoming = [n for n in incoming if n != start_node]
        
        if non_self_incoming:
            errors.append(f"Start node has {len(non_self_incoming)} incoming edges")
            errors.append(f"  Incoming from: {non_self_incoming}")
        
        # Start node should have outgoing edges
        if graph.out_degree(start_node) == 0:
            errors.append("Start node has no outgoing edges - survey cannot progress")
        
        return len(errors) == 0, errors
    
    def generate_validation_report(self, graph: nx.DiGraph, start_node: str,
                                  terminal_nodes: List[str]) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        
        is_valid, errors = self.validate_complete_dag(graph, start_node, terminal_nodes)
        
        # Basic graph metrics
        basic_metrics = {
            'node_count': graph.number_of_nodes(),
            'edge_count': graph.number_of_edges(),
            'is_dag': nx.is_directed_acyclic_graph(graph),
            'is_connected': nx.is_weakly_connected(graph),
            'density': nx.density(graph),
            'average_degree': sum(dict(graph.degree()).values()) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0
        }
        
        # Survey-specific validation
        survey_validation = validate_survey_flow(graph, start_node, terminal_nodes)
        
        report = {
            'overall_valid': is_valid,
            'validation_errors': errors,
            'basic_metrics': basic_metrics,
            'survey_validation': survey_validation,
            'recommendations': self._generate_recommendations(errors, survey_validation)
        }
        
        return report
    
    def _generate_recommendations(self, errors: List[str], 
                                survey_validation: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        if not survey_validation.get('is_valid_dag', True):
            recommendations.append("Fix cycles in graph - survey logic should be acyclic")
        
        if not survey_validation.get('is_connected', True):
            recommendations.append("Connect isolated components to main survey flow")
        
        unreachable = survey_validation.get('unreachable_nodes', [])
        if unreachable:
            recommendations.append(f"Add routing to make {len(unreachable)} nodes reachable")
        
        decision_points = survey_validation.get('decision_points', [])
        if not decision_points:
            recommendations.append("Add conditional routing - survey appears too linear")
        
        critical_path_length = survey_validation.get('critical_path_length', 0)
        if critical_path_length == 0:
            recommendations.append("Ensure survey has valid completion paths")
        
        return recommendations
