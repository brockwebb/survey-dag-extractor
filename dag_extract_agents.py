# dag_extract_agents.py
from __future__ import annotations
import argparse, logging, warnings, os, json
from pathlib import Path
from datetime import datetime, timezone
from jsonschema import Draft7Validator, validate as jsonschema_validate

from config import CONFIG, set_runtime_overrides, validate_env
from io_utils.pdf_utils import read_pdf_all_text_with_spans
from chunking.page_windows import chunk_text_by_pages
from agents.structure_agent import StructureAgent
from agents.content_agent import ContentAgent
from reducers.chunk_reduce import reduce_structure_chunks, reduce_content_chunks
from merge.merge_core import merge_to_core
from validators.structure import validate_structure_doc, validate_content_doc
from validators.qc_core import qc_core_report, qc_core_markdown
from validators.repairs import repair_structure_with_content

def silence_logs(level=logging.ERROR):
    warnings.filterwarnings("ignore")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    for name in ("", "langextract", "langextract.alignment", "langextract.core",
                 "pdfplumber", "pdfminer", "fitz", "PIL"):
        logging.getLogger(name).setLevel(level)
        logging.getLogger(name).propagate = False
    try:
        from absl import logging as absl_logging
        absl_logging.set_verbosity(absl_logging.ERROR)
        os.environ["ABSL_LOGGING_MIN_SEVERITY"] = "3"
    except Exception:
        pass

def validate_final_dag(doc: dict, schema_path: Path):
    schema = json.loads(schema_path.read_text())
    Draft7Validator.check_schema(schema)
    jsonschema_validate(instance=doc, schema=schema)

def main():
    ap = argparse.ArgumentParser(description="Chunked three-pass extraction → /output (+QC, tolerant)")
    ap.add_argument("--survey", required=True, help="PDF path (e.g., data/HTOPS_2502_Questionnaire_ENGLISH.pdf)")
    ap.add_argument("--out-base", default="dag", help="Base filename stem (no extension)")
    ap.add_argument("--output-dir", default="output", help="Directory to write artifacts")
    ap.add_argument("--model-structure", default=None)
    ap.add_argument("--model-content", default=None)
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 4))
    ap.add_argument("--workers-structure", type=int, default=None, help="Override workers for Structure pass only")
    ap.add_argument("--workers-content", type=int, default=None, help="Override workers for Content pass only")
    ap.add_argument("--char-buffer", type=int, default=1200)
    ap.add_argument("--chunk-size", type=int, default=10, help="Pages per chunk window")
    ap.add_argument("--overlap", type=int, default=2, help="Overlapping pages between adjacent windows")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--log-level", default="WARNING")
    ap.add_argument("--no-auto-names", action="store_true")
    ap.add_argument("--structure-schema", default="data/survey_structure_schema.json")
    ap.add_argument("--content-schema", default="data/survey_content_schema.json")
    ap.add_argument("--dag-schema", default=None, help="defaults to CONFIG.schema_path")
    ap.add_argument("--no-silence", action="store_true", help="Do not force-silence third-party logs")
    ap.add_argument("--strict", action="store_true", help="Fail fast on validation errors (default: tolerant)")
    args = ap.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.WARNING),
                        format="%(levelname)s: %(message)s")
    if not args.no_silence:
        silence_logs(level=logging.ERROR)

    set_runtime_overrides(model=None, survey_path=args.survey, schema_path=args.dag_schema)
    validate_env(raise_on_error=True)

    output_dir = Path(args.output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    chunk_dir = output_dir / "chunks"; chunk_dir.mkdir(parents=True, exist_ok=True)

    full_text, page_spans = read_pdf_all_text_with_spans(Path(args.survey))
    windows = chunk_text_by_pages(full_text, page_spans, chunk_size=args.chunk_size, overlap=args.overlap)
    if not windows:
        raise RuntimeError("No pages detected in the PDF.")

    model_structure = args.model_structure or (CONFIG.model_name or "gpt-5")
    model_content   = args.model_content   or (CONFIG.model_name or "gpt-5")

    w_struct = args.workers_structure if args.workers_structure is not None else args.workers
    w_content= args.workers_content   if args.workers_content   is not None else args.workers

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base = args.out_base

    # name helpers
    def name(prefix):  # without extension
        if args.no_auto_names:
            return f"{prefix}"
        return f"{prefix}_{ts}"

    # per-chunk artifacts
    chunk_struct_docs = []
    chunk_content_docs = []

    struct_agent = StructureAgent(model=model_structure, passes=args.passes, workers=w_struct,
                                  char_buf=args.char_buffer, quiet=args.quiet)
    content_agent = ContentAgent(model=model_content, passes=args.passes, workers=w_content,
                                 char_buf=args.char_buffer, quiet=args.quiet)

    # ---- Run agents per chunk window (sequential for determinism) ----
    for win in windows:
        idx = win["idx"]
        pages = f"{win['start_page']}-{win['end_page']}" if win["start_page"] != win["end_page"] else f"{win['start_page']}"
        text = win["text"]

        sdoc = struct_agent.run(text)
        cdoc = content_agent.run(text)

        s_path = chunk_dir / f"{name(f'{base}_structure_chunk{idx:03d}_p{pages}')}.json"
        c_path = chunk_dir / f"{name(f'{base}_content_chunk{idx:03d}_p{pages}')}.json"
        s_path.write_text(json.dumps(sdoc, indent=2))
        c_path.write_text(json.dumps(cdoc, indent=2))
        print(f"Wrote {s_path}")
        print(f"Wrote {c_path}")

        chunk_struct_docs.append(sdoc)
        chunk_content_docs.append(cdoc)

    # ---- Reduce chunks → global structure/content ----
    structure_raw = reduce_structure_chunks(chunk_struct_docs)
    content = reduce_content_chunks(chunk_content_docs)

    # write reduced globals immediately
    struct_raw_path = output_dir / f"{name(f'{base}_structure.reduced')}.json"
    content_path    = output_dir / f"{name(f'{base}_content.reduced')}.json"
    struct_raw_path.write_text(json.dumps(structure_raw, indent=2))
    content_path.write_text(json.dumps(content, indent=2))
    print(f"Wrote {struct_raw_path}")
    print(f"Wrote {content_path}")

    # ---- Validate content (soft), repair structure using content IDs ----
    try:
        validate_content_doc(content, Path(args.content_schema))
    except Exception as e:
        print(f"Content validation warning: {e}")

    structure_fixed, repair_report = repair_structure_with_content(structure_raw, content)
    repair_path = output_dir / f"{name(f'{base}_structure.repair')}.json"
    repair_path.write_text(json.dumps({"repair": repair_report}, indent=2))
    print(f"Wrote {repair_path}")

    # structure schema validation (soft unless --strict)
    try:
        validate_structure_doc(structure_fixed, Path(args.structure_schema))
    except Exception as e:
        if args.strict:
            raise
        print(f"Structure validation warning: {e}")

    struct_path = output_dir / f"{name(f'{base}_structure')}.json"
    struct_path.write_text(json.dumps(structure_fixed, indent=2))
    print(f"Wrote {struct_path}")

    # ---- Merge → production DAG ----
    dag = merge_to_core(structure_fixed, content, full_text=full_text, page_spans=page_spans)
    dag_schema_path = Path(args.dag_schema) if args.dag_schema else CONFIG.schema_path
    core_path = output_dir / f"{name(f'{base}_core')}.json"
    try:
        validate_final_dag(dag, dag_schema_path)
        core_path.write_text(json.dumps(dag, indent=2))
        print(f"Wrote {core_path}")
    except Exception as e:
        invalid_path = core_path.with_suffix(".invalid.json")
        invalid_path.write_text(json.dumps({"dag": dag, "validation_error": str(e)}, indent=2))
        print(f"Final DAG validation failed; wrote {invalid_path}")

    # ---- QC (JSON + Markdown) ----
    from validators.qc_core import qc_core_report, qc_core_markdown
    qcj = output_dir / f"{name(f'{base}_core.qc')}.json"
    qcmd = output_dir / f"{name(f'{base}_core.qc')}.md"
    report = qc_core_report(dag)
    qcj.write_text(json.dumps(report, indent=2))
    qcmd.write_text(qc_core_markdown(report))
    print(f"Wrote {qcj}")
    print(f"Wrote {qcmd}\nOK")

if __name__ == "__main__":
    main()
