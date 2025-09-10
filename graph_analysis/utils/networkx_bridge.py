"""
NetworkX Bridge Utilities

Handles conversion between schema-compliant JSON format 
and NetworkX graph objects.
"""

import networkx as nx
from typing import Dict, List, Any, Tuple


def nodes_to_networkx(nodes: List[Dict[str, Any]]) -> nx.DiGraph:
    """Convert schema-compliant nodes to NetworkX graph."""
    G = nx.DiGraph()
    
    for node in nodes:
        G.add_node(
            node['id'],
            **{k: v for k, v in node.items() if k != 'id'}
        )
    
    return G


def networkx_to_nodes(G: nx.DiGraph) -> List[Dict[str, Any]]:
    """Convert NetworkX graph nodes back to schema-compliant format."""
    nodes = []
    
    for node_id, data in G.nodes(data=True):
        node = {'id': node_id}
        node.update(data)
        nodes.append(node)
    
    return nodes


def add_edges_to_networkx(G: nx.DiGraph, edges: List[Dict[str, Any]]) -> nx.DiGraph:
    """Add schema-compliant edges to NetworkX graph."""
    for edge in edges:
        G.add_edge(
            edge['source'],
            edge['target'],
            **{k: v for k, v in edge.items() if k not in ['source', 'target']}
        )
    
    return G


def networkx_to_edges(G: nx.DiGraph) -> List[Dict[str, Any]]:
    """Convert NetworkX graph edges back to schema-compliant format."""
    edges = []
    
    for source, target, data in G.edges(data=True):
        edge = {
            'source': source,
            'target': target
        }
        edge.update(data)
        edges.append(edge)
    
    return edges


def validate_graph_properties(G: nx.DiGraph) -> Dict[str, Any]:
    """Validate mathematical properties of the graph."""
    return {
        'is_dag': nx.is_directed_acyclic_graph(G),
        'is_connected': nx.is_weakly_connected(G),
        'node_count': G.number_of_nodes(),
        'edge_count': G.number_of_edges(),
        'isolated_nodes': list(nx.isolates(G)),
        'cycles': list(nx.simple_cycles(G)) if not nx.is_directed_acyclic_graph(G) else [],
        'has_self_loops': len(list(nx.nodes_with_selfloops(G))) > 0
    }
