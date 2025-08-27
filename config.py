# config.py
from __future__ import annotations
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- Robust .env discovery ----------------------------------------------------
REPO_ROOT = Path(os.getenv("REPO_ROOT") or Path.cwd())
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path)
        REPO_ROOT = Path(os.getenv("REPO_ROOT") or Path(dotenv_path).resolve().parent)
except Exception:
    pass

def _discover_schema() -> Path:
    # Try the common places; prefer data/ first.
    candidates = [
        REPO_ROOT / "data" / "survey_dag_schema.json",
        Path.cwd() / "data" / "survey_dag_schema.json",
        REPO_ROOT / "survey_dag_schema.json",
        Path.cwd() / "survey_dag_schema.json",
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    # Default to REPO_ROOT/data even if missing; validate_env will surface a clear error.
    return (REPO_ROOT / "data" / "survey_dag_schema.json").resolve()

def _discover_pdf_default() -> Path:
    return (REPO_ROOT / "data" / "HTOPS_2502_Questionnaire_ENGLISH.pdf").resolve()

# --- App configuration --------------------------------------------------------
@dataclass
class AppConfig:
    # Auth / routing
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    openai_base_url: Optional[str] = os.environ.get("OPENAI_BASE_URL") or None
    openai_org: Optional[str] = os.environ.get("OPENAI_ORG") or None
    openai_project: Optional[str] = os.environ.get("OPENAI_PROJECT") or None

    # Model defaults (CLI can override)
    model_name: str = os.environ.get("MODEL_NAME", "gpt-5-mini")
    temperature: float = float(os.environ.get("MODEL_TEMPERATURE", "0.0"))
    max_tokens: int = int(os.environ.get("MODEL_MAX_TOKENS", "2000"))
    request_timeout: int = int(os.environ.get("OPENAI_TIMEOUT_S", "60"))

    # Paths (default to data/; CLI can override)
    repo_root: Path = REPO_ROOT
    schema_path: Path = Path(os.environ.get("SCHEMA_PATH") or _discover_schema())
    pdf_path: Path = Path(os.environ.get("PDF_PATH") or _discover_pdf_default())

    # Misc
    verbosity: int = int(os.environ.get("VERBOSITY", "1"))

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["repo_root"] = str(self.repo_root)
        d["schema_path"] = str(self.schema_path)
        d["pdf_path"] = str(self.pdf_path)
        return d

CONFIG = AppConfig()

# --- Runtime overrides (for CLI) ---------------------------------------------
def set_runtime_overrides(*, model: Optional[str] = None, survey_path: Optional[str] = None,
                          schema_path: Optional[str] = None) -> None:
    if model:
        CONFIG.model_name = model
    if survey_path:
        CONFIG.pdf_path = Path(survey_path).expanduser().resolve()
    if schema_path:
        CONFIG.schema_path = Path(schema_path).expanduser().resolve()

# --- OpenAI client + helpers --------------------------------------------------
def openai_client():
    from openai import OpenAI  # lazy import
    kwargs: Dict[str, Any] = {}
    if CONFIG.openai_base_url:
        kwargs["base_url"] = CONFIG.openai_base_url
    return OpenAI(**kwargs)  # reads OPENAI_* env vars

def llm_call(
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    client = openai_client()
    mdl = model or CONFIG.model_name
    temp = CONFIG.temperature if temperature is None else float(temperature)
    mx = CONFIG.max_tokens if max_tokens is None else int(max_tokens)

    resp = client.chat.completions.create(
        model=mdl,
        temperature=temp,
        max_tokens=mx,
        messages=messages,
        timeout=CONFIG.request_timeout,
    )
    return (resp.choices[0].message.content or "").strip()

def langextract_llm(prompt: str, *, text: Optional[str] = None,
                    system: Optional[str] = None, model: Optional[str] = None) -> str:
    sys_msg = system or "You are an expert survey extractor. Return only valid JSON."
    msgs = [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]
    if text:
        msgs.append({"role": "user", "content": text})
    return llm_call(msgs, model=model)

# --- Utilities ----------------------------------------------------------------
def validate_env(raise_on_error: bool = True) -> bool:
    missing: List[str] = []
    if not CONFIG.openai_api_key:
        missing.append("OPENAI_API_KEY")
    if not CONFIG.schema_path.exists():
        missing.append(f"SCHEMA_PATH missing file: {CONFIG.schema_path}")
    if not CONFIG.pdf_path.exists():
        missing.append(f"PDF_PATH missing file: {CONFIG.pdf_path}")
    if missing and raise_on_error:
        raise RuntimeError("Configuration error:\n  - " + "\n  - ".join(missing))
    return len(missing) == 0

def resolve_path(p: str | Path) -> Path:
    return Path(p).expanduser().resolve()

__all__ = [
    "CONFIG",
    "AppConfig",
    "set_runtime_overrides",
    "openai_client",
    "llm_call",
    "langextract_llm",
    "validate_env",
    "resolve_path",
]
