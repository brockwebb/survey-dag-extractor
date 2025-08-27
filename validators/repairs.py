# validators/repairs.py
from __future__ import annotations
from typing import Dict, List, Set

CANON_TERMINAL = "END_COMPLETE"
TERMINAL_ALIASES = {"END", "SUBMIT", "FINISH", "END_SURVEY", "COMPLETE", "ENDCOMPLETE"}

def _idset(nodes: List[dict]) -> Set[str]:
    return {n.get("id") for n in nodes if n.get("id")}

def _content_idset(content: dict) -> Set[str]:
    try:
        return {n.get("id") for n in content.get("survey_content", {}).get("nodes", []) if n.get("id")}
    except Exception:
        return set()

def _make_stub_node(node_id: str) -> dict:
    # Lightweight placeholder; merge step will still enrich from content later.
    return {
        "id": node_id,
        "kind": "question",
        "block": None,
        "response_type": None,
        "universe": None,
        "universe_ast": None,
    }

def repair_structure_with_content(structure: dict, content: dict) -> tuple[dict, dict]:
    """
    Returns (fixed_structure, report)
    - Adds stub nodes for any edge endpoints missing in structure when content contains that id.
    - Drops edges whose endpoints are missing from both structure and content.
    - Ensures canonical terminal presence and rewires terminal aliases to END_COMPLETE.
    """
    s = structure.get("survey_dag_structure", {})
    nodes = list(s.get("nodes", []))
    edges = list(s.get("edges", []))
    preds = dict(s.get("predicates", {}))

    report = {
        "added_nodes_from_content": [],
        "dropped_edges_unknown_endpoints": [],
        "rewired_terminal_edges": 0,
        "ensured_terminal": False,
    }

    # Canonicalize terminals: ensure END_COMPLETE exists and rewire edges from aliases
    node_ids = _idset(nodes)
    has_canon = CANON_TERMINAL in node_ids
    alias_present = node_ids & TERMINAL_ALIASES
    if not has_canon and (alias_present or any(n.get("kind") == "terminal" for n in nodes)):
        nodes.append(_make_stub_node(CANON_TERMINAL))
        nodes[-1]["kind"] = "terminal"
        report["ensured_terminal"] = True
        node_ids.add(CANON_TERMINAL)

    if alias_present:
        for e in edges:
            if e.get("source") in alias_present:
                e["source"] = CANON_TERMINAL
                report["rewired_terminal_edges"] += 1
            if e.get("target") in alias_present:
                e["target"] = CANON_TERMINAL
                report["rewired_terminal_edges"] += 1
        # drop alias terminal nodes
        nodes = [n for n in nodes if n.get("id") not in alias_present]
        node_ids = _idset(nodes)

    # Add missing endpoints from content when possible
    c_ids = _content_idset(content)
    for e in list(edges):
        src, tgt = e.get("source"), e.get("target")
        need_src = src and src not in node_ids
        need_tgt = tgt and tgt not in node_ids
        added = False
        if need_src and src in c_ids:
            nodes.append(_make_stub_node(src))
            node_ids.add(src)
            report["added_nodes_from_content"].append(src)
            added = True
        if need_tgt and tgt in c_ids:
            nodes.append(_make_stub_node(tgt))
            node_ids.add(tgt)
            report["added_nodes_from_content"].append(tgt)
            added = True
        if (need_src or need_tgt) and not added:
            # Neither endpoint exists in structure nor content → drop the edge
            report["dropped_edges_unknown_endpoints"].append(e)
            edges.remove(e)

    fixed = {
        "survey_dag_structure": {
            "id": s.get("id"),
            "version": s.get("version"),
            "start": s.get("start") or (nodes[0]["id"] if nodes else "Q1"),
            "terminals": [CANON_TERMINAL],
            "nodes": nodes,
            "edges": edges,
            "predicates": preds
        }
    }
    return fixed, report

