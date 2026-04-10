import logging
import os
from openai import OpenAI
from ai.config import AIConfig
from dataclasses import dataclass
from openai import RateLimitError


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMClient:
    def __init__(self):
        self._setup_client("openrouter")
        self.temperature = AIConfig.LLM_TEMPERATURE
        self.max_tokens = AIConfig.LLM_MAX_TOKENS
        self.current_provider = "openrouter"

    def _setup_client(self, provider):
        if provider == "groq":
            self.client = OpenAI(
                base_url=AIConfig.GROQ_BASE_URL,
                api_key=AIConfig.GROQ_API_KEY,
            )
            self.model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
        else:
            self.client = OpenAI(
                base_url=AIConfig.OPENROUTER_BASE_URL,
                api_key=AIConfig.OPENROUTER_API_KEY,
            )
            self.model = AIConfig.LLM_MODEL or os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free")
        self.current_provider = provider

    def chat(self, system_prompt, user_prompt, max_tokens=None, model=None, provider=None):
        # If provider changes or model is explicitly provided
        if provider and provider != self.current_provider:
            self._setup_client(provider)
        
        target_model = model or self.model
        models_to_try = [target_model]
        
        # Only add fallbacks if we are using the default model
        if not model:
            models_to_try += AIConfig.FALLBACK_MODELS
            
        last_error = None
        
        for m in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=m,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=max_tokens or self.max_tokens,
                )

                usage = response.usage
                logging.info(f"\n{'='*50}")
                logging.info(f"LLM Token Usage ({m}) [Provider: {self.current_provider}]")
                logging.info(f"  Input tokens:  {usage.prompt_tokens}")
                logging.info(f"  Output tokens: {usage.completion_tokens}")
                logging.info(f"  Total tokens:  {usage.total_tokens}")
                logging.info(f"{'='*50}\n")

                return LLMResponse(
                    content=response.choices[0].message.content,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                )
            except Exception as e:
                last_error = e
                logging.warning(f"Error for model {m}: {str(e)}")
                if not model: # Only try next model if no specific model was requested
                    continue
                else:
                    break
        
        if last_error:
            raise last_error
