# reducers/lossless_merge.py
from __future__ import annotations
from typing import Dict, List, Any, Tuple

def _rtype_rank(rt: str | None) -> int:
    # Prefer richer, more structured types
    order = ["enum", "set", "number", "text", None]
    try:
        return order.index(rt if rt in order else None)
    except ValueError:
        return len(order)

def _best_response_type(a: str | None, b: str | None) -> str | None:
    # Lower rank is better
    ra, rb = _rtype_rank(a), _rtype_rank(b)
    return a if ra <= rb else b

def _normalize_option(opt: Any) -> Tuple[str, str]:
    """
    Normalize a response option for dedupe union.
    Returns a key = (code_or_text, text_lower) used to detect duplicates.
    """
    if isinstance(opt, dict):
        code = str(opt.get("code", "")).strip()
        text = (opt.get("text") or "").strip()
        key = (code if code else text, text.lower())
    else:
        text = str(opt).strip()
        key = (text, text.lower())
    return key

def _union_options(a: List[Any] | None, b: List[Any] | None) -> List[Any] | None:
    if not a and not b:
        return None
    out: List[Any] = []
    seen: set[Tuple[str, str]] = set()
    for src in (a or []) + (b or []):
        key = _normalize_option(src)
        if key in seen:
            continue
        seen.add(key)
        out.append(src)
    return out

def _longer_text(a: str | None, b: str | None) -> str | None:
    a = a or ""
    b = b or ""
    if len(b) > len(a):
        return b
    return a if a else (b or None)

def merge_content_nodes(nodes: List[Dict]) -> List[Dict]:
    """
    Lossless, LLM-friendly merge:
      - choose longer question text
      - prefer response_type by richness (enum > set > number > text > None)
      - union response_options by (code/text) keys
      - keep universe fields if present
      - preserve provenance if available
    """
    by_id: Dict[str, Dict] = {}
    for n in nodes:
        qid = n.get("id")
        if not qid:
            continue
        if qid not in by_id:
            by_id[qid] = dict(n)
            continue
        base = by_id[qid]

        base["text"] = _longer_text(base.get("text"), n.get("text"))
        base["response_type"] = _best_response_type(base.get("response_type"), n.get("response_type"))
        base["response_options"] = _union_options(base.get("response_options"), n.get("response_options"))

        # keep universe if absent
        if base.get("universe") is None and n.get("universe") is not None:
            base["universe"] = n.get("universe")
        if base.get("universe_ast") is None and n.get("universe_ast") is not None:
            base["universe_ast"] = n.get("universe_ast")

        # light provenance union
        prov_a = base.get("provenance") or {}
        prov_b = n.get("provenance") or {}
        if prov_a or prov_b:
            merged_prov = dict(prov_a)
            for k, v in prov_b.items():
                if k not in merged_prov:
                    merged_prov[k] = v
            base["provenance"] = merged_prov

    # return in stable id order
    return [by_id[k] for k in sorted(by_id.keys())]

def normalize_predicates(struct: Dict, *, allow_underscores: bool = True) -> Dict:
    """
    Make predicate IDs schema-safe (upper-case, allowed chars) and
    propagate any renames into edges.
    If allow_underscores=True, we only uppercase and strip spaces.
    """
    if not struct:
        return struct
    preds = struct.get("predicates") or {}
    if not preds:
        struct["predicates"] = {}
        return struct

    new_preds: Dict[str, Any] = {}
    rename_map: Dict[str, str] = {}

    def to_safe(pid: str) -> str:
        s = (pid or "").strip().upper()
        if allow_underscores:
            # keep A-Z0-9_ only
            s = "".join(ch for ch in s if (ch.isalnum() or ch == "_"))
            if not s.startswith("P_"):
                s = "P_" + s
        else:
            # stricter: drop underscores
            s = "".join(ch for ch in s if ch.isalnum())
            if not s.startswith("P"):
                s = "P" + s
        return s

    for pid, body in preds.items():
        safe = to_safe(pid)
        rename_map[pid] = safe
        # ensure body fields are preserved
        new_preds[safe] = body

    # rewrite edges to use new IDs
    edges = struct.get("edges") or []
    for e in edges:
        p = e.get("predicate")
        if p in rename_map:
            e["predicate"] = rename_map[p]

    struct["predicates"] = new_preds
    struct["edges"] = edges
    return struct

