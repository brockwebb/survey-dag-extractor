# reducers/chunk_reduce.py
from __future__ import annotations
from typing import Dict, List
from collections import OrderedDict

CANON_TERMINAL = "END_COMPLETE"

def _first_non_null(*vals):
    for v in vals:
        if v is not None:
            return v
    return None

def reduce_structure_chunks(chunks: List[Dict]) -> Dict:
    """
    Union + dedupe by first-seen node id. Edges and predicates are unioned (first-wins on conflicts).
    Each chunk is a {"survey_dag_structure": {...}} doc.
    """
    nodes_by_id: "OrderedDict[str, dict]" = OrderedDict()
    edges: List[dict] = []
    preds: "OrderedDict[str, dict]" = OrderedDict()

    survey_id = None
    version = None
    start_id = None

    for ch in chunks:
        s = ch.get("survey_dag_structure", {})
        survey_id = survey_id or s.get("id")
        version = version or s.get("version")
        if not start_id:
            # tentative start = first node of first chunk
            ns = s.get("nodes", [])
            if ns:
                start_id = ns[0].get("id")

        for n in s.get("nodes", []):
            nid = n.get("id")
            if not nid or nid in nodes_by_id:
                continue
            # keep first-seen node definition
            nodes_by_id[nid] = {
                "id": nid,
                "kind": _first_non_null(n.get("kind"), "question"),
                "block": n.get("block"),
                "response_type": n.get("response_type"),
                "universe": n.get("universe"),
                "universe_ast": n.get("universe_ast"),
            }

        for e in s.get("edges", []):
            if not (e.get("source") and e.get("target")):
                continue
            edges.append({
                "source": e["source"],
                "target": e["target"],
                "predicate": e.get("predicate") or "P_TRUE",
            })

        for pid, p in (s.get("predicates") or {}).items():
            if pid in preds:
                continue
            preds[pid] = {
                "expr": p.get("expr") or "",
                "ast": p.get("ast") or ["TRUE"],
                "depends_on": p.get("depends_on") or [],
            }

    # ensure canonical terminal presence
    if CANON_TERMINAL not in nodes_by_id:
        nodes_by_id[CANON_TERMINAL] = {
            "id": CANON_TERMINAL,
            "kind": "terminal",
            "block": None,
            "response_type": None,
            "universe": None,
            "universe_ast": None,
        }

    return {
        "survey_dag_structure": {
            "id": survey_id or "survey",
            "version": version or "v0",
            "start": start_id or next(iter(nodes_by_id)).strip(),
            "terminals": [CANON_TERMINAL],
            "nodes": list(nodes_by_id.values()),
            "edges": edges,
            "predicates": dict(preds),
        }
    }

def reduce_content_chunks(chunks: List[Dict]) -> Dict:
    """
    Union + dedupe by id. On conflict:
      - take longest 'text'
      - keep first response_type unless later is clearly better (enum/set over text/number)
      - choose options list with the most entries.
    Each chunk is {"survey_content": {"nodes":[...]}}.
    """
    def better_type(curr: str|None, new: str|None) -> str|None:
        order = {"enum":3, "set":3, "number":2, "text":1, "boolean":2, None:0}
        return new if (order.get(new,0) > order.get(curr,0)) else curr

    by_id: OrderedDict[str, dict] = OrderedDict()

    for ch in chunks:
        nodes = (ch.get("survey_content") or {}).get("nodes", [])
        for n in nodes:
            nid = n.get("id")
            if not nid: 
                continue
            if nid not in by_id:
                by_id[nid] = {
                    "id": nid,
                    "text": n.get("text") or "",
                    "response_type": n.get("response_type"),
                    "response_options": n.get("response_options"),
                }
                continue

            cur = by_id[nid]
            # prefer longer text
            if len(n.get("text") or "") > len(cur.get("text") or ""):
                cur["text"] = n.get("text") or cur.get("text")

            # prefer stronger type (enum/set over text/number)
            cur["response_type"] = better_type(cur.get("response_type"), n.get("response_type")) or cur.get("response_type")

            # choose the option list with more entries
            ro_cur = cur.get("response_options") or []
            ro_new = n.get("response_options") or []
            if len(ro_new) > len(ro_cur):
                cur["response_options"] = ro_new

    return {"survey_content": {"nodes": list(by_id.values())}}

