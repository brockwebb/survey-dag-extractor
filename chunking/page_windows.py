# chunking/page_windows.py
from __future__ import annotations
from typing import List, Tuple, Dict

def chunk_text_by_pages(
    full_text: str,
    page_spans: List[Tuple[int, int, int]],
    *,
    chunk_size: int = 10,
    overlap: int = 2,
) -> List[Dict]:
    """
    Create overlapping page windows and slice the PDF's extracted text accordingly.

    page_spans: [(start_char, end_char, page_number starting at 1), ...] in ascending page order.
    Returns: [{"idx": 0, "pages": [p...], "start_page": p1, "end_page": pN, "text": "..."}...]
    """
    assert chunk_size >= 1, "chunk_size must be >= 1"
    assert 0 <= overlap < chunk_size, "overlap must be in [0, chunk_size-1]"

    n_pages = len(page_spans)
    if n_pages == 0:
        return []

    windows: List[Dict] = []
    step = chunk_size - overlap
    i = 0
    widx = 0
    while i < n_pages:
        j = min(i + chunk_size, n_pages)
        span_slice = page_spans[i:j]
        start_char = span_slice[0][0]
        end_char = span_slice[-1][1]
        pages = [p for (_, _, p) in span_slice]
        text = full_text[start_char:end_char]
        windows.append({
            "idx": widx,
            "pages": pages,
            "start_page": pages[0],
            "end_page": pages[-1],
            "text": text,
        })
        widx += 1
        i += step
    return windows

