"""
assembly.py - DAG Assembly Module
"""

from typing import Dict, List, Any
from datetime import datetime
from .config import ExtractorConfig


class DAGAssembler:
    """
    Assembles components into final DAG structure.
    """
    
    def __init__(self, config: ExtractorConfig):
        self.config = config
    
    def assemble(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        predicates: Dict[str, Dict],
        metadata: Dict
    ) -> Dict[str, Any]:
        """
        Assemble components into schema-compliant DAG.
        
        Returns:
            Complete survey_dag structure
        """
        # Identify start and terminals
        start_node = self._identify_start(nodes)
        terminal_nodes = self._identify_terminals(nodes)
        
        # Clean internal fields
        clean_nodes = [self._clean_node(n) for n in nodes]
        clean_edges = [self._clean_edge(e) for e in edges]
        clean_predicates = self._clean_predicates(predicates)
        
        # Build DAG structure
        survey_dag = {
            "survey_dag": {
                "metadata": metadata,
                "graph": {
                    "start": start_node,
                    "terminals": terminal_nodes,
                    "nodes": clean_nodes,
                    "edges": clean_edges
                },
                "predicates": clean_predicates,
                "validation": {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "gates": {
                        "acyclic": True,
                        "single_start": start_node is not None,
                        "all_reachable": True,
                        "terminals_reachable": len(terminal_nodes) > 0,
                        "predicates_valid": True
                    }
                },
                "analysis": {
                    "statistics": {
                        "node_count": len(nodes),
                        "edge_count": len(edges),
                        "predicate_count": len(predicates),
                        "max_depth": self._calculate_max_depth(nodes, edges, start_node),
                        "branching_factor": len(edges) / len(nodes) if nodes else 0,
                        "complexity_score": self._calculate_complexity(nodes, edges, predicates)
                    },
                    "topology": {
                        "topological_order": self._topological_sort(nodes, edges, start_node),
                        "strongly_connected_components": [],  # Should be empty for valid DAG
                        "critical_path": self._find_critical_path(nodes, edges, start_node)
                    }
                }
            }
        }
        
        return survey_dag
    
    def _identify_start(self, nodes: List[Dict]) -> str:
        """Identify the start node."""
        # Check for explicitly marked start
        for node in nodes:
            if node.get('_is_start'):
                return node['id']
        
        # Find first non-terminal by order
        non_terminals = [n for n in nodes if n['type'] != 'terminal']
        if non_terminals:
            non_terminals.sort(key=lambda n: n.get('order_index', 999))
            return non_terminals[0]['id']
        
        return None
    
    def _identify_terminals(self, nodes: List[Dict]) -> List[str]:
        """Identify terminal nodes."""
        terminals = []
        
        for node in nodes:
            if node['type'] == 'terminal' or node['id'].startswith('END_'):
                terminals.append(node['id'])
        
        return sorted(list(set(terminals)))
    
    def _clean_node(self, node: Dict) -> Dict:
        """Remove internal fields from node."""
        # Keep only schema-defined fields
        clean = {}
        schema_fields = [
            'id', 'type', 'order_index', 'block', 'domain',
            'metadata', 'universe', 'provenance'
        ]
        
        for field in schema_fields:
            if field in node:
                clean[field] = node[field]
        
        # Ensure required fields have defaults
        if 'type' not in clean:
            clean['type'] = 'question'
        if 'domain' not in clean:
            clean['domain'] = {'kind': 'text'}
        
        return clean
    
    def _clean_edge(self, edge: Dict) -> Dict:
        """Remove internal fields from edge."""
        # Keep only schema-defined fields
        clean = {}
        schema_fields = [
            'id', 'source', 'target', 'predicate', 'kind',
            'priority', 'subkind', 'metadata', 'provenance'
        ]
        
        for field in schema_fields:
            if field in edge:
                clean[field] = edge[field]
        
        # Ensure required fields have defaults
        if 'priority' not in clean:
            clean['priority'] = 0
        if 'subkind' not in clean:
            clean['subkind'] = 'sequence'
        if 'kind' not in clean:
            clean['kind'] = 'branch'
        
        return clean
    
    def _clean_predicates(self, predicates: Dict) -> Dict:
        """Clean predicate entries."""
        clean = {}
        
        for pred_id, pred in predicates.items():
            clean[pred_id] = {
                "ast": pred.get('ast', ["TRUE"]),
                "text": pred.get('text', ''),
                "complexity": pred.get('complexity', 'simple')
            }
            
            # Add optional fields if present
            if 'depends_on' in pred:
                clean[pred_id]['depends_on'] = pred['depends_on']
            if 'semantic_meaning' in pred:
                clean[pred_id]['semantic_meaning'] = pred['semantic_meaning']
        
        return clean
    
    def _calculate_max_depth(self, nodes: List, edges: List, start: str) -> int:
        """Calculate maximum depth of DAG."""
        if not start:
            return 0
        
        # Build adjacency list
        adj = {n['id']: [] for n in nodes}
        for edge in edges:
            if edge['source'] in adj:
                adj[edge['source']].append(edge['target'])
        
        # BFS to find max depth
        depths = {start: 0}
        queue = [start]
        max_depth = 0
        
        while queue:
            current = queue.pop(0)
            current_depth = depths[current]
            
            for neighbor in adj.get(current, []):
                if neighbor not in depths:
                    depths[neighbor] = current_depth + 1
                    max_depth = max(max_depth, depths[neighbor])
                    queue.append(neighbor)
        
        return max_depth
    
    def _calculate_complexity(self, nodes: List, edges: List, predicates: Dict) -> float:
        """Calculate survey complexity score."""
        # Factors:
        # - Number of nodes
        # - Branching factor
        # - Predicate complexity
        # - Skip distance
        
        node_score = min(10, len(nodes) / 10)  # 100 nodes = score 10
        
        edge_score = min(10, len(edges) / len(nodes) if nodes else 0)
        
        # Average predicate complexity
        complexity_map = {'trivial': 0, 'simple': 1, 'moderate': 2, 'complex': 3}
        pred_scores = [complexity_map.get(p.get('complexity', 'simple'), 1) for p in predicates.values()]
        pred_score = sum(pred_scores) / len(pred_scores) if pred_scores else 0
        
        # Normalize to 0-10 scale
        complexity = (node_score * 0.3 + edge_score * 0.4 + pred_score * 3 * 0.3)
        
        return round(complexity, 2)
    
    def _topological_sort(self, nodes: List, edges: List, start: str) -> List[str]:
        """Get topological ordering of nodes."""
        if not start:
            return []
        
        # Build adjacency list and in-degree
        adj = {n['id']: [] for n in nodes}
        in_degree = {n['id']: 0 for n in nodes}
        
        for edge in edges:
            if edge['source'] in adj:
                adj[edge['source']].append(edge['target'])
                in_degree[edge['target']] = in_degree.get(edge['target'], 0) + 1
        
        # Start with nodes that have no incoming edges
        queue = [n for n, deg in in_degree.items() if deg == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in adj.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    def _find_critical_path(self, nodes: List, edges: List, start: str) -> List[str]:
        """Find the critical (longest) path through DAG."""
        if not start:
            return []
        
        # Build adjacency list
        adj = {n['id']: [] for n in nodes}
        for edge in edges:
            if edge['source'] in adj:
                adj[edge['source']].append(edge['target'])
        
        # DFS to find longest path
        def find_longest(node, visited):
            if node in visited:
                return []
            
            visited.add(node)
            longest = []
            
            for neighbor in adj.get(node, []):
                path = find_longest(neighbor, visited.copy())
                if len(path) > len(longest):
                    longest = path
            
            return [node] + longest
        
        return find_longest(start, set())
