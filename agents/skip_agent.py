# agents/skip_agent.py
from __future__ import annotations
import os
from typing import Dict, List
from contextlib import nullcontext
import langextract as lx
from utils.silence import mute_everything

PROMPT = """
<task>
From the provided text window, extract ONLY explicit skip/branch logic printed in the survey (e.g., "If No, skip to Q8").
Emit extractions:
- extraction_class="structure_edge" with attributes {source, target, predicate}
- extraction_class="structure_predicate" with attributes {id, expr, ast, depends_on[]}
Rules:
- Copy any printed cue verbatim into extraction_text, otherwise leave extraction_text="".
- Use P_TRUE for unconditional sequential flows ONLY if that flow is explicitly printed.
- Predicates must use the survey ids and primitive AST: ["==","Q5",2], ["INCLUDES","Q12",8], ["NOT", ...].
- Do not invent edges; only what is printed in the window.
</task>
""".strip()

EXAMPLES = [
    lx.data.ExampleData(
        text="Q12. If No, skip to Q15.",
        extractions=[
            lx.data.Extraction(
                extraction_class="structure_edge",
                extraction_text="If No, skip to Q15.",
                attributes={"source":"Q12","target":"Q15","predicate":"P_Q12_EQ_2"}
            ),
            lx.data.Extraction(
                extraction_class="structure_predicate",
                extraction_text="Q12 == No",
                attributes={"id":"P_Q12_EQ_2","expr":"Q12 == No","ast":["==","Q12",2],"depends_on":["Q12"]}
            )
        ]
    )
]

class SkipAgent:
    def __init__(self, model: str = "gpt-5-mini", passes: int = 1, quiet: bool = True):
        self.model = model; self.passes = passes; self.quiet = quiet

    def run_window(self, text: str) -> Dict:
        kwargs = dict(
            text_or_documents=text,
            prompt_description=PROMPT,
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

        edges: List[dict] = []; preds: dict = {}
        exts = getattr(res, "extractions", None) or (res.get("extractions", []) if isinstance(res, dict) else [])
        for e in exts:
            cls = getattr(e, "extraction_class", None) or e.get("extraction_class")
            attrs = getattr(e, "attributes", None) or e.get("attributes", {}) or {}
            if cls == "structure_edge":
                src, tgt = attrs.get("source"), attrs.get("target")
                if src and tgt:
                    edges.append({"source": src, "target": tgt, "predicate": attrs.get("predicate") or "P_TRUE"})
            elif cls == "structure_predicate":
                pid = attrs.get("id")
                if pid and pid not in preds:
                    preds[pid] = {"expr": attrs.get("expr") or "", "ast": attrs.get("ast") or ["TRUE"], "depends_on": attrs.get("depends_on") or []}
        preds.setdefault("P_TRUE", {"expr":"Always true","ast":["TRUE"],"depends_on":[]})
        return {"edges": edges, "predicates": preds}
