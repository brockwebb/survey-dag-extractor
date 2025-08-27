# chunking/smart_slicing.py
from __future__ import annotations
from typing import List, Tuple, Dict

def create_question_slices(full_text: str, page_spans: List[Tuple[int,int,int]],
                           question_index: List[Dict]) -> Dict[str, str]:
    """
    Create focused text slices for each question using context-aware windowing.
    
    Strategy:
    1. For each question, find its approximate location in full_text
    2. Expand window to include likely related content (skip logic, follow-ups)
    3. Use overlapping windows to avoid missing cross-references
    
    Returns: {question_id: text_slice}
    """
    # Build page-to-text mapping for quick lookups
    page_to_span = {p: (s, e) for (s, e, p) in page_spans}
    
    question_slices = {}
    
    for i, q in enumerate(question_index):
        qid = q["id"]
        page_guess = q["page_guess"]
        short_text = q.get("short_text", "")
        
        # Strategy 1: Find question by searching for its short_text
        if short_text:
            text_pos = full_text.find(short_text[:50])  # First 50 chars should be unique
            if text_pos >= 0:
                # Found exact position - create generous window around it
                window_start = max(0, text_pos - 1500)  # 1500 chars before
                window_end = min(len(full_text), text_pos + 3000)  # 3000 chars after
                question_slices[qid] = full_text[window_start:window_end]
                continue
        
        # Strategy 2: Fall back to page-based slicing with generous context
        try:
            # Use current page + next 2 pages for context
            end_page = min(page_guess + 2, max(p for _, _, p in page_spans))
            start_char, _ = page_to_span[page_guess]
            _, end_char = page_to_span[end_page]
            
            # Add buffer before start page if available
            if page_guess > 1:
                buffer_start, _ = page_to_span[page_guess - 1]
                start_char = buffer_start
            
            question_slices[qid] = full_text[start_char:end_char]
            
        except KeyError:
            # Final fallback: just use the question's page
            try:
                start_char, end_char = page_to_span[page_guess]
                question_slices[qid] = full_text[start_char:end_char]
            except Exception:
                # Ultimate fallback: empty slice (will be handled by content agent)
                question_slices[qid] = ""
    
    return question_slices


def validate_extraction_quality(question_index: List[Dict],
                                content_nodes: List[Dict],
                                structure_edges: List[Dict]) -> Dict:
    """
    Detect error accumulation patterns before they compound.
    
    Returns quality metrics and warnings.
    """
    index_ids = {q["id"] for q in question_index}
    content_ids = {n["id"] for n in content_nodes if n.get("id")}
    edge_ids = set()
    for e in structure_edges:
        if e.get("source"): edge_ids.add(e["source"])
        if e.get("target"): edge_ids.add(e["target"])
    
    metrics = {
        "index_count": len(index_ids),
        "content_count": len(content_ids),
        "edge_reference_count": len(edge_ids),
        "content_coverage": len(content_ids & index_ids) / len(index_ids) if index_ids else 0.0,
        "edge_coverage": len(edge_ids & index_ids) / len(edge_ids) if edge_ids else 1.0,
        "warnings": []
    }
    
    # Error accumulation indicators
    if metrics["content_coverage"] < 0.8:
        metrics["warnings"].append(f"Low content coverage: {metrics['content_coverage']:.1%}")
    
    if metrics["edge_coverage"] < 0.7:
        metrics["warnings"].append(f"Many edges reference unknown questions: {1-metrics['edge_coverage']:.1%}")
    
    # Check for empty content nodes (extraction failures)
    empty_content = [n["id"] for n in content_nodes if not n.get("text") or len(n.get("text", "")) < 10]
    if empty_content:
        metrics["warnings"].append(f"Empty content for {len(empty_content)} questions: {empty_content[:5]}")
    
    # Check for unreasonable response options (hallucination indicator)
    for n in content_nodes:
        opts = n.get("response_options", [])
        if opts and len(opts) > 20:  # Suspiciously many options
            metrics["warnings"].append(f"Question {n['id']} has {len(opts)} options (possible hallucination)")
    
    return metrics


def early_quality_gate(metrics: Dict, min_coverage: float = 0.7) -> bool:
    """
    Stop processing early if quality is too low to prevent error accumulation.
    
    Returns: True if quality is acceptable, False if should abort
    """
    if metrics["content_coverage"] < min_coverage:
        print(f"QUALITY GATE FAILED: Content coverage {metrics['content_coverage']:.1%} < {min_coverage:.1%}")
        return False
    
    if len(metrics["warnings"]) > 5:
        print(f"QUALITY GATE FAILED: Too many warnings ({len(metrics['warnings'])})")
        return False
    
    return True
