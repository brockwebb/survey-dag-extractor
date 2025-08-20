"""
validation.py - DAG Validation Module
"""

from typing import Dict, List, Any, Set
from .config import ExtractorConfig


class DAGValidator:
    """
    Validates DAG structure and consistency.
    """
    
    def __init__(self, config: ExtractorConfig):
        self.config = config
    
    def validate(self, dag: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate DAG against schema requirements.
        
        Returns:
            Validation result with issues and stats
        """
        issues = []
        warnings = []
        
        graph = dag['survey_dag']['graph']
        predicates = dag['survey_dag']['predicates']
        
        # Run validation checks
        issues.extend(self._validate_structure(graph))
        issues.extend(self._validate_nodes(graph))
        issues.extend(self._validate_edges(graph, predicates))
        issues.extend(self._validate_predicates(graph, predicates))
        warnings.extend(self._validate_flow(graph))
        
        # Calculate statistics
        stats = self._calculate_stats(graph, predicates)
        
        # Determine overall validity
        is_valid = len(issues) == 0
        
        return {
            "is_valid": is_valid,
            "issues": issues,
            "warnings": warnings,
            "statistics": stats,
            "gates": {
                "acyclic": self._check_acyclic(graph),
                "single_start": graph.get('start') is not None,
                "all_reachable": self._check_reachability(graph),
                "terminals_reachable": len(graph.get('terminals', [])) > 0,
                "predicates_valid": len([i for i in issues if 'predicate' in i.lower()]) == 0
            }
        }
    
    def _validate_structure(self, graph: Dict) -> List[str]:
        """Validate basic structure."""
        issues = []
        
        # Required fields
        if not graph.get('start'):
            issues.append("No start node identified")
        
        if not graph.get('terminals'):
            issues.append("No terminal nodes identified")
        
        if not graph.get('nodes'):
            issues.append("No nodes in graph")
        
        if not graph.get('edges'):
            issues.append("No edges in graph")
        
        return issues
    
    def _validate_nodes(self, graph: Dict) -> List[str]:
        """Validate node structure and IDs."""
        issues = []
        node_ids = set()
        
        for node in graph.get('nodes', []):
            # Check required fields
            if 'id' not in node:
                issues.append("Node missing ID")
                continue
            
            node_id = node['id']
            
            # Check for duplicates
            if node_id in node_ids:
                issues.append(f"Duplicate node ID: {node_id}")
            node_ids.add(node_id)
            
            # Validate ID format
            if node['type'] == 'terminal':
                if not node_id.startswith('END_'):
                    issues.append(f"Terminal node '{node_id}' should start with END_")
            
            # Check required fields
            for field in ['type', 'domain', 'metadata', 'universe']:
                if field not in node:
                    issues.append(f"Node '{node_id}' missing required field: {field}")
        
        # Validate start node exists
        if graph.get('start') and graph['start'] not in node_ids:
            issues.append(f"Start node '{graph['start']}' not found in nodes")
        
        # Validate terminals exist
        for terminal in graph.get('terminals', []):
            if terminal not in node_ids:
                issues.append(f"Terminal '{terminal}' not found in nodes")
        
        return issues
    
    def _validate_edges(self, graph: Dict, predicates: Dict) -> List[str]:
        """Validate edge structure and references."""
        issues = []
        node_ids = {n['id'] for n in graph.get('nodes', [])}
        edge_ids = set()
        
        for edge in graph.get('edges', []):
            # Check required fields
            if 'id' not in edge:
                issues.append("Edge missing ID")
                continue
            
            edge_id = edge['id']
            
            # Check for duplicates
            if edge_id in edge_ids:
                issues.append(f"Duplicate edge ID: {edge_id}")
            edge_ids.add(edge_id)
            
            # Validate source/target
            if 'source' not in edge:
                issues.append(f"Edge '{edge_id}' missing source")
            elif edge['source'] not in node_ids:
                issues.append(f"Edge '{edge_id}' source '{edge['source']}' not found")
            
            if 'target' not in edge:
                issues.append(f"Edge '{edge_id}' missing target")
            elif edge['target'] not in node_ids:
                issues.append(f"Edge '{edge_id}' target '{edge['target']}' not found")
            
            # Validate predicate reference
            if 'predicate' not in edge:
                issues.append(f"Edge '{edge_id}' missing predicate")
            elif edge['predicate'] not in predicates:
                issues.append(f"Edge '{edge_id}' references undefined predicate '{edge['predicate']}'")
            
            # Check required fields
            for field in ['kind', 'subkind', 'priority']:
                if field not in edge:
                    issues.append(f"Edge '{edge_id}' missing required field: {field}")
        
        return issues
    
    def _validate_predicates(self, graph: Dict, predicates: Dict) -> List[str]:
        """Validate predicate structure."""
        issues = []
        
        # Check P_TRUE exists
        if 'P_TRUE' not in predicates:
            issues.append("Missing required P_TRUE predicate")
        
        for pred_id, pred in predicates.items():
            # Check required fields
            if 'ast' not in pred:
                issues.append(f"Predicate '{pred_id}' missing AST")
            
            # Validate AST structure
            ast = pred.get('ast')
            if not isinstance(ast, list):
                issues.append(f"Predicate '{pred_id}' AST must be a list")
        
        return issues
    
    def _validate_flow(self, graph: Dict) -> List[str]:
        """Validate survey flow logic."""
        warnings = []
        
        nodes = {n['id']: n for n in graph.get('nodes', [])}
        edges = graph.get('edges', [])
        terminals = set(graph.get('terminals', []))
        
        # Check all non-terminals have outgoing edges
        nodes_with_outgoing = {e['source'] for e in edges}
        for node_id, node in nodes.items():
            if node_id not in terminals and node_id not in nodes_with_outgoing:
                warnings.append(f"Non-terminal node '{node_id}' has no outgoing edges")
        
        # Check terminals have no outgoing edges
        for edge in edges:
            if edge['source'] in terminals:
                warnings.append(f"Terminal '{edge['source']}' has outgoing edge")
        
        # Check for very long skips
        for edge in edges:
            if edge.get('subkind') == 'skip':
                source = nodes.get(edge['source'], {})
                target = nodes.get(edge['target'], {})
                
                source_order = source.get('order_index', 0)
                target_order = target.get('order_index', 0)
                
                if abs(target_order - source_order) > 20:
                    warnings.append(
                        f"Long skip detected: {edge['source']} → {edge['target']} "
                        f"(spans {abs(target_order - source_order)} questions)"
                    )
        
        return warnings
    
    def _check_acyclic(self, graph: Dict) -> bool:
        """Check if DAG is acyclic."""
        # Build adjacency list
        adj = {}
        for node in graph.get('nodes', []):
            adj[node['id']] = []
        
        for edge in graph.get('edges', []):
            if edge['source'] in adj:
                adj[edge['source']].append(edge['target'])
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node_id in adj:
            if node_id not in visited:
                if has_cycle(node_id):
                    return False
        
        return True
    
    def _check_reachability(self, graph: Dict) -> bool:
        """Check if all nodes are reachable from start."""
        start = graph.get('start')
        if not start:
            return False
        
        # BFS from start
        visited = set()
        queue = [start]
        
        # Build adjacency list
        adj = {}
        for node in graph.get('nodes', []):
            adj[node['id']] = []
        
        for edge in graph.get('edges', []):
            if edge['source'] in adj:
                adj[edge['source']].append(edge['target'])
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)
        
        # Check if all nodes were visited
        all_nodes = {n['id'] for n in graph.get('nodes', [])}
        return visited == all_nodes
    
    def _calculate_stats(self, graph: Dict, predicates: Dict) -> Dict:
        """Calculate DAG statistics."""
        nodes = graph.get('nodes', [])
        edges = graph.get('edges', [])
        
        # Count node types
        node_types = {}
        for node in nodes:
            t = node.get('type', 'unknown')
            node_types[t] = node_types.get(t, 0) + 1
        
        # Count edge types
        edge_types = {}
        for edge in edges:
            t = edge.get('subkind', 'unknown')
            edge_types[t] = edge_types.get(t, 0) + 1
        
        # Calculate branching factor
        outgoing_counts = {}
        for edge in edges:
            source = edge['source']
            outgoing_counts[source] = outgoing_counts.get(source, 0) + 1
        
        avg_branching = sum(outgoing_counts.values()) / len(outgoing_counts) if outgoing_counts else 0
        max_branching = max(outgoing_counts.values()) if outgoing_counts else 0
        
        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "predicate_count": len(predicates),
            "terminal_count": len(graph.get('terminals', [])),
            "node_types": node_types,
            "edge_types": edge_types,
            "avg_branching_factor": round(avg_branching, 2),
            "max_branching_factor": max_branching
        }
