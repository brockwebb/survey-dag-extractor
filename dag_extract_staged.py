# dag_extract_staged.py
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from jsonschema import Draft7Validator, validate as jsonschema_validate

from config import CONFIG, set_runtime_overrides, validate_env
from io_utils.pdf_utils import read_pdf_all_text_with_spans
from chunking.page_windows import chunk_text_by_pages, chunk_text_by_blocks
from chunking.block_detect import detect_blocks, summarize_blocks
from chunking.smart_slicing import (
    create_question_slices,
    validate_extraction_quality,
    early_quality_gate,
)

from agents.question_index_agent import QuestionIndexAgent
from agents.content_one_agent import ContentOneAgent
from agents.skip_agent import SkipAgent

from reducers.chunk_reduce import reduce_structure_chunks
from validators.repairs import repair_structure_with_content
from merge.merge_core import merge_to_core

from validators.qc_core import qc_core_report, qc_core_markdown
from reducers.sequential_fallback import make_sequential_edges, needs_sequential_fallback
from reducers.lossless_merge import merge_content_nodes, normalize_predicates
from validators.no_drop import ensure_nodes_for_all_index

from utils.normalize import coerce_to_schema_nlossy


# ----------------- small utilities (inlined to avoid more modules) -----------------

def _dedupe_index(items: List[Dict]) -> List[Dict]:
    seen = set(); out = []
    for it in sorted(items, key=lambda x: (x.get("page_guess", 10**9), x.get("id",""))):
        _id = it.get("id")
        if not _id or _id in seen:
            continue
        seen.add(_id); out.append(it)
    return out

def validate_final_dag(doc: dict, schema_path: Path):
    schema = json.loads(schema_path.read_text())
    Draft7Validator.check_schema(schema)
    jsonschema_validate(instance=doc, schema=schema)

def tighten_slice(slice_text: str, qid: str, short_text: str | None,
                  before_chars: int, after_chars: int) -> str:
    if not slice_text:
        return slice_text
    anchor = -1
    if short_text:
        anchor = slice_text.find(short_text[:50])
    if anchor < 0 and qid:
        anchor = slice_text.find(qid)
    if anchor < 0:
        maxlen = before_chars + after_chars
        return slice_text[:maxlen] if len(slice_text) > maxlen else slice_text
    start = max(0, anchor - before_chars)
    end = min(len(slice_text), anchor + after_chars)
    return slice_text[start:end]

def _get_core_container(doc: dict) -> dict:
    """Return the top-level core graph container regardless of key name."""
    return (doc.get("survey_dag_core")
            or doc.get("survey_dag")
            or doc.get("survey_dag_structure")
            or {})

def _set_core_container(doc: dict, core: dict) -> None:
    if "survey_dag_core" in doc:
        doc["survey_dag_core"] = core
    elif "survey_dag" in doc:
        doc["survey_dag"] = core
    elif "survey_dag_structure" in doc:
        doc["survey_dag_structure"] = core
    else:
        doc["survey_dag_core"] = core

def fix_terminal_aliases(dag: dict,
                         canonical: str = "END_COMPLETE",
                         aliases: tuple[str, ...] = ("END", "END_SURVEY", "SUBMIT")) -> tuple[dict, dict]:
    """
    Redirect edges that point at terminal aliases to the canonical terminal.
    If canonical terminal is missing, create it. Drops alias-nodes if present.
    Returns (dag, alias_map).
    """
    core = _get_core_container(dag)
    graph = core.get("graph", core)  # support both {core:{graph:{...}}} and flat shapes
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    id_set = {n["id"] for n in nodes if n.get("id")}
    alias_map: dict[str, str] = {}

    # Ensure canonical terminal exists
    if canonical not in id_set:
        nodes.append({"id": canonical, "kind": "terminal", "block": None,
                      "text": "End of survey", "response_type": None, "universe": None, "universe_ast": None})
        id_set.add(canonical)

    # Build alias map for any alias that appears in edges or nodes
    used_aliases = set()
    for e in edges:
        if e.get("target") in aliases:
            used_aliases.add(e["target"])
        if e.get("source") in aliases:
            used_aliases.add(e["source"])
    used_aliases.update(id_set.intersection(aliases))

    for a in used_aliases:
        if a != canonical:
            alias_map[a] = canonical

    if alias_map:
        # Rewrite nodes: drop any alias nodes (since canonical exists)
        nodes = [n for n in nodes if n.get("id") not in alias_map]
        # Rewrite edges
        for e in edges:
            s = e.get("source")
            t = e.get("target")
            if s in alias_map:
                e["source"] = alias_map[s]
            if t in alias_map:
                e["target"] = alias_map[t]

    # Write back (respect both shapes)
    if "graph" in core:
        core["graph"]["nodes"] = nodes
        core["graph"]["edges"] = edges
    else:
        core["nodes"] = nodes
        core["edges"] = edges
    _set_core_container(dag, core)
    return dag, alias_map

def ensure_edge_endpoints_exist(dag: dict) -> tuple[dict, list[str]]:
    """
    Guarantee every edge endpoint exists as a node.
    If missing, create a minimal 'junction' node so schema validation passes.
    Returns (dag, added_stub_ids).
    """
    core = _get_core_container(dag)
    graph = core.get("graph", core)
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    id_set = {n["id"] for n in nodes if n.get("id")}
    added: list[str] = []

    def add_stub(nid: str):
        nodes.append({"id": nid, "kind": "junction", "block": None,
                      "text": None, "response_type": None, "universe": None, "universe_ast": None})
        id_set.add(nid)
        added.append(nid)

    for e in edges:
        s = e.get("source")
        t = e.get("target")
        if s and s not in id_set:
            add_stub(s)
        if t and t not in id_set:
            add_stub(t)

    if "graph" in core:
        core["graph"]["nodes"] = nodes
    else:
        core["nodes"] = nodes
    _set_core_container(dag, core)
    return dag, added


# -------------------------------------- main --------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Staged Survey DAG Extraction (GPT-5x, prompts, Stage-0 seeds)")
    ap.add_argument("--survey", required=True)
    ap.add_argument("--output-dir", default="output")

    # Chunking / structure
    ap.add_argument("--chunk-size", type=int, default=8)
    ap.add_argument("--overlap", type=int, default=1)
    ap.add_argument("--block-aware", action="store_true",
                    help="Detect blocks by ID prefix/patterns and chunk by blocks")
    ap.add_argument("--passes", type=int, default=1)
    ap.add_argument("--force", action="store_true", help="Recompute even if per-question files exist")
    ap.add_argument("--dag-schema", default=None)

    # Models (all-in on 5x defaults)
    ap.add_argument("--model", default="gpt-5-mini", help="Default model for content/skips if not overridden")
    ap.add_argument("--index-model", default="gpt-5-mini", help="Stage 1 (windowed index)")
    ap.add_argument("--content-model", default="gpt-5-mini", help="Stage 2 (content)")
    ap.add_argument("--skips-model", default="gpt-5-mini", help="Stage 4 (skips)")
    ap.add_argument("--s0-model", default="gpt-5", help="Stage 0 (full-doc seeds)")

    # Temperatures (kept at 0.0 by default)
    ap.add_argument("--temp-index", type=float, default=0.0)
    ap.add_argument("--temp-content", type=float, default=0.0)
    ap.add_argument("--temp-skips", type=float, default=0.0)

    # Workers
    ap.add_argument("--index-workers", type=int, default=3)
    ap.add_argument("--content-workers", type=int, default=8)
    ap.add_argument("--skips-workers", type=int, default=2)

    # Slice window for content extraction
    ap.add_argument("--slice-before", type=int, default=500)
    ap.add_argument("--slice-after", type=int, default=1400)

    # Prompts
    ap.add_argument("--prompt-dir", default="prompts")

    # Stage-0 toggle
    ap.add_argument("--stage0", action="store_true",
                    help="Run Stage 0 (full-doc GPT-5 index seeding) before Stage 1")

    args = ap.parse_args()

    set_runtime_overrides(model=args.model, survey_path=args.survey, schema_path=args.dag_schema)
    validate_env(raise_on_error=True)

    outdir = Path(args.output_dir); outdir.mkdir(parents=True, exist_ok=True)
    qdir = outdir / "questions"; qdir.mkdir(parents=True, exist_ok=True)
    chunks_dir = outdir / "chunks"; chunks_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = ts

    def log(msg: str):
        print(msg, flush=True)

    log("────────────────────────────────────────────────────────")
    log("Survey DAG staged extraction")
    log(f"  survey:      {args.survey}")
    log(f"  models:      s0={args.s0_model}  index={args.index_model}  content={args.content_model}  skips={args.skips_model}  (passes={args.passes})")
    log(f"  chunk/over:  {args.chunk_size}/{args.overlap}")
    log(f"  output dir:  {outdir}")
    log(f"  slice win:   -{args.slice_before}/+{args.slice_after} chars")
    log(f"  temps:       index={args.temp_index}  content={args.temp_content}  skips={args.temp_skips}")
    log(f"  stage0:      {'ON' if args.stage0 else 'OFF'}")
    log("────────────────────────────────────────────────────────")

    # ---------- Load PDF ----------
    log("Reading PDF text…")
    full_text, page_spans = read_pdf_all_text_with_spans(Path(args.survey))

    # ---------- Stage 0 (optional, recommended) ----------
    stage0_seeds: List[Dict[str, Any]] = []
    if args.stage0:
        prompt_s0 = str(Path(args.prompt_dir) / "stage0_index_full_gpt5.txt")
        log("\n[Stage 0/5] Full-document seeding of question index (GPT-5)…")
        # Use indexing agent with Stage-0 prompt; feed WHOLE doc.
        s0_agent = QuestionIndexAgent(model=args.s0_model, passes=1, quiet=True)
        if hasattr(s0_agent, "set_prompt_path"):
            try: s0_agent.set_prompt_path(prompt_s0)
            except Exception: pass
        elif hasattr(s0_agent, "prompt_path"):
            try: setattr(s0_agent, "prompt_path", prompt_s0)
            except Exception: pass
        t0 = time.perf_counter()
        s0_doc = s0_agent.run_window(full_text, page_start=1)  # full doc
        dt = time.perf_counter() - t0
        stage0_seeds = s0_doc.get("question_index", [])
        s0_out = outdir / f"stage0_seeds_{args.s0_model}_{run_id}.json"
        s0_out.write_text(json.dumps({"question_index": stage0_seeds}, indent=2), encoding="utf-8")
        log(f"  Stage0 seeds: {len(stage0_seeds)} ↳ {dt:.1f}s  → {s0_out.name}")

    # ---------- Windows (block-aware or pages) ----------
    if args.block_aware:
        blocks = detect_blocks(full_text, page_spans, min_hits=2, buffer_pages=1)
        log(f"Detected blocks: {summarize_blocks(blocks)}")
        windows = chunk_text_by_blocks(full_text, page_spans, blocks)
    else:
        windows = chunk_text_by_pages(full_text, page_spans, chunk_size=args.chunk_size, overlap=args.overlap)
    log(f"Pages detected: {len(page_spans)}  |  Windows: {len(windows)}")

    # ---------- Stage 1: Windowed indexing ----------
    log("\n[Stage 1/5] Indexing questions (IDs, order, coarse pages)…")
    prompt_s1 = str(Path(args.prompt_dir) / "stage1_index_window_gpt5.txt")

    idx_agent = QuestionIndexAgent(model=args.index_model, passes=args.passes, quiet=True)
    if hasattr(idx_agent, "set_prompt_path"):
        try: idx_agent.set_prompt_path(prompt_s1)
        except Exception: pass
    elif hasattr(idx_agent, "prompt_path"):
        try: setattr(idx_agent, "prompt_path", prompt_s1)
        except Exception: pass

    def idx_worker(w):
        t0 = time.perf_counter()
        doc = idx_agent.run_window(w["text"], page_start=w["start_page"])
        dt = time.perf_counter() - t0
        return w, doc, dt

    index_items: List[Dict[str, Any]] = []
    if max(1, args.index_workers) == 1:
        for w in windows:
            w, doc, dt = idx_worker(w)
            label = f"p{w['start_page']}-{w['end_page']}"
            log(f"  [Index] {label} ↳ {dt:.1f}s")
            (chunks_dir / f"index_chunk{w['idx']:03d}_p{w['start_page']}-{w['end_page']}.json").write_text(json.dumps(doc, indent=2))
            index_items.extend(doc.get("question_index", []))
    else:
        with ThreadPoolExecutor(max_workers=args.index_workers) as ex:
            futs = {ex.submit(idx_worker, w): w for w in windows}
            done = 0
            for f in as_completed(futs):
                w, doc, dt = f.result()
                done += 1
                label = f"p{w['start_page']}-{w['end_page']}"
                log(f"  [Index] {done}/{len(windows)} {label} ↳ {dt:.1f}s")
                (chunks_dir / f"index_chunk{w['idx']:03d}_p{w['start_page']}-{w['end_page']}.json").write_text(json.dumps(doc, indent=2))
                index_items.extend(doc.get("question_index", []))

    # Union Stage-0 seeds and Stage-1 results
    union_items = (stage0_seeds or []) + index_items
    ordered = _dedupe_index(union_items)

    idx_out = outdir / f"question_index_{args.index_model}_{run_id}.json"
    idx_out.write_text(json.dumps({"question_index": ordered}, indent=2))
    log(f"Indexed questions (union): {len(ordered)}  →  {idx_out.name}")
    if not ordered:
        log("No questions indexed. Exiting."); return

    # ---------- Stage 2: Content per question ----------
    log("\n[Stage 2/5] Extracting question content in parallel…")
    prompt_s2 = str(Path(args.prompt_dir) / "stage2_content_gpt5.txt")

    one_agent = ContentOneAgent(model=args.content_model, passes=args.passes, quiet=True)
    if hasattr(one_agent, "set_prompt_path"):
        try: one_agent.set_prompt_path(prompt_s2)
        except Exception: pass
    elif hasattr(one_agent, "prompt_path"):
        try: setattr(one_agent, "prompt_path", prompt_s2)
        except Exception: pass

    log("  Building smart slices for all questions…")
    question_slices = create_question_slices(full_text, page_spans, ordered)
    log(f"  Slices ready: {len(question_slices)}")

    def content_worker(q):
        qid = q["id"]
        qpath = qdir / f"{qid}.json"
        short_text = q.get("short_text", "")
        if not args.force and qpath.exists():
            node = json.loads(qpath.read_text())
            return qid, node, True, 0.0

        slice_text = question_slices.get(qid, "")
        if not slice_text or len(slice_text.strip()) < 40:
            node = {"id": qid, "text": short_text, "response_type":"text", "response_options": None}
            qpath.write_text(json.dumps(node, indent=2))
            return qid, node, False, 0.0

        tight = tighten_slice(slice_text, qid, short_text, args.slice_before, args.slice_after)
        t0 = time.perf_counter()
        node = one_agent.run_slice(tight, qid)
        dt = time.perf_counter() - t0
        if not node:
            node = {"id": qid, "text": short_text, "response_type":"text", "response_options": None}
        qpath.write_text(json.dumps(node, indent=2))
        return qid, node, False, dt

    results_map: Dict[str, Dict] = {}
    submitted = 0; completed = 0
    with ThreadPoolExecutor(max_workers=max(1, args.content_workers)) as ex:
        futures = {ex.submit(content_worker, q): q for q in ordered if args.force or not (qdir / f"{q['id']}.json").exists()}
        submitted = len(futures)
        log(f"  Submitted {submitted} new extractions; {len(ordered)-submitted} cached")
        for f in as_completed(futures):
            qid, node, cached, dt = f.result()
            results_map[qid] = node
            completed += 1
            if completed % 10 == 0 or completed == submitted:
                rt = node.get("response_type") or "?"
                opts = node.get("response_options") or []
                optn = len(opts) if isinstance(opts, list) else 0
                tag = "cached" if cached else f"{dt:.1f}s"
                log(f"    [Content {completed}/{submitted}] {qid}: {rt}, {optn} opts ({tag})")

    content_nodes: List[Dict] = []
    for q in ordered:
        qid = q["id"]; qpath = qdir / f"{qid}.json"
        if qid in results_map:
            content_nodes.append(results_map[qid])
        else:
            content_nodes.append(json.loads(qpath.read_text()))

    content_nodes = merge_content_nodes(content_nodes)
    content_nodes = ensure_nodes_for_all_index(
        ordered, content_nodes, full_text, page_spans,
        before_chars=args.slice_before, after_chars=args.slice_after
    )

    content_doc = {"survey_content": {"nodes": content_nodes}}
    content_out = outdir / f"content_{args.content_model}_{run_id}.json"
    content_out.write_text(json.dumps(content_doc, indent=2))
    log(f"Content snapshot → {content_out.name}")

    # ---------- Stage 3: Quality gate (informational) ----------
    log("\n[Stage 3/5] Quality gate on content coverage…")
    metrics = validate_extraction_quality(ordered, content_nodes, [])
    (outdir / f"quality_{args.content_model}_{run_id}.json").write_text(json.dumps(metrics, indent=2))
    log(f"  Coverage: content={metrics['content_coverage']:.1%}  index={metrics['index_count']}  content_nodes={metrics['content_count']}")
    if metrics["warnings"]:
        for w in metrics["warnings"][:8]:
            log(f"    - {w}")
        if len(metrics["warnings"]) > 8:
            log(f"    … {len(metrics['warnings'])-8} more")
    log("  Proceeding…")

    # ---------- Stage 4: Skips / predicates ----------
    log("\n[Stage 4/5] Extracting explicit skips/branching…")
    prompt_s4 = str(Path(args.prompt_dir) / "stage4_skips_gpt5.txt")
    skip_agent = SkipAgent(model=args.skips_model, passes=args.passes, quiet=True)
    if hasattr(skip_agent, "set_prompt_path"):
        try: skip_agent.set_prompt_path(prompt_s4)
        except Exception: pass
    elif hasattr(skip_agent, "prompt_path"):
        try: setattr(skip_agent, "prompt_path", prompt_s4)
        except Exception: pass

    def skip_worker(w):
        sdoc = skip_agent.run_window(w["text"])
        return {
            "survey_dag_structure": {
                "id": "survey", "version": "v0",
                "start": ordered[0]["id"] if ordered else "Q1",
                "terminals": ["END_COMPLETE"],
                "nodes": [{"id": q["id"], "kind": "question", "block": None, "response_type": None,
                           "universe": None, "universe_ast": None} for q in ordered],
                "edges": sdoc.get("edges", []),
                "predicates": sdoc.get("predicates", {}),
            }
        }

    struct_chunks: List[Dict] = []
    if max(1, args.skips_workers) == 1:
        for i, w in enumerate(windows, 1):
            t0 = time.perf_counter(); sdoc = skip_worker(w); dt = time.perf_counter() - t0
            log(f"  [Skips] {i}/{len(windows)} p{w['start_page']}-{w['end_page']} ↳ {dt:.1f}s")
            struct_chunks.append(sdoc)
            (chunks_dir / f"skips_chunk{w['idx']:03d}_p{w['start_page']}-{w['end_page']}.json").write_text(json.dumps(sdoc, indent=2))
    else:
        with ThreadPoolExecutor(max_workers=args.skips_workers) as ex:
            futs = {ex.submit(skip_worker, w): w for w in windows}
            done = 0
            for f in as_completed(futs):
                sdoc = f.result(); w = futs[f]; done += 1
                log(f"  [Skips] {done}/{len(windows)} p{w['start_page']}-{w['end_page']} ✓")
                struct_chunks.append(sdoc)
                (chunks_dir / f"skips_chunk{w['idx']:03d}_p{w['start_page']}-{w['end_page']}.json").write_text(json.dumps(sdoc, indent=2))

    structure_raw = reduce_structure_chunks(struct_chunks)
    s = structure_raw.get("survey_dag_structure", {})
    log(f"  Skips reduced → nodes={len(s.get('nodes', []))}, edges={len(s.get('edges', []))}, preds={len((s.get('predicates') or {}))}")

    # ---------- Stage 5: Repair-lite → Merge → Normalize → Validate → QC ----------
    log("\n[Stage 5/5] Merging with content, normalizing, and validating…")

    # (A) Repair-lite on structure: ensure P_TRUE, add sequential edges if very sparse
    structure_fixed, repair_report = repair_structure_with_content(structure_raw, content_doc)
    struct_out = outdir / f"structure_{args.content_model}_{run_id}.json"
    struct_out.write_text(json.dumps(structure_fixed, indent=2))
    (outdir / f"structure_repair_{args.content_model}_{run_id}.json").write_text(json.dumps({"repair": repair_report}, indent=2))
    log(f"  Structure (fixed) → {struct_out.name}")

    # Ensure P_TRUE after normalize_predicates later too
    struct = structure_fixed.get("survey_dag_structure") or {}
    predicates = struct.get("predicates") or {}
    if "P_TRUE" not in predicates:
        predicates["P_TRUE"] = {"expr": "Always true", "ast": ["TRUE"], "depends_on": []}
    struct["predicates"] = predicates

    # Add sequential fallback edges if edge count is very low relative to nodes
    node_ids_in_order = [q["id"] for q in ordered]
    edges_list = struct.get("edges") or []
    if needs_sequential_fallback(edges_list, node_count=len(node_ids_in_order), min_ratio=0.05):
        seq_edges = make_sequential_edges(node_ids_in_order, terminal_id=(struct.get("terminals") or [None])[0])
        existing = {(e["source"], e["target"]) for e in edges_list}
        for e in seq_edges:
            if (e["source"], e["target"]) not in existing:
                edges_list.append(e)
        struct["edges"] = edges_list

    struct = normalize_predicates(struct, allow_underscores=True)
    structure_fixed["survey_dag_structure"] = struct

    # (B) Merge structure+content into the core DAG
    dag_core = merge_to_core(structure_fixed, content_doc, full_text=full_text, page_spans=page_spans)

    # (C) Validation helpers before normalization: fix terminal aliases, ensure edge endpoints exist
    dag_core, alias_map = fix_terminal_aliases(dag_core,
                                               canonical="END_COMPLETE",
                                               aliases=("END", "END_SURVEY", "SUBMIT"))
    if alias_map:
        log(f"  Aliased terminals → {alias_map}")
    dag_core, stub_ids = ensure_edge_endpoints_exist(dag_core)
    if stub_ids:
        sample = sorted(set(stub_ids))[:8]
        more = " …" if len(set(stub_ids)) > 8 else ""
        log(f"  Added stub nodes for missing endpoints: {sample}{more}")

    # (D) Normalize to schema (non-lossy); sidecar preserves rich option/code data
    dag_core, sidecar = coerce_to_schema_nlossy(dag_core)
    stem = f"dag_core_{args.content_model}_{run_id}"
    (outdir / f"{stem}.sidecar.json").write_text(json.dumps(sidecar, ensure_ascii=False, indent=2))

    # (E) Validate & persist
    dag_schema_path = Path(args.dag_schema) if args.dag_schema else CONFIG.schema_path
    core_path = outdir / f"{stem}.json"
    try:
        validate_final_dag(dag_core, dag_schema_path)
        core_path.write_text(json.dumps(dag_core, indent=2))
        log(f"  Final DAG  → {core_path.name}")
    except Exception as e:
        invalid = outdir / f"{stem}.invalid.json"
        invalid.write_text(json.dumps({"dag": dag_core, "validation_error": str(e)}, indent=2))
        log(f"  Final DAG validation failed; wrote {invalid.name}")

    # (F) QC
    rep = qc_core_report(dag_core)
    (outdir / f"{stem}.qc.json").write_text(json.dumps(rep, indent=2))
    (outdir / f"{stem}.qc.md").write_text(qc_core_markdown(rep))

    log("\nDONE ✅")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    main()
