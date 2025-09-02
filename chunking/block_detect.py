# chunking/block_detect.py
from __future__ import annotations
import re
from typing import List, Dict, Tuple, Optional

IdMatch = Tuple[str, int]  # (prefix, char_pos)

_QID_RE = re.compile(
    r"""
    (?<![A-Za-z0-9_])          # left boundary
    ([A-Z]{1,6})               # PREFIX: 1..6 uppercase letters (D, FD, HSE, EMP, NDX, INFLATE, etc.)
    (?:\d{1,3}(?:_[A-Za-z0-9]+)?)  # number (and optional suffix like _rev or _OTHER)
    (?![A-Za-z0-9_])           # right boundary
    """,
    re.VERBOSE,
)

def _build_page_lookup(page_spans: List[Tuple[int, int, int]]):
    # page_spans: List[(start_char, end_char, page_no)], page_no is 1-indexed
    # Pre-sort just in case
    spans = sorted(page_spans, key=lambda t: t[0])
    starts = [s for (s, _, _) in spans]
    return spans, starts

def _char_to_page(pos: int, spans_sorted: List[Tuple[int, int, int]], starts_sorted: List[int]) -> int:
    # Binary search to map char pos to page
    lo, hi = 0, len(starts_sorted) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        s, e, p = spans_sorted[mid]
        if pos < s:
            hi = mid - 1
        elif pos >= e:
            lo = mid + 1
        else:
            return p
    # Fallback: clamp to nearest
    if not spans_sorted:
        return 1
    if pos < spans_sorted[0][0]:
        return spans_sorted[0][2]
    return spans_sorted[-1][2]

def _scan_ids(full_text: str) -> List[IdMatch]:
    out: List[IdMatch] = []
    for m in _QID_RE.finditer(full_text):
        prefix = m.group(1)
        out.append((prefix, m.start()))
    return out

def detect_blocks(
    full_text: str,
    page_spans: List[Tuple[int, int, int]],
    *,
    min_hits: int = 2,
    buffer_pages: int = 1,
) -> List[Dict]:
    """
    Detect blocks by clustering question IDs with the same PREFIX (letters before the number).
    Returns a list sorted by start_page:
      [{ "prefix": "D", "start_page": 1, "end_page": 6, "count": 18 }, ...]
    """
    spans, starts = _build_page_lookup(page_spans)
    matches = _scan_ids(full_text)
    if not matches:
        return []

    # Aggregate by prefix → min/max page
    stats: Dict[str, Dict[str, int]] = {}
    for prefix, pos in matches:
        page = _char_to_page(pos, spans, starts)
        st = stats.setdefault(prefix, {"min": page, "max": page, "count": 0})
        st["count"] += 1
        if page < st["min"]:
            st["min"] = page
        if page > st["max"]:
            st["max"] = page

    # Filter weak prefixes and buffer page ranges
    blocks: List[Dict] = []
    max_page = max(p for _, _, p in page_spans) if page_spans else 1
    for prefix, st in stats.items():
        if st["count"] < min_hits:
            continue
        start = max(1, st["min"] - buffer_pages)
        end = min(max_page, st["max"] + buffer_pages)
        blocks.append({
            "prefix": prefix,
            "start_page": start,
            "end_page": end,
            "count": st["count"],
        })

    # Sort by start_page, then by end_page ascending
    blocks.sort(key=lambda b: (b["start_page"], b["end_page"], b["prefix"]))
    return blocks

def summarize_blocks(blocks: List[Dict]) -> str:
    if not blocks:
        return "none"
    parts = [f"{b['prefix']}: p{b['start_page']}-{b['end_page']} (n={b['count']})" for b in blocks]
    return ", ".join(parts)

