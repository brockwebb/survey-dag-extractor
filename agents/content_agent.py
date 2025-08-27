# agents/content_agent.py
from __future__ import annotations
import os, contextlib, io
from typing import Dict, List
import langextract as lx

def _content_prompt() -> str:
    return """
<task>
Extract ONLY CONTENT: one record per question/sub-item with full text and options.
Use extraction_class="question_content".
</task>
<rules>
- id: prefer printed; for batteries emit CHILD items as PARENT_1..N and DO NOT emit parent-only.
- response_type: enum|set|number|text|boolean
- Yes/No => enum with codes 1=Yes, 2=No
- response_options ONLY for enum/set; codes must be contiguous 1..N in order; labels verbatim.
- No hallucinated options; rely only on provided text.
</rules>
""".strip()

def _examples() -> List[lx.data.ExampleData]:
    return [
        lx.data.ExampleData(
            text="Q1. What is your age? 1 Under 18 2 18–24 3 25–34 4 35–44 5 45–54 6 55+",
            extractions=[
                lx.data.Extraction(
                    extraction_class="question_content",
                    extraction_text="Q1. What is your age?",
                    attributes={
                        "id": "Q1",
                        "response_type": "enum",
                        "response_options": [
                            {"code": 1, "text": "Under 18"},
                            {"code": 2, "text": "18–24"},
                            {"code": 3, "text": "25–34"},
                            {"code": 4, "text": "35–44"},
                            {"code": 5, "text": "45–54"},
                            {"code": 6, "text": "55+"}
                        ]
                    }
                )
            ]
        ),
        lx.data.ExampleData(
            text="HLTH2. Do you currently have health insurance? (Yes/No)",
            extractions=[
                lx.data.Extraction(
                    extraction_class="question_content",
                    extraction_text="HLTH2. Do you currently have health insurance?",
                    attributes={
                        "id": "HLTH2",
                        "response_type": "enum",
                        "response_options": [{"code": 1, "text": "Yes"}, {"code": 2, "text": "No"}]
                    }
                )
            ]
        )
    ]

def _coerce_extractions(res):
    if hasattr(res, "extractions"): return res.extractions
    if hasattr(res, "to_dict"):
        d = res.to_dict()
        if isinstance(d, dict) and "extractions" in d: return d["extractions"]
    if isinstance(res, dict): return res.get("extractions", [])
    return []

class ContentAgent:
    def __init__(self, model: str, passes=3, workers=8, char_buf=1200, quiet=True):
        self.model=model; self.passes=passes; self.workers=workers; self.char_buf=char_buf; self.quiet=quiet

    def run(self, text: str) -> Dict:
        kwargs = dict(
            text_or_documents=text,
            prompt_description=_content_prompt(),
            examples=_examples(),
            model_id=self.model,
            api_key=os.environ.get("OPENAI_API_KEY") if self.model.startswith("gpt-") else os.environ.get("LANGEXTRACT_API_KEY"),
            extraction_passes=self.passes,
            max_workers=self.workers,
            max_char_buffer=self.char_buf,
            fence_output=True if self.model.startswith("gpt-") else False,
            use_schema_constraints=False if self.model.startswith("gpt-") else True,
        )
        if self.quiet:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                res = lx.extract(**kwargs)
        else:
            res = lx.extract(**kwargs)

        items = []
        for e in _coerce_extractions(res):
            get = lambda k, d=None: getattr(e, k, None) if hasattr(e, k) else e.get(k, d) if isinstance(e, dict) else d
            if get("extraction_class") != "question_content":
                continue
            attrs = get("attributes", {}) or {}
            qid = attrs.get("id")
            if not qid: continue
            items.append({
                "id": qid,
                "text": (get("extraction_text") or attrs.get("text") or "").strip(),
                "response_type": attrs.get("response_type"),
                "response_options": attrs.get("response_options")
            })

        # Deduplicate by first occurrence
        seen=set(); out=[]
        for it in items:
            if it["id"] in seen: continue
            seen.add(it["id"]); out.append(it)

        return {"survey_content": {"nodes": out}}

