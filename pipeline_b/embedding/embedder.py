from openai import OpenAI
from shared.config import get_settings
from shared.logger import get_logger

logger = get_logger(__name__)

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY is missing. Embeddings generation may fail.")
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    client = _get_client()
    settings = get_settings()
    model = getattr(settings, "LLM_EMBEDDING_MODEL", "text-embedding-3-small")

    # OpenAI API raises 400 invalid request error for empty strings ""
    cleaned_texts = [t if t and str(t).strip() else " " for t in texts]

    all_embeddings = []
    chunk_size = 500  # Process up to 500 chunks per request to avoid API batch limits

    for i in range(0, len(cleaned_texts), chunk_size):
        batch = cleaned_texts[i : i + chunk_size]
        try:
            response = client.embeddings.create(
                model=model,
                input=batch,
            )
            # Ensure exact ordering matches the input batch
            sorted_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([item.embedding for item in sorted_data])
        except Exception as e:
            logger.error(f"Failed to generate embeddings with model {model}: {e}")
            raise

    return all_embeddings


def embed_single(text: str) -> list[float]:
    return embed([text])[0]

