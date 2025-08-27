# io_utils/pdf_utils.py
from __future__ import annotations
from pathlib import Path
from typing import List, Tuple, Optional
import pdfplumber

def read_pdf_all_text_with_spans(path: Path) -> tuple[str, list[tuple[int,int,int]]]:
    parts: list[str] = []
    spans: list[tuple[int,int,int]] = []
    cursor = 0
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages):
            t = page.extract_text() or ""
            parts.append(t)
            start = cursor
            cursor += len(t)
            spans.append((start, cursor, i+1))
    return "".join(parts), spans

def page_for_text(extraction_text: str, full_text: str, page_spans: List[Tuple[int,int,int]]) -> Optional[int]:
    if not extraction_text:
        return None
    idx = full_text.find(extraction_text[:120])
    if idx < 0:
        return None
    mid = idx + min(len(extraction_text), 120)//2
    for start, end, page in page_spans:
        if start <= mid < end:
            return page
    return None
