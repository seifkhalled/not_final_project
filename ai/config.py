import os
from dotenv import load_dotenv

load_dotenv()


class AIConfig:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    
    if not OPENROUTER_API_KEY and not GROQ_API_KEY:
        raise EnvironmentError("Neither OPENROUTER_API_KEY nor GROQ_API_KEY is set in environment.")
        
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    
    LLM_MODEL = os.getenv("OPENROUTER_TRIP_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free")
    TOOL_CALL_MODEL = os.getenv("OPENROUTER_TOOL_MODEL", "stepfun/step-3.5-flash:free")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    API_BASE_URL = os.getenv("API_BASE_URL", "")
    
    FALLBACK_MODELS = [
        "mistralai/mistral-7b-instruct:free",
        "meta-llama/llama-3-8b-instruct:free"
    ]

    LLM_TEMPERATURE = 0.7
    LLM_MAX_TOKENS = 4096
    LLM_SUMMARY_MAX_TOKENS = 256
