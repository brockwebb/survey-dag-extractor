# merge/merge_core.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple, Optional

def flatten_values(options):
    if not options: return []
    if all(isinstance(o,(str,int,float)) for o in options): return options
    dicts=[o for o in options if isinstance(o,dict)]
    if dicts and len(dicts)==len(options):
        have_codes = all("code" in o for o in dicts)
        if have_codes:
            vals=[o["code"] for o in dicts]
            return [int(v) if isinstance(v,str) and v.isdigit() else v for v in vals]
        return [o.get("text") for o in dicts if isinstance(o.get("text"), str)]
    return [str(o) for o in options if o is not None]

def labels_annotation(options):
    if not options or not all(isinstance(o,dict) for o in options): return None
    pairs=[]
    for o in options:
        c,t=o.get("code"), o.get("text")
        if c is not None and t: pairs.append(f"{c}={t}")
    return ("labels: " + "; ".join(pairs)) if pairs else None

def page_for_text(extraction_text: str, full_text: str, page_spans: List[Tuple[int,int,int]]) -> Optional[int]:
    if not extraction_text: return None
    idx = full_text.find(extraction_text[:120])
    if idx < 0: return None
    mid = idx + min(len(extraction_text),120)//2
    for start,end,page in page_spans:
        if start <= mid < end: return page
    return None

def merge_to_core(structure: dict, content: dict, *, full_text: str, page_spans: List[tuple[int,int,int]]) -> dict:
    S = structure["survey_dag_structure"]
    Cmap = {n["id"]: n for n in content["survey_content"]["nodes"]}

    nodes_out=[]; edges_out=[]
    for idx, n in enumerate(S["nodes"]):
        qid = n.get("id")
        kind = n.get("kind") or "question"
        cn = Cmap.get(qid, {})
        text = (cn.get("text") or "").strip()
        rtype = cn.get("response_type") or n.get("response_type") or "text"
        ropts = cn.get("response_options") or []
        flat = flatten_values(ropts)
        ann = labels_annotation(ropts)
        page_num = page_for_text(text, full_text, page_spans) if text else None

        node_obj = {
            "id": qid,
            "type": "terminal" if kind=="terminal" else ("junction" if kind=="junction" else "question"),
            "order_index": idx,
            "block": n.get("block"),
            "domain": {"kind": rtype, "values": flat},
            "metadata": {"text": text, "required": False}
        }
        if ann: node_obj.setdefault("annotations", []).append(ann)
        if page_num:
            node_obj["provenance"] = {"method":"langextract","locators":[{"type":"page","value":str(page_num)}]}
        nodes_out.append(node_obj)

    for e in S.get("edges", []):
        edges_out.append({
            "id": f"E_{len(edges_out)+1:010d}",
            "source": e["source"],
            "target": e["target"],
            "predicate": e.get("predicate") or "P_TRUE",
            "kind": "fallthrough",
            "subkind": "sequence",
            "priority": 0
        })

    if "END_COMPLETE" not in {n["id"] for n in nodes_out}:
        nodes_out.append({"id":"END_COMPLETE","type":"terminal","order_index":len(nodes_out)})

    if nodes_out and not any(e["target"]=="END_COMPLETE" for e in edges_out):
        last_q = next((n["id"] for n in reversed(nodes_out) if n["type"]=="question"), None)
        if last_q:
            edges_out.append({
                "id": f"E_{len(edges_out)+1:010d}",
                "source": last_q,
                "target": "END_COMPLETE",
                "predicate": "P_TRUE",
                "kind": "terminate",
                "subkind": "terminal_exit",
                "priority": 0
            })

    dag = {
      "survey_dag": {
        "metadata": {
          "id": S["id"],
          "title": "Household Trends and Outlook Pulse Survey (HTOPS) – Feb 2025",
          "version": S["version"],
          "objective": "edge",
          "build": {
            "extractor_version": "langextract-1.x",
            "extracted_at": __import__("datetime").datetime.utcnow().isoformat()+"Z",
            "method": "llm_extraction",
            "source_format": "pdf",
            "validation_passed": False,
            "post_edit": False
          }
        },
        "graph": {
          "start": S["start"] or (nodes_out[0]["id"] if nodes_out else "Q1"),
          "terminals": ["END_COMPLETE"],
          "nodes": nodes_out,
          "edges": edges_out
        },
        "predicates": {pid: {"ast": p.get("ast") or ["TRUE"], "text": p.get("expr") or ""} for pid, p in S.get("predicates", {}).items()},
        "validation": {"status":"FAIL","issues":[],"gates":{}},
        "analysis": {},
        "coverage": {}
      }
    }
    return dag

