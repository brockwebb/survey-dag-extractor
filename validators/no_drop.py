# validators/no_drop.py
from __future__ import annotations
from typing import List, Dict, Tuple
from chunking.smart_slicing import create_question_slices

def _tighten_slice(slice_text: str, qid: str, short_text: str | None,
                   before_chars: int, after_chars: int) -> str:
    if not slice_text:
        return slice_text
    anchor = -1
    if short_text:
        anchor = slice_text.find(short_text[:50])
    if anchor < 0 and qid:
        anchor = slice_text.find(qid)
    if anchor < 0:
        maxlen = before_chars + after_chars
        return slice_text[:maxlen] if len(slice_text) > maxlen else slice_text
    start = max(0, anchor - before_chars)
    end = min(len(slice_text), anchor + after_chars)
    return slice_text[start:end]

def ensure_nodes_for_all_index(
    ordered_index: List[Dict],
    content_nodes: List[Dict],
    full_text: str,
    page_spans: List[Tuple[int, int, int]],
    before_chars: int = 500,
    after_chars: int = 1400,
) -> List[Dict]:
    """
    Guarantee that every indexed question has a content node.
    If missing, create a conservative placeholder with best-guess text slice.
    """
    have = {n.get("id") for n in content_nodes if n.get("id")}
    need = [q for q in ordered_index if q.get("id") not in have]

    if not need:
        # Also normalize existing nodes (strip stray empties)
        return [n for n in content_nodes if n.get("id")]

    # Build slices for *all* questions (so we don't call into PDF multiple times)
    slices = create_question_slices(full_text, page_spans, ordered_index)

    out = [n for n in content_nodes if n.get("id")]
    for q in need:
        qid = q["id"]
        short_text = q.get("short_text")
        slice_text = _tighten_slice(slices.get(qid, ""), qid, short_text, before_chars, after_chars)
        placeholder = {
            "id": qid,
            "text": short_text or (slice_text[:300] if slice_text else None),
            "response_type": q.get("response_type") or "text",
            "response_options": None,
            "universe": q.get("universe"),
            "universe_ast": q.get("universe_ast"),
            "provenance": {"safety_net": True}
        }
        out.append(placeholder)

    # keep stable order by index
    order = {q["id"]: i for i, q in enumerate(ordered_index)}
    out.sort(key=lambda n: order.get(n["id"], 10**9))
    return out

