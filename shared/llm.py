from openai import OpenAI
from shared.config import get_settings
from shared.logger import get_logger

logger = get_logger(__name__)

_client = None

def get_llm_client() -> OpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        if settings.LLM_PROVIDER.lower() == "groq":
            logger.info("Initializing Groq LLM client")
            _client = OpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )
        else:
            logger.info("Initializing OpenAI LLM client")
            _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client

def get_text_model() -> str:
    return get_settings().LLM_TEXT_MODEL

def get_vision_model() -> str:
    return get_settings().LLM_VISION_MODEL
