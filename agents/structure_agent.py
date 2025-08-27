# agents/structure_agent.py
from __future__ import annotations
import os, contextlib, io
from typing import Dict, List, Tuple
import langextract as lx

CANON_TERMINAL = "END_COMPLETE"
TERMINAL_ALIASES = {"END", "SUBMIT", "FINISH", "END_SURVEY", "COMPLETE", "ENDCOMPLETE"}

def _structure_prompt() -> str:
    return """
<task>
Extract ONLY the SURVEY STRUCTURE (topology, skips) from the given text.
Use extractions: "structure_node", "structure_edge", "structure_predicate".
Default flow is sequential; also add explicit skips ("If No, skip to Q8").
</task>
<output_shape>
nodes: {id, kind(question|junction|terminal), block(lower_snake_case|null), response_type(enum|set|text|number|boolean|null), universe|null, universe_ast|null}
edges: {source, target, predicate}
predicates: {id -> {expr, ast, depends_on[]}}
</output_shape>
<rules>
- IDs unique and stable. For batteries, use CHILD suffixes (_1..N); do not emit parent if children exist.
- Include P_TRUE predicate: ast=["TRUE"].
- Minimize exploration; rely only on provided text.
</rules>
""".strip()

def _examples():
    return [
        lx.data.ExampleData(
            text="Q1. Do you currently have health insurance? (Yes/No)",
            extractions=[
                lx.data.Extraction(
                    extraction_class="structure_node",
                    extraction_text="Q1. Do you currently have health insurance?",
                    attributes={"id": "Q1", "kind": "question", "block": "health", "response_type": "enum"}
                ),
                lx.data.Extraction(
                    extraction_class="structure_predicate",
                    extraction_text="Always true",
                    attributes={"id": "P_TRUE", "expr": "Always true", "ast": ["TRUE"], "depends_on": []}
                )
            ]
        ),
        lx.data.ExampleData(
            text="Q5. If No, skip to Q8.",
            extractions=[
                lx.data.Extraction(
                    extraction_class="structure_edge",
                    extraction_text="If Q5==No then goto Q8",
                    attributes={"source": "Q5", "target": "Q8", "predicate": "P_Q5_EQ_2"}
                ),
                lx.data.Extraction(
                    extraction_class="structure_predicate",
                    extraction_text="Q5==No",
                    attributes={"id": "P_Q5_EQ_2", "expr": "Q5 == No", "ast": ["==","Q5",2], "depends_on": ["Q5"]}
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

def _canonicalize_terminals(nodes: List[dict], edges: List[dict]) -> Tuple[List[dict], List[dict]]:
    """
    Coalesce any terminal alias (END, SUBMIT, ...) into a single canonical 'END_COMPLETE'.
    Rewire edges to the canonical id and drop duplicate terminal nodes.
    """
    alias_ids = set()
    has_canon = False
    for n in nodes:
        if n.get("kind") == "terminal":
            nid = (n.get("id") or "").strip()
            if nid == CANON_TERMINAL:
                has_canon = True
            elif nid in TERMINAL_ALIASES:
                alias_ids.add(nid)

    # Ensure canonical exists if any terminal exists
    if not has_canon and (alias_ids or any(n.get("kind") == "terminal" for n in nodes)):
        nodes.append({"id": CANON_TERMINAL, "kind": "terminal", "block": None,
                      "response_type": None, "universe": None, "universe_ast": None})
        has_canon = True

    # Rewire edges
    if has_canon and alias_ids:
        for e in edges:
            if e.get("source") in alias_ids:
                e["source"] = CANON_TERMINAL
            if e.get("target") in alias_ids:
                e["target"] = CANON_TERMINAL

    # Drop alias nodes
    if alias_ids:
        nodes = [n for n in nodes if not (n.get("kind") == "terminal" and (n.get("id") in alias_ids))]

    return nodes, edges

def _dedupe_nodes(nodes: List[dict]) -> List[dict]:
    """
    Deduplicate by node id (keep first). This absorbs rare multi-worker / multi-pass
    duplicates without bailing out the whole run.
    """
    seen = set()
    out = []
    for n in nodes:
        nid = n.get("id")
        if not nid:
            continue
        if nid in seen:
            # skip duplicate
            continue
        seen.add(nid)
        out.append(n)
    return out

class StructureAgent:
    def __init__(self, model: str, passes=3, workers=8, char_buf=1200, quiet=True):
        self.model = model; self.passes=passes; self.workers=workers; self.char_buf=char_buf; self.quiet=quiet

    def run(self, text: str) -> Dict:
        kwargs = dict(
            text_or_documents=text,
            prompt_description=_structure_prompt(),
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

        nodes, edges, preds = [], [], {}
        for e in _coerce_extractions(res):
            get = lambda k, d=None: getattr(e, k, None) if hasattr(e, k) else e.get(k, d) if isinstance(e, dict) else d
            cls = get("extraction_class"); attrs = get("attributes", {}) or {}
            if cls == "structure_node":
                nodes.append({
                    "id": attrs.get("id"),
                    "kind": attrs.get("kind") or "question",
                    "block": attrs.get("block"),
                    "response_type": attrs.get("response_type"),
                    "universe": attrs.get("universe"),
                    "universe_ast": attrs.get("universe_ast")
                })
            elif cls == "structure_edge":
                edges.append({"source": attrs.get("source"), "target": attrs.get("target"), "predicate": attrs.get("predicate") or "P_TRUE"})
            elif cls == "structure_predicate":
                pid = attrs.get("id")
                if pid:
                    preds[pid] = {"expr": attrs.get("expr") or "", "ast": attrs.get("ast") or ["TRUE"], "depends_on": attrs.get("depends_on") or []}

        preds.setdefault("P_TRUE", {"expr": "Always true", "ast": ["TRUE"], "depends_on": []})

        # Canonicalize terminals and dedupe ids
        nodes, edges = _canonicalize_terminals(nodes, edges)
        nodes = _dedupe_nodes(nodes)

        return {
            "survey_dag_structure": {
                "id": "htops_2025_02",
                "version": "2025-02",
                "start": (nodes[0]["id"] if nodes else "Q1"),
                "terminals": [CANON_TERMINAL],
                "nodes": nodes,
                "edges": edges,
                "predicates": preds
            }
        }
