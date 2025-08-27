# validators/qc_core.py
from __future__ import annotations
from typing import Dict, List, Set
from collections import defaultdict, Counter

CANON_TERMINAL = "END_COMPLETE"
TERMINAL_ALIASES = {"END", "SUBMIT", "FINISH", "END_SURVEY", "COMPLETE", "ENDCOMPLETE"}

def _nodes(dag: dict) -> List[dict]:
    return dag["survey_dag"]["graph"]["nodes"]

def _edges(dag: dict) -> List[dict]:
    return dag["survey_dag"]["graph"]["edges"]

def _preds(dag: dict) -> Dict[str, dict]:
    return dag["survey_dag"].get("predicates", {})

def _start(dag: dict) -> str:
    return dag["survey_dag"]["graph"]["start"]

def _idset(dag: dict) -> Set[str]:
    return {n["id"] for n in _nodes(dag)}

def _adj(dag: dict):
    adj = defaultdict(list)
    for e in _edges(dag):
        adj[e["source"]].append(e["target"])
    return adj

def _reachable(dag: dict) -> Set[str]:
    start = _start(dag)
    adj = _adj(dag)
    seen = set()
    stack = [start]
    while stack:
        u = stack.pop()
        if u in seen: continue
        seen.add(u)
        stack.extend(adj.get(u, []))
    return seen

def qc_core_report(dag: dict) -> dict:
    nodes = _nodes(dag); edges = _edges(dag); preds = _preds(dag)
    node_ids = [n["id"] for n in nodes]
    freq = Counter(node_ids)
    duplicates = [nid for nid, c in freq.items() if c > 1]

    # Node text & domain checks
    empty_text = [n["id"] for n in nodes if n.get("type") == "question" and not (n.get("metadata") or {}).get("text")]
    enum_set_without_values = [n["id"] for n in nodes
                               if n.get("type") == "question"
                               and (n.get("domain") or {}).get("kind") in ("enum","set")
                               and not (n.get("domain") or {}).get("values")]

    # Edge endpoint checks
    idset = set(node_ids)
    bad_edges = [e for e in edges if e.get("source") not in idset or e.get("target") not in idset]

    # Reachability / dead-ends
    reach = _reachable(dag)
    unreachable = sorted(list(idset - reach))
    nonterm_deadends = []
    outdeg = defaultdict(int)
    for e in edges:
        outdeg[e["source"]] += 1
    for n in nodes:
        if n["id"] not in reach: continue
        if n["type"] != "terminal" and outdeg[n["id"]] == 0:
            nonterm_deadends.append(n["id"])

    # Predicate checks
    pred_ids = set(preds.keys())
    used_preds = set(e.get("predicate") for e in edges if e.get("predicate"))
    missing_preds = sorted(list(used_preds - pred_ids))
    unused_preds = sorted(list(pred_ids - used_preds))

    # Terminal consistency
    terminal_nodes = [n["id"] for n in nodes if n.get("type") == "terminal"]
    alias_terminals_present = sorted(list(set(terminal_nodes) & TERMINAL_ALIASES))
    canonical_terminal_present = CANON_TERMINAL in terminal_nodes

    return {
        "summary": {
            "nodes": len(nodes),
            "edges": len(edges),
            "predicates": len(preds),
            "start": _start(dag),
        },
        "issues": {
            "duplicate_node_ids": duplicates,
            "empty_question_text": empty_text,
            "enum_or_set_without_values": enum_set_without_values,
            "edges_with_unknown_endpoints": bad_edges,
            "unreachable_nodes_from_start": unreachable,
            "dead_ends_nonterminal": nonterm_deadends,
            "missing_predicates": missing_preds,
            "unused_predicates": unused_preds,
            "terminal_alias_nodes_present": alias_terminals_present,
            "canonical_terminal_present": canonical_terminal_present
        }
    }

def qc_core_markdown(rep: dict) -> str:
    s = rep.get("summary", {})
    i = rep.get("issues", {})
    lines = []
    lines.append("# DAG Quality Check Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- nodes: {s.get('nodes')}")
    lines.append(f"- edges: {s.get('edges')}")
    lines.append(f"- predicates: {s.get('predicates')}")
    lines.append(f"- start: `{s.get('start')}`")
    lines.append("")
    lines.append("## Issues")
    def _blk(title, val):
        lines.append(f"### {title}")
        if not val:
            lines.append("- none")
        elif isinstance(val, list):
            for v in val[:200]:
                lines.append(f"- {v}")
            if len(val) > 200:
                lines.append(f"- … ({len(val)-200} more)")
        else:
            lines.append(f"- {val}")
        lines.append("")
    _blk("Duplicate node ids", i.get("duplicate_node_ids"))
    _blk("Empty question text", i.get("empty_question_text"))
    _blk("Enum/Set without values", i.get("enum_or_set_without_values"))
    _blk("Edges with unknown endpoints", i.get("edges_with_unknown_endpoints"))
    _blk("Unreachable nodes from start", i.get("unreachable_nodes_from_start"))
    _blk("Dead-ends (non-terminal nodes)", i.get("dead_ends_nonterminal"))
    _blk("Missing predicates (used by edges but undefined)", i.get("missing_predicates"))
    _blk("Unused predicates (defined but not used)", i.get("unused_predicates"))
    _blk("Terminal alias nodes present", i.get("terminal_alias_nodes_present"))
    _blk("Canonical terminal present", i.get("canonical_terminal_present"))
    return "\n".join(lines)

