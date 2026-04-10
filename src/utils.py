import re
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


def clean_name(name: str) -> str:
    """Remove ' - Section X' suffixes from chunked document names."""
    if not name:
        return name
    return re.sub(r'\s*-?\s*section\s*\d+$', '', name, flags=re.IGNORECASE).strip()


def truncate_context(text: str, max_chars: int = 25000) -> str:
    """Soft truncation to prevent context overflow while preserving quality."""
    if len(text) <= max_chars:
        return text
    logger.info(f"Truncating context from {len(text)} to {max_chars} chars.")
    return text[:max_chars] + "... [context truncated for stability]"


def safe_llm_call(client: OpenAI, models: List[str], messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
    """
    LLM call with automatic fallback logic.
    Tries each model in the list until one succeeds.
    """
    for model in models:
        try:
            logger.info(f"Attempting LLM call with model: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                timeout=120,  # 2 minute timeout per attempt
                **kwargs
            )
            if response and response.choices:
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Model {model} failed or timed out: {e}")
            continue

    return None
