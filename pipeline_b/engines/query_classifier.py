import json
import time

from pipeline_b.embedding.embedder import embed_single
from pipeline_b.schemas.query import ClassifiedQuery, PersonaType, QueryType
from shared.logger import get_logger


logger = get_logger(__name__)


RULES: dict[QueryType, list[str]] = {
    QueryType.trend: [
        "trend",
        "over time",
        "last 3",
        "changed",
        "history",
        "previous",
        "comparison",
        "improving",
        "worsening",
        "getting better",
        "getting worse",
        "across visits",
    ],
    QueryType.retrieval: [
        "show me",
        "find",
        "list",
        "which patients",
        "all patients",
        "who has",
        "records for",
        "reports for",
        "patients with",
    ],
    QueryType.reasoning: [
        "is this normal",
        "what does",
        "interpret",
        "explain",
        "significance",
        "suggest",
        "indicate",
        "abnormal",
        "what is",
        "why is",
        "clinical",
        "diagnosis",
        "concern",
    ],
    QueryType.patient_chat: [
        "what is my",
        "am i",
        "should i",
        "my report",
        "my result",
        "my test",
        "my blood",
        "understand my",
    ],
}


EXAMPLE_QUERIES: dict[QueryType, list[str]] = {
    QueryType.retrieval: [
        "show me all patients with low hemoglobin",
        "find patients with platelet count below 150",
        "list all lab reports from october 2025",
        "which patients have abnormal ESR",
    ],
    QueryType.reasoning: [
        "is this CBC result normal for a 50 year old female",
        "what does elevated ESR with low hemoglobin indicate",
        "interpret these lab values for me",
        "explain the clinical significance of these findings",
    ],
    QueryType.trend: [
        "how has hemoglobin changed over the last 3 visits",
        "show me the trend for platelet count",
        "is the ESR improving over time",
        "hemoglobin history for this patient",
    ],
    QueryType.patient_chat: [
        "what does my hemoglobin result mean",
        "is my blood test normal",
        "can you explain my report in simple language",
        "what does low hemoglobin mean for me",
    ],
}


_example_embeddings: dict[QueryType, list[list[float]]] | None = None


def _get_example_embeddings() -> dict[QueryType, list[list[float]]]:
    global _example_embeddings
    if _example_embeddings is None:
        _example_embeddings = {
            qt: [embed_single(q) for q in queries]
            for qt, queries in EXAMPLE_QUERIES.items()
        }
    return _example_embeddings


def _embedding_classify(query_vec: list[float]) -> tuple[QueryType, float]:
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    examples = _get_example_embeddings()
    best_type, best_score = QueryType.reasoning, 0.0
    for qt, vecs in examples.items():
        scores = cosine_similarity([query_vec], vecs)[0]
        score = float(np.max(scores))
        if score > best_score:
            best_score = score
            best_type = qt
    return best_type, best_score


def _llm_classify(query: str, persona: PersonaType) -> ClassifiedQuery:
    from openai import OpenAI

    from shared.config import get_settings

    client = OpenAI(api_key=get_settings().OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify this medical query into exactly one of: "
                    "retrieval, reasoning, trend, patient_chat. "
                    'Return JSON: {"type": "...", "confidence": 0.0}'
                ),
            },
            {"role": "user", "content": query},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    return ClassifiedQuery(
        text=query,
        persona=persona,
        query_type=QueryType(result["type"]),
        confidence=result["confidence"],
        classification_method="llm",
    )


def classify(query: str, persona: PersonaType) -> ClassifiedQuery:
    query_lower = query.lower()
    t_start = time.time()

    scores = {
        qt: sum(1 for kw in kws if kw in query_lower)
        for qt, kws in RULES.items()
    }
    best_rule = max(scores, key=scores.get)
    if scores[best_rule] >= 2:
        result = ClassifiedQuery(
            text=query,
            persona=persona,
            query_type=best_rule,
            confidence=min(scores[best_rule] / 4.0, 1.0),
            classification_method="rule",
        )
        logger.info(
            "query_classified",
            method="rule",
            type=best_rule.value,
            confidence=result.confidence,
            duration_ms=round((time.time() - t_start) * 1000, 2),
        )
        return result

    query_vec = embed_single(query)
    emb_type, emb_score = _embedding_classify(query_vec)
    if emb_score >= 0.70:
        result = ClassifiedQuery(
            text=query,
            persona=persona,
            query_type=emb_type,
            confidence=emb_score,
            classification_method="embedding",
        )
        logger.info(
            "query_classified",
            method="embedding",
            type=emb_type.value,
            confidence=emb_score,
            duration_ms=round((time.time() - t_start) * 1000, 2),
        )
        return result

    logger.warning(
        "classifier_fallback_to_llm",
        query=query[:100],
        rule_score=scores[best_rule],
        emb_score=emb_score,
    )
    result = _llm_classify(query, persona)
    logger.info(
        "query_classified",
        method="llm",
        type=result.query_type.value,
        confidence=result.confidence,
        duration_ms=round((time.time() - t_start) * 1000, 2),
    )
    return result
