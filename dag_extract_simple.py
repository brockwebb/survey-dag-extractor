#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, re, sys, time, os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Load .env so OPENAI_API_KEY is available to langextract's OpenAI provider
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import langextract as lx
from jsonschema import validate as _validate, Draft7Validator

# ----------------------------- utils: PDF and text -----------------------------

def read_pdf_all_text_with_spans_fallback(pdf_path: Path) -> tuple[str, List[Tuple[int,int,int]]]:
    """
    Return (full_text, page_spans[(start,end,page_no)]).
    Tries your project's io_utils.pdf_utils. Falls back to PyPDF2.
    """
    try:
        from io_utils.pdf_utils import read_pdf_all_text_with_spans  # your existing util if present
        return read_pdf_all_text_with_spans(pdf_path)
    except Exception:
        try:
            import PyPDF2
        except Exception as e:
            raise RuntimeError(
                "Need either io_utils.pdf_utils or PyPDF2. Install with: pip install PyPDF2"
            ) from e
        text = ""
        spans = []
        pos = 0
        with open(pdf_path, "rb") as f:
            r = PyPDF2.PdfReader(f)
            for i, p in enumerate(r.pages, start=1):
                t = p.extract_text() or ""
                s = len(t)
                spans.append((pos, pos + s, i))
                text += t
                pos += s
        return text, spans

def normalize_for_index(s: str) -> str:
    # de-hyphenate line wraps: "transpor-\n tation" -> "transportation"
    s = re.sub(r'(\w)-\n(\w)', r'\1\2', s)
    # collapse lone newlines
    s = re.sub(r'[ \t]*\n[ \t]*', ' ', s)
    s = re.sub(r' {2,}', ' ', s)
    return s.strip()

def page_of_char(char_index: int, page_spans: List[Tuple[int,int,int]]) -> int:
    # page_spans is [(start,end,page_no)]
    # binary search would be nicer; linear is fine for ~36 pages
    for start, end, p in page_spans:
        if start <= char_index < end:
            return p
    return page_spans[-1][2] if page_spans else 1

# ----------------------------- Stage 0: deterministic index -----------------------------

# Explicit ID tokens we care about (customize as needed)
ID_TOKEN = re.compile(
    r"""
    \b(
        (?:Q|FD|HSE|NDX|HH|QS|SC|D|R|M|P)          # common stems
        \d+(?:_[0-9A-Za-z]+)*                      # suffixes like _1, _OTHER, _rev
        |
        (?:END|INTRO|CONSENT|LANG(?:UAGE)?)        # special tokens occasionally present
        (?:_[0-9A-Za-z]+)*
    )\b[.:)]?                                      # trailing punct often present
    """,
    re.VERBOSE,
)

def stage0_index_local(full_text: str, page_spans: List[Tuple[int,int,int]]) -> List[Dict[str,Any]]:
    """
    Deterministically builds a seed index of questions by scanning for explicit IDs.
    Returns: [{"id","short_text","page_guess"}, ...] in first-occurrence order (unique by id).
    """
    seeds: List[Dict[str,Any]] = []
    seen: set[str] = set()

    # iterate in document order
    for m in ID_TOKEN.finditer(full_text):
        qid = m.group(1)
        if qid in seen:
            continue  # keep only first occurrence
        seen.add(qid)

        # short_text: take the next 80–120 chars after the ID token, cleaned
        tail = full_text[m.end(): m.end() + 240]
        # trim leading punctuation/space
        tail = tail.lstrip(" .:)-–—\n\t")
        # stop at first hard stop if it occurs early
        stop = min([x for x in [tail.find("."), tail.find("?"), tail.find(":")] if x != -1] + [120])
        short = tail[:max(80, min(stop, 120))].strip()
        short = re.sub(r'\s+', ' ', short)

        # page guess from char position
        pg = page_of_char(m.start(), page_spans)

        seeds.append({"id": qid, "short_text": short, "page_guess": int(pg)})

    return seeds

# ----------------------------- Stage 1: content (LLM via LangExtract) -----------------------------

PROMPT_CONTENT_ONE = """
You are extracting ONE survey question in the provided slice.
The question ID will be provided separately.

Return JSON object:
{
  "id": "<ID>",
  "text": "<full question text>",
  "response_type": "enum|set|text|number",
  "response_options": [ ... ]  // flat list of codes or labels when enum/set; else null
}

Rules:
- Use the provided ID exactly (case and underscores).
- text: full prompt stem (exclude IDs, routing lines, page footers).
- response_type: 
  - 'set' for multi-select check-all-that-apply
  - 'enum' for single-choice
  - 'text' for free-text / other-specify
  - 'number' for numeric entry
- response_options: 
  - For enum/set, return a flat list of codes or labels. Prefer numeric codes (1..N) if visible; else labels. 
  - For text/number: return null.
- If options are split across lines/bullets, merge into one list in display order.
- Do not invent options; only include what you see in the slice.
Output only the JSON object (no prose).
"""

def _examples_content() -> List["lx.data.ExampleData"]:
    # Use keyword args to match recent langextract versions
    return [
        lx.data.ExampleData(
            text="Q7 Is this number a cell phone or a land line?\n1 Cell phone\n2 Land line",
            extractions=[
                lx.data.Extraction(
                    extraction_class="question_content_one",
                    extraction_text="Q7 Is this number ...",
                    attributes={
                        "id":"Q7","text":"Is this number a cell phone or a land line?",
                        "response_type":"enum","response_options":[1,2]
                    }
                )
            ],
        ),
        lx.data.ExampleData(
            text="NDX2. Type of natural disaster (select all that apply)\n1 Flood\n8 Other (specify)",
            extractions=[
                lx.data.Extraction(
                    extraction_class="question_content_one",
                    extraction_text="NDX2 ...",
                    attributes={
                        "id":"NDX2","text":"Type of natural disaster (select all that apply)",
                        "response_type":"set","response_options":[1,8]
                    }
                )
            ],
        ),
        lx.data.ExampleData(
            text="NDX2_OTHER. Other, specify: ________",
            extractions=[
                lx.data.Extraction(
                    extraction_class="question_content_one",
                    extraction_text="NDX2_OTHER ...",
                    attributes={
                        "id":"NDX2_OTHER","text":"Other, specify",
                        "response_type":"text","response_options":None
                    }
                )
            ],
        ),
    ]

def extract_content_for_slice(slice_text: str, qid: str, model: str) -> Dict[str,Any]:
    result = lx.extract(
        text_or_documents=slice_text,
        prompt_description=PROMPT_CONTENT_ONE,
        examples=_examples_content(),
        model_id=model,
    )
    if not getattr(result, "extractions", None):
        return {"id": qid, "text": "", "response_type": "text", "response_options": None}
    attrs = result.extractions[0].attributes or {}
    # enforce ID & minimal defaults
    attrs["id"] = qid
    if not attrs.get("response_type"):
        attrs["response_type"] = "text"
        attrs["response_options"] = None
    return attrs

# ----------------------------- slicing around anchors -----------------------------

def find_anchor_pos(full_text: str, qid: str, short_text: str) -> int:
    # prefer short_text (more specific), fallback to qid
    s = (short_text or "").strip()
    if s:
        i = full_text.lower().find(s[:100].lower())
        if i >= 0:
            return i
    i = full_text.find(qid)
    return i

def slice_for_q(full_text: str, pos: int, before: int=600, after: int=1600) -> str:
    if pos < 0:
        # fallback: first window
        return full_text[:min(len(full_text), before+after)]
    start = max(0, pos - before)
    end = min(len(full_text), pos + after)
    return full_text[start:end]

# ----------------------------- DAG assembly & validation -----------------------------

ID_SAFE = re.compile(r"[^A-Za-z0-9_]+")

def canon_id(qid: str) -> str:
    return ID_SAFE.sub("", qid or "").strip() or "NODE"

def build_minimal_dag(survey_id: str, nodes: List[Dict[str,Any]]) -> Dict[str,Any]:
    # canonicalize IDs and ensure unique
    seen = {}
    for n in nodes:
        old = n["id"]
        new = canon_id(old)
        if new in seen:
            seen[new] += 1
            new = f"{new}_{seen[new]}"
        else:
            seen[new] = 1
        n["id"] = new

    # sequential fallback edges + terminal
    edges = []
    for i in range(len(nodes)-1):
        edges.append({"source": nodes[i]["id"], "target": nodes[i+1]["id"], "predicate": "P_TRUE"})
    terminal_id = "END_COMPLETE"
    preds = {"P_TRUE": {"expr":"Always true","ast":["TRUE"],"depends_on":[]}}

    dag = {
        "survey_dag": {
            "id": survey_id,
            "version": "v0",
            "start": nodes[0]["id"] if nodes else None,
            "terminals": [terminal_id],
            "metadata": {
                "build": {"method": "llm_extraction", "model": "minimal_pipeline"},
            },
            "graph": {
                "nodes": nodes + [{
                    "id": terminal_id, "kind": "terminal", "block": None,
                    "text": "End of survey", "response_type": None,
                    "universe": None, "universe_ast": None,
                }],
                "edges": edges,
                "predicates": preds,
            }
        }
    }
    return dag

def validate_against_schema(doc: dict, schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft7Validator.check_schema(schema)
    _validate(instance=doc, schema=schema)

# ----------------------------------- main -----------------------------------

def main():
    ap = argparse.ArgumentParser(description="Minimal, deterministic survey DAG extraction (deterministic Stage 0)")
    ap.add_argument("--survey", required=True)
    ap.add_argument("--model", default="gpt-5-mini", help="Model for per-question content")
    ap.add_argument("--schema", default="data/survey_dag_schema.json")
    ap.add_argument("--before", type=int, default=600, help="slice chars before anchor")
    ap.add_argument("--after", type=int, default=1600, help="slice chars after anchor")
    args = ap.parse_args()

    pdf_path = Path(args.survey)
    outdir = Path("output"); outdir.mkdir(exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    stem = f"reset_{args.model}_{ts}"

    print("Reading PDF…", flush=True)
    full_text_raw, page_spans = read_pdf_all_text_with_spans_fallback(pdf_path)
    full_text = normalize_for_index(full_text_raw)
    print(f"Pages detected: {len(page_spans)}", flush=True)

    # Stage 0 — deterministic seeds (no LLM)
    print("[Stage 0] Deterministic index (explicit IDs only)…", flush=True)
    t0 = time.perf_counter()
    seeds = stage0_index_local(full_text, page_spans)
    print(f"  seeds: {len(seeds)}  ({time.perf_counter()-t0:.1f}s)", flush=True)
    outdir.joinpath(f"{stem}.stage0_seeds.json").write_text(json.dumps({"question_index": seeds}, indent=2))

    if not seeds:
        print("No questions found. Exiting.", file=sys.stderr)
        return

    # Stage 1 — content per question (LLM)
    nodes: List[Dict[str,Any]] = []
    print("[Stage 1] Extracting content per question…", flush=True)
    for i, s in enumerate(seeds, 1):
        qid = s["id"]; short = s.get("short_text","")
        pos = find_anchor_pos(full_text, qid, short)
        sl = slice_for_q(full_text, pos, before=args.before, after=args.after)
        node = extract_content_for_slice(sl, qid=qid, model=args.model)
        # Fill required DAG fields
        node.setdefault("kind", "question")
        node.setdefault("block", None)
        node.setdefault("universe", None)
        node.setdefault("universe_ast", None)
        nodes.append(node)
        if i % 10 == 0 or i == len(seeds):
            print(f"  [{i}/{len(seeds)}] {qid}  rt={node.get('response_type')}  opts={len(node.get('response_options') or [])}", flush=True)

    # Assemble & validate
    print("[Stage 2] Building minimal DAG…", flush=True)
    dag = build_minimal_dag(survey_id=pdf_path.stem, nodes=nodes)

    schema_path = Path(args.schema)
    try:
        validate_against_schema(dag, schema_path)
        out = outdir / f"{stem}.dag.json"
        out.write_text(json.dumps(dag, indent=2))
        print(f"OK ✓  → {out}", flush=True)
    except Exception as e:
        bad = outdir / f"{stem}.invalid.json"
        bad.write_text(json.dumps({"dag": dag, "validation_error": str(e)}, indent=2))
        print(f"Validation failed → {bad}\n{e}", file=sys.stderr, flush=True)

if __name__ == "__main__":
    # Fast explicit guard in case .env didn’t load
    if not os.getenv("OPENAI_API_KEY"):
        sys.stderr.write("Warning: OPENAI_API_KEY not found in environment. Stage 1 will fail.\n")
    main()
