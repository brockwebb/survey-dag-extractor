# utils/normalize.py
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

_ID_SAFE = re.compile(r"[^A-Za-z0-9_]+")

def _canonicalize_id(qid: str) -> str:
    # keep IDs stable but strip weird glyphs like "EMP■7" -> "EMP7"
    # do NOT collapse underscores to avoid accidental merges
    return _ID_SAFE.sub("", qid or "").strip() or "NODE"

def _flatten_option(x: Any) -> Tuple[Any, Dict[str, Any] | None]:
    """
    Returns (schema_value, rich_record_or_None).
    - schema_value: string|number (schema-compliant)
    - rich_record:  {code, text} if present (for sidecar)
    """
    if isinstance(x, dict):
        text = x.get("text") or x.get("label") or x.get("value")
        code = x.get("code")
        if text is not None:
            return text, {"code": code, "text": text}
        if code is not None:
            return code, {"code": code, "text": str(code)}
        # last resort: stringify whole dict
        return str(x), {"code": None, "text": str(x)}
    # already scalar and schema-friendly
    return x, None

def _flatten_values(val_list: Any) -> Tuple[List[Any], List[Dict[str, Any]]]:
    vals: List[Any] = []
    rich: List[Dict[str, Any]] = []
    if not isinstance(val_list, list):
        return vals, rich
    for v in val_list:
        flat, rec = _flatten_option(v)
        vals.append(flat)
        if rec is not None:
            rich.append(rec)
    return vals, rich

def coerce_to_schema_nlossy(core_doc: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Make the doc pass your strict JSON schema **without losing info**.
    - Returns (normalized_core, sidecar)
    Sidecar contains any rich option/value mappings and ID renames so you can round-trip.
    """
    sidecar: Dict[str, Any] = {"id_map": {}, "option_maps": {}, "domain_value_maps": {}}

    sd = core_doc.get("survey_dag") or core_doc.get("survey_dag_core") or {}
    graph = sd.get("graph", {})
    nodes = graph.get("nodes", [])

    # Normalize node IDs (non-ascii glyph cleanup) + collect sidecar id_map
    seen_ids: Dict[str, int] = {}
    for n in nodes:
        old_id = n.get("id")
        new_id = _canonicalize_id(old_id) if isinstance(old_id, str) else "NODE"
        if new_id in seen_ids:
            seen_ids[new_id] += 1
            new_id = f"{new_id}_{seen_ids[new_id]}"
        else:
            seen_ids[new_id] = 1

        if new_id != old_id and old_id:
            sidecar["id_map"][old_id] = new_id
            n["id"] = new_id

    # Rewrite edges with any ID remaps (no drops)
    for e in graph.get("edges", []):
        s = e.get("source")
        t = e.get("target")
        if s in sidecar["id_map"]:
            e["source"] = sidecar["id_map"][s]
        if t in sidecar["id_map"]:
            e["target"] = sidecar["id_map"][t]

    # Flatten response_options and domain.values, collecting rich info into sidecar
    for n in nodes:
        qid = n.get("id")
        # Response options -> strings/numbers for schema + keep (code,text) in sidecar
        if isinstance(n.get("response_options"), list):
            flat_opts, rich_opts = _flatten_values(n["response_options"])
            n["response_options"] = flat_opts
            if rich_opts:
                sidecar["option_maps"][qid] = rich_opts

        # Domain values -> strings/numbers + keep mapping
        domain = n.get("domain")
        if isinstance(domain, dict) and isinstance(domain.get("values"), list):
            flat_vals, rich_vals = _flatten_values(domain["values"])
            n.setdefault("domain", {})["values"] = flat_vals
            if rich_vals:
                sidecar["domain_value_maps"][qid] = rich_vals

    # Ensure start/terminals exist as nodes if referenced (no-op if already present)
    node_ids = {n.get("id") for n in nodes}
    start_id = sd.get("start")
    if start_id and start_id not in node_ids:
        nodes.insert(0, {"id": start_id, "kind": "junction", "block": None,
                         "response_type": None, "universe": None, "universe_ast": None})
        node_ids.add(start_id)

    for term in sd.get("terminals", []) or []:
        if term not in node_ids:
            nodes.append({"id": term, "kind": "terminal", "block": None,
                          "response_type": None, "universe": None, "universe_ast": None})
            node_ids.add(term)

    # Return updated structure
    if "survey_dag_core" in core_doc:
        core_doc["survey_dag_core"]["graph"]["nodes"] = nodes
    else:
        core_doc["survey_dag"]["graph"]["nodes"] = nodes

    return core_doc, sidecar

