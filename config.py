# config.py
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    _HAS_DOTENV = True
except Exception:
    _HAS_DOTENV = False

PROJECT_ROOT = Path(__file__).resolve().parent

DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "data" / "survey_dag_schema.json"
DEFAULT_PROMPT_DIR  = PROJECT_ROOT / "prompts"

# Model defaults (all-in GPT-5x)
DEFAULT_S0_MODEL      = "gpt-5"       # Stage 0 (full-doc seeds)
DEFAULT_INDEX_MODEL   = "gpt-5-mini"  # Stage 1
DEFAULT_CONTENT_MODEL = "gpt-5-mini"  # Stage 2
DEFAULT_SKIPS_MODEL   = "gpt-5-mini"  # Stage 4

# Temperatures
DEFAULT_TEMPERATURE = 0.0
EDGE_TEMPERATURE    = 0.05

@dataclass
class RuntimeConfig:
    # Paths
    survey_path: Optional[Path] = None
    schema_path: Path = DEFAULT_SCHEMA_PATH
    prompt_dir: Path = DEFAULT_PROMPT_DIR

    # Models
    s0_model: str = DEFAULT_S0_MODEL
    index_model: str = DEFAULT_INDEX_MODEL
    content_model: str = DEFAULT_CONTENT_MODEL
    skips_model: str = DEFAULT_SKIPS_MODEL

    # Temperatures
    temp_index: float = DEFAULT_TEMPERATURE
    temp_content: float = DEFAULT_TEMPERATURE
    temp_skips: float = DEFAULT_TEMPERATURE

    # API keys (read from env)
    openai_api_key: Optional[str] = None
    langextract_api_key: Optional[str] = None

CONFIG = RuntimeConfig()

def _load_env():
    if _HAS_DOTENV:
        # Load from project root .env if present
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)

    # Read keys
    CONFIG.openai_api_key = os.getenv("OPENAI_API_KEY")
    CONFIG.langextract_api_key = os.getenv("LANGEXTRACT_API_KEY")

    # Bridge OPENAI_API_KEY -> LANGEXTRACT_API_KEY (langextract uses the latter)
    if not CONFIG.langextract_api_key and CONFIG.openai_api_key:
        os.environ["LANGEXTRACT_API_KEY"] = CONFIG.openai_api_key
        CONFIG.langextract_api_key = CONFIG.openai_api_key

def set_runtime_overrides(
    model: Optional[str] = None,
    survey_path: Optional[str] = None,
    schema_path: Optional[str] = None,
    prompt_dir: Optional[str] = None,
):
    if model:
        CONFIG.index_model = CONFIG.content_model = CONFIG.skips_model = model
    if survey_path:
        CONFIG.survey_path = Path(survey_path).resolve()
    if schema_path:
        CONFIG.schema_path = Path(schema_path).resolve()
    if prompt_dir:
        CONFIG.prompt_dir = Path(prompt_dir).resolve()

def validate_env(raise_on_error: bool = False) -> bool:
    _load_env()
    missing = []

    # API keys
    if not (CONFIG.openai_api_key or CONFIG.langextract_api_key):
        missing.append("OPENAI_API_KEY (or LANGEXTRACT_API_KEY)")

    # Schema path
    if not CONFIG.schema_path.exists():
        missing.append(f"SCHEMA_PATH missing file: {CONFIG.schema_path}")

    # Prompt dir (warn if Stage-0 prompt missing)
    s0_prompt = CONFIG.prompt_dir / "stage0_index_full_gpt5.txt"
    if not s0_prompt.exists():
        missing.append(f"Prompt missing: {s0_prompt}")

    if missing and raise_on_error:
        raise RuntimeError("Configuration error:\n  - " + "\n  - ".join(missing))
    return not missing
