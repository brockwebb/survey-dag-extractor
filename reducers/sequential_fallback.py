# reducers/sequential_fallback.py
from __future__ import annotations
from typing import List, Dict, Optional

def make_sequential_edges(node_ids: List[str],
                          terminal_id: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Build a simple, forward-only path: Q[i] -> Q[i+1] with predicate P_TRUE.
    Optionally wire last node to a terminal.
    """
    edges: List[Dict[str, str]] = []
    for a, b in zip(node_ids, node_ids[1:]):
        edges.append({"source": a, "target": b, "predicate": "P_TRUE"})
    if terminal_id and node_ids:
        edges.append({"source": node_ids[-1], "target": terminal_id, "predicate": "P_TRUE"})
    return edges

def needs_sequential_fallback(edges: List[Dict], node_count: int, min_ratio: float = 0.05) -> bool:
    """
    Trigger fallback if we discovered too few edges.
    Default: fall back when #edges < 5% of #nodes (rounded up).
    """
    try:
        n_edges = len(edges or [])
    except Exception:
        n_edges = 0
    threshold = max(1, int(min_ratio * max(1, node_count)))
    return n_edges < threshold

