from sentence_transformers import SentenceTransformer


_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embed_single(text: str) -> list[float]:
    return embed([text])[0]
