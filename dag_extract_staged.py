# dag_extract_staged.py
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from jsonschema import Draft7Validator, validate as jsonschema_validate

from config import CONFIG, set_runtime_overrides, validate_env
from io_utils.pdf_utils import read_pdf_all_text_with_spans
from chunking.page_windows import chunk_text_by_pages
from chunking.smart_slicing import (
    create_question_slices,
    validate_extraction_quality,
    early_quality_gate,
)
from agents.question_index_agent import QuestionIndexAgent
from agents.content_one_agent import ContentOneAgent
from agents.skip_agent import SkipAgent
from validators.repairs import repair_structure_with_content
from reducers.chunk_reduce import reduce_structure_chunks
from validators.qc_core import qc_core_report, qc_core_markdown
from merge.merge_core import merge_to_core

def validate_final_dag(doc: dict, schema_path: Path):
    schema = json.loads(schema_path.read_text())
    Draft7Validator.check_schema(schema)
    jsonschema_validate(instance=doc, schema=schema)

def tighten_slice(slice_text: str, qid: str, short_text: str | None,
                  before_chars: int, after_chars: int) -> str:
    """
    Center the slice around a reliable anchor to reduce tokens per call.
    Anchor priority: short_text[:50] -> qid -> leave as-is.
    """
    if not slice_text:
        return slice_text
    anchor = -1
    if short_text:
        anchor = slice_text.find(short_text[:50])
    if anchor < 0 and qid:
        anchor = slice_text.find(qid)
    if anchor < 0:
        # If no anchor, clamp to max size (front of slice)
        maxlen = before_chars + after_chars
        return slice_text[:maxlen] if len(slice_text) > maxlen else slice_text
    start = max(0, anchor - before_chars)
    end = min(len(slice_text), anchor + after_chars)
    return slice_text[start:end]

def main():
    ap = argparse.ArgumentParser(description="Staged, parallel, cost-efficient extraction")
    ap.add_argument("--survey", required=True)
    ap.add_argument("--output-dir", default="output")
    ap.add_argument("--chunk-size", type=int, default=10)
    ap.add_argument("--overlap", type=int, default=2)
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--passes", type=int, default=1)
    ap.add_argument("--force", action="store_true", help="recompute even if per-question files exist")
    ap.add_argument("--dag-schema", default=None)

    # Speed knobs
    ap.add_argument("--content-workers", type=int, default=8, help="parallel workers for content extraction")
    ap.add_argument("--skips-workers", type=int, default=1, help="parallel workers for skip extraction (windows)")
    ap.add_argument("--slice-before", type=int, default=900, help="chars to keep before anchor in a question slice")
    ap.add_argument("--slice-after", type=int, default=2200, help="chars to keep after anchor in a question slice")
    ap.add_argument("--progress-every", type=int, default=10, help="print progress every N completions for content")

    args = ap.parse_args()

    set_runtime_overrides(model=args.model, survey_path=args.survey, schema_path=args.dag_schema)
    validate_env(raise_on_error=True)

    outdir = Path(args.output_dir); outdir.mkdir(parents=True, exist_ok=True)
    qdir = outdir / "questions"; qdir.mkdir(parents=True, exist_ok=True)
    chunks_dir = outdir / "chunks"; chunks_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_log_path = outdir / f"run_{args.model}_{ts}.log"

    def log(msg: str) -> None:
        print(msg, flush=True)
        try:
            with open(run_log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

    log("────────────────────────────────────────────────────────")
    log(f"Survey DAG staged extraction")
    log(f"  survey:      {args.survey}")
    log(f"  model:       {args.model} (passes={args.passes})")
    log(f"  chunk/over:  {args.chunk_size}/{args.overlap}")
    log(f"  output dir:  {outdir}")
    log(f"  log file:    {run_log_path.name}")
    log(f"  workers:     content={args.content_workers}, skips={args.skips_workers}")
    log(f"  slice window: -{args.slice_before}/+{args.slice_after} chars")
    log("────────────────────────────────────────────────────────")

    # ---- Load PDF text ----
    log("Reading PDF text…")
    full_text, page_spans = read_pdf_all_text_with_spans(Path(args.survey))
    windows = chunk_text_by_pages(full_text, page_spans, chunk_size=args.chunk_size, overlap=args.overlap)
    log(f"Pages detected: {len(page_spans)}  |  Windows: {len(windows)}")

    # ---- Stage 1: Index (cheap, few windows; keep sequential) ----
    log("\n[Stage 1/5] Indexing questions (IDs, order, coarse pages)…")
    idx_agent = QuestionIndexAgent(model=args.model, passes=args.passes, quiet=True)
    index_items = []
    for i, w in enumerate(windows, 1):
        label = f"Chunk {i}/{len(windows)} p{w['start_page']}-{w['end_page']}"
        log(f"  [Index] {label} …")
        t0 = time.perf_counter()
        doc = idx_agent.run_window(w["text"], page_start=w["start_page"])
        dt = time.perf_counter() - t0
        log(f"    ↳ done in {dt:.1f}s")
        path = chunks_dir / f"index_chunk{w['idx']:03d}_p{w['start_page']}-{w['end_page']}.json"
        path.write_text(json.dumps(doc, indent=2))
        index_items.extend(doc.get("question_index", []))

    # dedupe by first seen, stable by earliest page_guess then ID
    seen = set(); ordered = []
    for item in sorted(index_items, key=lambda x: (x["page_guess"], x["id"])):
        if item["id"] in seen:
            continue
        seen.add(item["id"]); ordered.append(item)

    idx_out = outdir / f"question_index_{args.model}_{ts}.json"
    idx_out.write_text(json.dumps({"question_index": ordered}, indent=2))
    log(f"Indexed questions: {len(ordered)}  →  {idx_out.name}")
    if not ordered:
        log("No questions indexed. Exiting.")
        return

    # ---- Stage 2: Content per question (parallel, cached per file) ----
    log("\n[Stage 2/5] Extracting question content in parallel…")
    one_agent = ContentOneAgent(model=args.model, passes=args.passes, quiet=True)

    # Smart slices once using page + text hints
    log("  Building smart slices for all questions…")
    question_slices = create_question_slices(full_text, page_spans, ordered)
    log(f"  Slices ready: {len(question_slices)}")

    total_q = len(ordered)
    results_map: dict[str, dict] = {}
    submitted = 0
    completed = 0

    def submit_needed(q):
        qid = q["id"]; qpath = qdir / f"{qid}.json"
        return args.force or not qpath.exists()

    def worker(q):
        qid = q["id"]
        qpath = qdir / f"{qid}.json"
        short_text = q.get("short_text", "")
        if not (args.force or not qpath.exists()):
            # cached
            node = json.loads(qpath.read_text())
            return qid, node, True, 0.0

        slice_text = question_slices.get(qid, "")
        # Skip trivial slices to save tokens
        if not slice_text or len(slice_text.strip()) < 40:
            node = {"id": qid, "text": short_text, "response_type":"text", "response_options": None}
            qpath.write_text(json.dumps(node, indent=2))
            return qid, node, False, 0.0

        # tighten slice to reduce prompt size
        slice_text_tight = tighten_slice(slice_text, qid, short_text, args.slice_before, args.slice_after)

        t0 = time.perf_counter()
        node = one_agent.run_slice(slice_text_tight, qid)
        dt = time.perf_counter() - t0

        if not node:
            node = {"id": qid, "text": short_text, "response_type":"text", "response_options": None}

        qpath.write_text(json.dumps(node, indent=2))
        return qid, node, False, dt

    # Submit in parallel
    with ThreadPoolExecutor(max_workers=max(1, args.content_workers)) as ex:
        futures = {ex.submit(worker, q): q for q in ordered if submit_needed(q)}
        submitted = len(futures)
        log(f"  Submitted {submitted} new extractions; {total_q - submitted} cached")

        for f in as_completed(futures):
            qid, node, cached, dt = f.result()
            results_map[qid] = node
            completed += 1
            # Minimal progress
            if (completed % max(1, args.progress_every)) == 0 or completed == submitted:
                rt = node.get("response_type") or "?"
                opts = node.get("response_options") or []
                optn = len(opts) if isinstance(opts, list) else 0
                tag = "cached" if cached else f"{dt:.1f}s"
                log(f"    [Content {completed}/{submitted}] {qid}: {rt}, {optn} opts ({tag})")

    # Collect content_nodes in original order (mixing cached and new)
    content_nodes = []
    for q in ordered:
        qid = q["id"]
        qpath = qdir / f"{qid}.json"
        if qid in results_map:
            content_nodes.append(results_map[qid])
        else:
            # cached path
            node = json.loads(qpath.read_text())
            content_nodes.append(node)

    content_doc = {"survey_content": {"nodes": content_nodes}}
    content_out = outdir / f"content_{args.model}_{ts}.json"
    content_out.write_text(json.dumps(content_doc, indent=2))
    log(f"Content snapshot → {content_out.name}")

    # ---- Stage 3: Quality gate ----
    log("\n[Stage 3/5] Quality gate on content coverage…")
    metrics = validate_extraction_quality(ordered, content_nodes, [])
    (outdir / f"quality_{args.model}_{ts}.json").write_text(json.dumps(metrics, indent=2))
    log(f"  Coverage: content={metrics['content_coverage']:.1%}  "
        f"index={metrics['index_count']}  content_nodes={metrics['content_count']}")
    if metrics["warnings"]:
        log("  Warnings:")
        for w in metrics["warnings"][:5]:
            log(f"    - {w}")
        if len(metrics["warnings"]) > 5:
            log(f"    … {len(metrics['warnings'])-5} more")
    if not early_quality_gate(metrics):
        log("Extraction quality too low → aborting before structure.")
        return
    log("  Quality gate passed.")

    # ---- Stage 4: Skips (windows) — optionally parallel ----
    log("\n[Stage 4/5] Extracting explicit skips/branching…")
    skip_agent = SkipAgent(model=args.model, passes=args.passes, quiet=True)

    def skip_worker(w):
        sdoc = skip_agent.run_window(w["text"])
        return {
            "survey_dag_structure": {
                "id": "survey", "version": "v0",
                "start": ordered[0]["id"] if ordered else "Q1",
                "terminals": ["END_COMPLETE"],
                "nodes": [{"id": q["id"], "kind": "question", "block": None, "response_type": None,
                           "universe": None, "universe_ast": None} for q in ordered],
                "edges": sdoc["edges"],
                "predicates": sdoc["predicates"],
            }
        }

    struct_chunks = []
    if max(1, args.skips_workers) == 1:
        for i, w in enumerate(windows, 1):
            label = f"Chunk {i}/{len(windows)} p{w['start_page']}-{w['end_page']}"
            log(f"  [Skips] {label} …")
            t0 = time.perf_counter()
            sdoc = skip_worker(w)
            dt = time.perf_counter() - t0
            log(f"    ↳ done in {dt:.1f}s")
            struct_chunks.append(sdoc)
            (chunks_dir / f"skips_chunk{w['idx']:03d}_p{w['start_page']}-{w['end_page']}.json").write_text(json.dumps(sdoc, indent=2))
    else:
        with ThreadPoolExecutor(max_workers=args.skips_workers) as ex:
            futs = {ex.submit(skip_worker, w): w for w in windows}
            done = 0
            for f in as_completed(futs):
                sdoc = f.result()
                w = futs[f]
                struct_chunks.append(sdoc)
                (chunks_dir / f"skips_chunk{w['idx']:03d}_p{w['start_page']}-{w['end_page']}.json").write_text(json.dumps(sdoc, indent=2))
                done += 1
                log(f"  [Skips] {done}/{len(windows)} windows complete")

    structure_raw = reduce_structure_chunks(struct_chunks)
    s = structure_raw.get("survey_dag_structure", {})
    log(f"  Skips reduced → nodes={len(s.get('nodes', []))}, edges={len(s.get('edges', []))}, preds={len((s.get('predicates') or {}))}")

    # ---- Stage 5: Merge → Validate → QC ----
    log("\n[Stage 5/5] Repairing structure, merging with content, validating, and QC…")
    structure_fixed, repair_report = repair_structure_with_content(structure_raw, content_doc)
    (outdir / f"structure_repair_{args.model}_{ts}.json").write_text(json.dumps({"repair": repair_report}, indent=2))
    struct_out = outdir / f"structure_{args.model}_{ts}.json"
    struct_out.write_text(json.dumps(structure_fixed, indent=2))
    log(f"  Structure (fixed) → {struct_out.name}")

    dag = merge_to_core(structure_fixed, content_doc, full_text=full_text, page_spans=page_spans)
    dag_schema_path = Path(args.dag_schema) if args.dag_schema else CONFIG.schema_path
    core_path = outdir / f"dag_core_{args.model}_{ts}.json"
    try:
        validate_final_dag(dag, dag_schema_path)
        core_path.write_text(json.dumps(dag, indent=2))
        log(f"  Final DAG  → {core_path.name}")
    except Exception as e:
        invalid = core_path.with_suffix(".invalid.json")
        invalid.write_text(json.dumps({"dag": dag, "validation_error": str(e)}, indent=2))
        log(f"  Final DAG validation failed; wrote {invalid.name}")

    rep = qc_core_report(dag)
    qcj = outdir / f"dag_core_{args.model}_{ts}.qc.json"
    qcmd = outdir / f"dag_core_{args.model}_{ts}.qc.md"
    qcj.write_text(json.dumps(rep, indent=2))
    qcmd.write_text(qc_core_markdown(rep))
    log(f"  QC → {qcj.name}, {qcmd.name}")
    log("\nDONE ✅")

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    main()
