# chunking/page_windows.py
from __future__ import annotations
from typing import List, Dict, Tuple

def _page_to_span_map(page_spans: List[Tuple[int, int, int]]):
    return {p: (s, e) for (s, e, p) in page_spans}

def _slice_text(full_text: str, page_spans: List[Tuple[int, int, int]], start_page: int, end_page: int) -> str:
    mp = _page_to_span_map(page_spans)
    s0, _ = mp.get(start_page, (0, 0))
    _, e1 = mp.get(end_page, (len(full_text), len(full_text)))
    if s0 >= e1:
        return ""
    return full_text[s0:e1]

def chunk_text_by_pages(
    full_text: str,
    page_spans: List[Tuple[int, int, int]],
    *,
    chunk_size: int = 8,
    overlap: int = 1,
) -> List[Dict]:
    """
    Fixed-size page windows with overlap.
    Returns: [{"idx": i, "start_page": a, "end_page": b, "text": "..."}]
    """
    if not page_spans:
        return [{"idx": 0, "start_page": 1, "end_page": 1, "text": full_text}]

    max_page = max(p for _, _, p in page_spans)
    windows: List[Dict] = []
    idx = 0
    start = 1
    step = max(1, chunk_size - overlap)
    while start <= max_page:
        end = min(max_page, start + chunk_size - 1)
        txt = _slice_text(full_text, page_spans, start, end)
        windows.append({"idx": idx, "start_page": start, "end_page": end, "text": txt})
        idx += 1
        if end == max_page:
            break
        start = end - overlap + 1
    return windows

def chunk_text_by_blocks(
    full_text: str,
    page_spans: List[Tuple[int, int, int]],
    blocks: List[Dict],
) -> List[Dict]:
    """
    Block-aware windows from detected block page ranges.
    Merges overlapping/adjacent ranges to reduce redundant calls.
    """
    if not blocks:
        return [{"idx": 0, "start_page": 1, "end_page": (max(p for _, _, p in page_spans) if page_spans else 1),
                 "text": full_text}]
    # Merge overlapping or adjacent block ranges
    ranges = [(b["start_page"], b["end_page"]) for b in blocks]
    ranges.sort()
    merged: List[Tuple[int, int]] = []
    for (s, e) in ranges:
        if not merged:
            merged.append((s, e))
        else:
            ps, pe = merged[-1]
            if s <= pe + 1:
                merged[-1] = (ps, max(pe, e))
            else:
                merged.append((s, e))
    # Build windows
    windows: List[Dict] = []
    for i, (s, e) in enumerate(merged):
        txt = _slice_text(full_text, page_spans, s, e)
        windows.append({"idx": i, "start_page": s, "end_page": e, "text": txt})
    return windows
