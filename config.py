"""
Configuration module for Survey DAG Extractor
Handles model selection and API keys
"""

import os
from typing import Optional, Literal
from dataclasses import dataclass


@dataclass
class ExtractorConfig:
    """
    Configuration for extraction pipeline.
    """
    primary_model: Literal["gpt-4o", "claude-3-5-sonnet"] = "gpt-4o"
    secondary_model: Literal["gpt-4o-mini", "claude-3-haiku"] = "gpt-4o-mini"
    debug: bool = False
    
    # LangExtract settings
    max_char_buffer: int = 4000  # Chunk size for processing
    max_workers: int = 4  # Parallel processing
    max_retries: int = 3
    
    # API Keys (from environment)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    def __post_init__(self):
        """Load API keys from environment."""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Set appropriate key for LangExtract
        if "gpt" in self.primary_model:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            os.environ['LANGEXTRACT_API_KEY'] = self.openai_api_key
        elif "claude" in self.primary_model:
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
            os.environ['LANGEXTRACT_API_KEY'] = self.anthropic_api_key
    
    def get_model_id(self, use_secondary: bool = False) -> str:
        """Get the appropriate model ID for LangExtract."""
        model = self.secondary_model if use_secondary else self.primary_model
        
        # Map to actual model IDs
        model_map = {
            "gpt-4o": "gpt-4o",
            "gpt-4o-mini": "gpt-4o-mini", 
            "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
            "claude-3-haiku": "claude-3-haiku-20240307"
        }
        
        return model_map.get(model, model)
