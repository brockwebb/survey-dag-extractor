# agents/index_safety_pass.py
from __future__ import annotations
from typing import List, Dict, Tuple, Callable
from dataclasses import dataclass

@dataclass
class SafetyPassConfig:
    early_pages: int = 6       # scan first N pages explicitly (screeners/consent)
    use_full_doc: bool = True  # also scan the entire document text as one window

class IndexSafetyPass:
    """
    Lightweight high-recall pass that asks the index agent to enumerate
    *all* question IDs and first-line text from (a) the first N pages and
    (b) optionally the entire document, then unions results.

    It reuses your existing QuestionIndexAgent to avoid diverging prompts.
    """
    def __init__(self, index_agent, limiter, max_retries: int, base_delay: float, max_delay: float,
                 cfg: SafetyPassConfig | None = None,
                 with_retries: Callable | None = None):
        self.agent = index_agent
        self.limiter = limiter
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.cfg = cfg or SafetyPassConfig()
        self._with_retries = with_retries

    def _dedupe_index(self, items: List[Dict]) -> List[Dict]:
        seen = set(); out = []
        # sort by page_guess then id for determinism
        for item in sorted(items, key=lambda x: (x.get("page_guess", 10**9), x.get("id",""))):
            _id = item.get("id")
            if not _id or _id in seen:
                continue
            seen.add(_id)
            out.append(item)
        return out

    def run(self, full_text: str, page_spans: List[Tuple[int,int,int]]) -> List[Dict]:
        """
        full_text: entire PDF text
        page_spans: [(start_char, end_char, page_num), ...]
        returns: list of {'id','short_text','page_guess',...}
        """
        all_items: List[Dict] = []

        # 1) Early window (first N pages), very high recall for early content
        try:
            early_n = min(self.cfg.early_pages, page_spans[-1][2])
            s0, _ = page_spans[0]
            _, eN = page_spans[early_n-1]
            early_text = full_text[s0:eN]
            doc_early = self._with_retries(
                lambda: self.agent.run_window(early_text, page_start=1),
                limiter=self.limiter,
                max_retries=self.max_retries,
                base_delay=self.base_delay,
                max_delay=self.max_delay,
            )
            all_items.extend(doc_early.get("question_index", []))
        except Exception:
            # fail-soft: safety pass should never crash the run
            pass

        # 2) Full document single-span pass (optional)
        if self.cfg.use_full_doc:
            try:
                doc_full = self._with_retries(
                    lambda: self.agent.run_window(full_text, page_start=1),
                    limiter=self.limiter,
                    max_retries=self.max_retries,
                    base_delay=self.base_delay,
                    max_delay=self.max_delay,
                )
                all_items.extend(doc_full.get("question_index", []))
            except Exception:
                pass

        return self._dedupe_index(all_items)

