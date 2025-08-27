# agents/content_one_agent.py
from __future__ import annotations
import os
from typing import Dict, Optional
from contextlib import nullcontext
import langextract as lx
from utils.silence import mute_everything

PROMPT = """
<task>
Extract the FULL CONTENT for exactly ONE question with id={target_id}.
Emit ONE extraction with extraction_class="question_content" and attributes:
{id, text, response_type, response_options?}
Rules:
- Copy "id" and the stem "text" verbatim from the window (shortest unique span OK).
- response_type ∈ {enum, set, text, number, boolean}
- For Yes/No: enum with [{"code":1,"text":"Yes"},{"code":2,"text":"No"}].
- For enum/set: codes must be contiguous 1..N; copy option labels verbatim.
- Emit nothing if {target_id} is not present in this window.
</task>
""".strip()

EXAMPLE = lx.data.ExampleData(
    text="NDX4_2. Number displaced: Children\n0) None\n1) One\n2) Two or more",
    extractions=[lx.data.Extraction(
        extraction_class="question_content",
        extraction_text="NDX4_2. Number displaced: Children",
        attributes={
            "id":"NDX4_2",
            "text":"NDX4_2. Number displaced: Children",
            "response_type":"enum",
            "response_options":[
                {"code":1,"text":"None"},
                {"code":2,"text":"One"},
                {"code":3,"text":"Two or more"}
            ],
        }
    )]
)

class ContentOneAgent:
    def __init__(self, model: str = "gpt-5-mini", passes: int = 1, quiet: bool = True):
        self.model = model; self.passes = passes; self.quiet = quiet

    def run_slice(self, text: str, target_id: str) -> Optional[Dict]:
        kwargs = dict(
            text_or_documents=text,
            prompt_description=PROMPT.replace("{target_id}", target_id),
            examples=[EXAMPLE],
            model_id=self.model,
            api_key=os.environ.get("OPENAI_API_KEY"),
            extraction_passes=self.passes,
            max_workers=1,
            max_char_buffer=900,
            fence_output=True,
            use_schema_constraints=False,
        )
        with mute_everything() if self.quiet else nullcontext():
            res = lx.extract(**kwargs)

        exts = getattr(res, "extractions", None) or (res.get("extractions", []) if isinstance(res, dict) else [])
        for e in exts:
            cls = getattr(e, "extraction_class", None) or e.get("extraction_class")
            if cls != "question_content":
                continue
            attrs = getattr(e, "attributes", None) or e.get("attributes", {}) or {}
            qid = attrs.get("id")
            if qid and qid.strip() == target_id:
                return {
                    "id": qid,
                    "text": attrs.get("text") or "",
                    "response_type": attrs.get("response_type") or "text",
                    "response_options": attrs.get("response_options"),
                }
        return None
