# agents/question_index_agent.py
from __future__ import annotations
import os
from typing import Dict, List
from contextlib import nullcontext
import langextract as lx
from utils.silence import mute_everything

PROMPT = """
<task>
From the provided text window, extract ONLY question index records.
Each record must copy verbatim the question ID and the first 8–12 words of the stem.
Emit "question_index" extractions with attributes:
{id, short_text, page_guess}.
Rules:
- "id" must be the printed survey id (e.g., NDX4_2).
- "short_text" must be a verbatim substring from the window (no paraphrase).
- "page_guess" = the starting page number of this window (given).
- Do NOT include batteries' parent item when children exist; include children only.
- No content/options. No edges/predicates.
</task>
""".strip()

EXAMPLES = [
    lx.data.ExampleData(
        text="NDX4_2. Number displaced: Children\n1) None\n2) One\n",
        extractions=[
            lx.data.Extraction(
                extraction_class="question_index",
                extraction_text="NDX4_2. Number displaced: Children",
                attributes={"id":"NDX4_2","short_text":"NDX4_2. Number displaced: Children","page_guess":10}
            )
        ]
    ),
]

class QuestionIndexAgent:
    def __init__(self, model: str = "gpt-5-mini", passes: int = 1, quiet: bool = True):
        self.model = model
        self.passes = passes
        self.quiet = quiet

    def run_window(self, text: str, page_start: int) -> Dict:
        kwargs = dict(
            text_or_documents=text,
            prompt_description=PROMPT + f"\n<context>page_start={page_start}</context>",
            examples=EXAMPLES,
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

        out: List[dict] = []
        exts = getattr(res, "extractions", None) or (res.get("extractions", []) if isinstance(res, dict) else [])
        for e in exts:
            cls = getattr(e, "extraction_class", None) or e.get("extraction_class")
            if cls != "question_index":
                continue
            attrs = getattr(e, "attributes", None) or e.get("attributes", {}) or {}
            qid = attrs.get("id"); st = attrs.get("short_text")
            if not qid or not st:
                continue
            out.append({"id": qid, "short_text": st, "page_guess": page_start})
        return {"question_index": out}
