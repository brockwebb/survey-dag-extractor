# stage0_full_index.py
from __future__ import annotations
import json
from typing import List, Dict, Any, Optional
import os
import langextract as lx

def run_stage0_full_index(
    full_text: str,
    prompt_path: str = "prompts/stage0_index_full_gpt5.txt",
    model_id: str = "gpt-5",
    api_key_env: str = "OPENAI_API_KEY",
) -> List[Dict[str, Any]]:
    """
    Stage 0: A single full-document pass with GPT-5 to extract the ordered question index.
    Uses LangExtract with OpenAI provider (fenced output; no schema constraints).
    Returns a list of {id, short_text, page_guess}.
    """

    # LangExtract prefers LANGEXTRACT_API_KEY. Bridge OPENAI_API_KEY if needed.
    api_key = os.getenv("LANGEXTRACT_API_KEY") or os.getenv(api_key_env)
    if not os.getenv("LANGEXTRACT_API_KEY") and api_key:
        os.environ["LANGEXTRACT_API_KEY"] = api_key

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read().strip()

    # Single-pass, single-worker; let GPT-5 process the whole text
    result = lx.extract(
        text_or_documents=full_text,
        prompt_description=prompt,
        examples=[],                      # no few-shot needed for a strict JSON task
        model_id=model_id,                # "gpt-5" (full) by default
        fence_output=True,                # REQUIRED for OpenAI provider per README
        use_schema_constraints=False,     # REQUIRED for OpenAI provider per README
        extraction_passes=1,
        max_workers=1,
        max_char_buffer=2000,             # generous; not critical for single pass
    )

    # LangExtract returns a structured annotated document; the fenced JSON is in result.content
    # Normalize to Python object
    content = getattr(result, "content", None)
    if isinstance(content, (bytes, bytearray)):
        content = content.decode("utf-8", "ignore")
    if not isinstance(content, str):
        content = str(content or "")

    try:
        payload = json.loads(content)
        items = payload.get("question_index", [])
        # Basic sanity/shape check
        out = []
        for it in items:
            if not isinstance(it, dict):
                continue
            qid = it.get("id")
            st = it.get("short_text")
            pg = it.get("page_guess")
            if isinstance(qid, str) and qid.strip():
                out.append({
                    "id": qid.strip(),
                    "short_text": (st or "")[:200],
                    "page_guess": int(pg) if isinstance(pg, int) else None,
                })
        return out
    except Exception as e:
        raise RuntimeError(f"Stage 0 JSON parse failed: {e}\nRaw content snippet:\n{content[:800]}")

