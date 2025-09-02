# stage0_full_index.py
from __future__ import annotations
import json, os
from typing import List, Dict, Any
import langextract as lx

def run_stage0_full_index(
    full_text: str,
    prompt_path: str = "prompts/stage0_index_full_gpt5.txt",
    model_id: str = "gpt-5",
) -> List[Dict[str, Any]]:
    """
    Stage 0: One full-document pass with GPT-5 (via langextract/OpenAI provider)
    to enumerate the ordered question index.
    """
    # Bridge OPENAI_API_KEY -> LANGEXTRACT_API_KEY if needed
    api_key = os.getenv("LANGEXTRACT_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key and not os.getenv("LANGEXTRACT_API_KEY"):
        os.environ["LANGEXTRACT_API_KEY"] = api_key

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read().strip()

    # OpenAI provider with langextract requires these flags
    result = lx.extract(
        text_or_documents=full_text,
        prompt_description=prompt,
        examples=[],
        model_id=model_id,            # "gpt-5" (full) for Stage 0
        fence_output=True,            # required for OpenAI provider
        use_schema_constraints=False, # required for OpenAI provider
        extraction_passes=1,
        max_workers=1,
        max_char_buffer=2000,
    )

    content = getattr(result, "content", None)
    if isinstance(content, (bytes, bytearray)):
        content = content.decode("utf-8", "ignore")
    if not isinstance(content, str):
        content = str(content or "")

    try:
        payload = json.loads(content)
        items = payload.get("question_index", [])
        out: List[Dict[str, Any]] = []
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
        raise RuntimeError(f"Stage 0 JSON parse failed: {e}\nRaw snippet:\n{content[:800]}")

