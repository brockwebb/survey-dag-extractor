# compare_dags.py
from __future__ import annotations
import argparse, json
from pathlib import Path
from difflib import SequenceMatcher
from collections import Counter

def load_json(p: Path):
    return json.loads(Path(p).read_text())

def normalize_text(s: str) -> str:
    if not s: return ""
    return " ".join(str(s).split())  # collapse whitespace

def first_page_from_provenance(node: dict) -> int | None:
    prov = node.get("provenance") or {}
    locs = prov.get("locators") or []
    for loc in locs:
        if isinstance(loc, dict) and loc.get("type") == "page":
            v = loc.get("value")
            try:
                return int(str(v))
            except Exception:
                return None
    return None

def extract_questions(dag: dict) -> dict[str, dict]:
    sd = dag.get("survey_dag", {})
    nodes = (sd.get("graph") or {}).get("nodes") or []
    out = {}
    for n in nodes:
        if not isinstance(n, dict): 
            continue
        if n.get("type") != "question": 
            continue
        qid = n.get("id")
        if not qid: 
            continue
        dom = n.get("domain") or {}
        vals = dom.get("values") or []
        # normalize values to strings for set comparison
        vals_norm = [str(v) for v in vals if v is not None]
        text = ((n.get("metadata") or {}).get("text")) or ""
        out[qid] = {
            "id": qid,
            "text": normalize_text(text),
            "block": n.get("block"),
            "kind": dom.get("kind"),
            "values": vals_norm,
            "values_set": set(vals_norm),
            "values_len": len(vals_norm),
            "page": first_page_from_provenance(n),
        }
    return out

def summarize(dag: dict) -> dict:
    sd = dag.get("survey_dag", {})
    meta = sd.get("metadata", {})
    graph = sd.get("graph", {}) or {}
    nodes = graph.get("nodes", []) or []
    edges = graph.get("edges", []) or []
    start = graph.get("start")
    node_ids = [n.get("id") for n in nodes if isinstance(n, dict)]
    dup = [k for k,v in Counter(node_ids).items() if v > 1]
    return {
        "title": meta.get("title"),
        "version": meta.get("version"),
        "build_method": (meta.get("build") or {}).get("method"),
        "nodes_total": len(nodes),
        "edges_total": len(edges),
        "start": start,
        "dup_nodes": dup,
    }

def compare(a: dict, b: dict, limit: int = 25) -> dict:
    qa = extract_questions(a)
    qb = extract_questions(b)
    ids_a, ids_b = set(qa), set(qb)
    inter = ids_a & ids_b
    union = ids_a | ids_b

    changed_text = []
    changed_block = []
    changed_kind = []
    changed_values_len = []
    changed_values_set = []
    changed_page = []

    for qid in sorted(inter):
        A, B = qa[qid], qb[qid]

        # text similarity
        if A["text"] != B["text"]:
            sim = SequenceMatcher(None, A["text"], B["text"]).ratio()
            changed_text.append({"id": qid, "similarity": round(sim, 3)})

        # block/kind/values/page diffs
        if A["block"] != B["block"]:
            changed_block.append({"id": qid, "a": A["block"], "b": B["block"]})
        if A["kind"] != B["kind"]:
            changed_kind.append({"id": qid, "a": A["kind"], "b": B["kind"]})
        if A["values_len"] != B["values_len"]:
            changed_values_len.append({"id": qid, "a": A["values_len"], "b": B["values_len"]})
        if A["values_set"] != B["values_set"]:
            # show small symmetric difference
            added = sorted(list(B["values_set"] - A["values_set"]))[:10]
            removed = sorted(list(A["values_set"] - B["values_set"]))[:10]
            changed_values_set.append({"id": qid, "added": added, "removed": removed})
        if A["page"] != B["page"]:
            changed_page.append({"id": qid, "a": A["page"], "b": B["page"]})

    summary = {
        "counts": {
            "questions_a": len(qa),
            "questions_b": len(qb),
            "overlap": len(inter),
            "jaccard": round(len(inter) / len(union), 3) if union else 1.0,
            "only_in_a": len(ids_a - ids_b),
            "only_in_b": len(ids_b - ids_a),
        },
        "only_in_a": sorted(list(ids_a - ids_b))[:limit],
        "only_in_b": sorted(list(ids_b - ids_a))[:limit],
        "changed": {
            "text": sorted(changed_text, key=lambda x: x["similarity"])[:limit],
            "block": changed_block[:limit],
            "kind": changed_kind[:limit],
            "values_len": changed_values_len[:limit],
            "values_set": changed_values_set[:limit],
            "page": changed_page[:limit],
        },
    }
    return summary

def main():
    ap = argparse.ArgumentParser(description="Compare two DAG JSONs (nodes, text, domains, values).")
    ap.add_argument("file_a", help="Path to first dag.json")
    ap.add_argument("file_b", help="Path to second dag.json")
    ap.add_argument("--limit", type=int, default=25, help="Max rows to show per diff bucket")
    ap.add_argument("--out", default=None, help="Optional path to write a JSON report")
    args = ap.parse_args()

    a = load_json(Path(args.file_a))
    b = load_json(Path(args.file_b))
    sum_a, sum_b = summarize(a), summarize(b)
    rep = compare(a, b, limit=args.limit)

    # Pretty print
    print("=== A ===")
    print(json.dumps(sum_a, indent=2))
    print("\n=== B ===")
    print(json.dumps(sum_b, indent=2))

    print("\n=== COMPARISON SUMMARY ===")
    print(json.dumps(rep["counts"], indent=2))

    def show(title, rows):
        print(f"\n-- {title} --")
        if not rows:
            print("  (none)")
        else:
            print(json.dumps(rows, indent=2))

    show("IDs only in A", rep["only_in_a"])
    show("IDs only in B", rep["only_in_b"])
    c = rep["changed"]
    show("Changed TEXT (lowest similarity first)", c["text"])
    show("Changed BLOCK", c["block"])
    show("Changed KIND", c["kind"])
    show("Changed VALUES length", c["values_len"])
    show("Changed VALUES set (samples)", c["values_set"])
    show("Changed PAGE provenance", c["page"])

    if args.out:
        Path(args.out).write_text(json.dumps({"summary_a": sum_a, "summary_b": sum_b, "diffs": rep}, indent=2))
        print(f"\nWrote report to {args.out}")

if __name__ == "__main__":
    main()

