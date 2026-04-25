# """Inline tests for pipeline_a/matching/matcher.py.

# Mocks: structlog, rapidfuzz, sentence_transformers, sklearn, numpy
# so tests run without those packages installed.
# """
# import sys
# import types
# from pathlib import Path
# from unittest.mock import MagicMock

# # Ensure project root is on sys.path
# _project_root = str(Path(__file__).resolve().parent.parent)
# if _project_root not in sys.path:
#     sys.path.insert(0, _project_root)

# # ===========================================================================
# # Mock structlog
# # ===========================================================================
# ms = types.ModuleType("structlog")
# ms.stdlib = types.ModuleType("structlog.stdlib")
# ms.contextvars = types.ModuleType("structlog.contextvars")
# ms.processors = types.ModuleType("structlog.processors")

# class ML:
#     def info(self, *a, **kw): pass
#     def error(self, *a, **kw): pass
#     def warning(self, *a, **kw): pass
#     def debug(self, *a, **kw): pass

# ms.stdlib.BoundLogger = ML
# ms.stdlib.LoggerFactory = lambda: None
# ms.stdlib.filter_by_level = ms.stdlib.add_logger_name = ms.stdlib.add_log_level = lambda *a: None
# ms.stdlib.PositionalArgumentsFormatter = lambda: None
# ms.contextvars.merge_contextvars = lambda *a: None
# ms.processors.TimeStamper = lambda **kw: None
# ms.processors.StackInfoRenderer = ms.processors.UnicodeDecoder = ms.processors.JSONRenderer = lambda: None
# ms.configure = lambda **kw: None
# ms.get_logger = lambda name: ML()
# for k in ["structlog", "structlog.stdlib", "structlog.contextvars", "structlog.processors"]:
#     sys.modules[k] = ms if k == "structlog" else getattr(ms, k.split(".")[-1])

# # ===========================================================================
# # Mock numpy (minimal)
# # ===========================================================================
# import numpy as np  # numpy is usually available; if not, this test file won't run

# # ===========================================================================
# # Mock rapidfuzz
# # ===========================================================================
# rf = types.ModuleType("rapidfuzz")
# rf_fuzz = types.ModuleType("rapidfuzz.fuzz")
# rf_process = types.ModuleType("rapidfuzz.process")


# def _mock_token_set_ratio(s1, s2):
#     """Simple mock scorer: character overlap ratio."""
#     s1l, s2l = s1.lower(), s2.lower()
#     if s1l == s2l:
#         return 100.0
#     shorter, longer = (s1l, s2l) if len(s1l) <= len(s2l) else (s2l, s1l)
#     if shorter in longer:
#         return 90.0
#     common = sum(1 for c in set(shorter) if c in longer)
#     return min((common / max(len(set(shorter)), 1)) * 100, 100.0)


# def _mock_extract_one(query, choices, scorer=None):
#     """Mock extractOne: finds the best match by scorer."""
#     if not choices:
#         return None
#     sc = scorer or _mock_token_set_ratio
#     best_phrase = None
#     best_score = -1
#     best_idx = 0
#     for i, choice in enumerate(choices):
#         score = sc(query, choice)
#         if score > best_score:
#             best_score = score
#             best_phrase = choice
#             best_idx = i
#     return (best_phrase, best_score, best_idx)


# rf_fuzz.token_set_ratio = _mock_token_set_ratio
# rf_process.extractOne = _mock_extract_one
# rf.fuzz = rf_fuzz
# rf.process = rf_process
# sys.modules["rapidfuzz"] = rf
# sys.modules["rapidfuzz.fuzz"] = rf_fuzz
# sys.modules["rapidfuzz.process"] = rf_process

# # ===========================================================================
# # Mock sentence_transformers
# # ===========================================================================
# st = types.ModuleType("sentence_transformers")


# class MockSentenceTransformer:
#     """Mock that returns random-ish but deterministic embeddings."""
#     def __init__(self, model_name: str):
#         self.model_name = model_name

#     def encode(self, texts, convert_to_numpy=True, show_progress_bar=False):
#         # Return deterministic embeddings based on text hash
#         result = []
#         for t in texts:
#             np.random.seed(hash(t) % (2**31))
#             result.append(np.random.randn(384).astype(np.float32))
#         return np.array(result)


# st.SentenceTransformer = MockSentenceTransformer
# sys.modules["sentence_transformers"] = st

# # ===========================================================================
# # Mock sklearn
# # ===========================================================================
# sk = types.ModuleType("sklearn")
# sk_pw = types.ModuleType("sklearn.metrics")
# sk_pw2 = types.ModuleType("sklearn.metrics.pairwise")


# def _mock_cosine_similarity(a, b):
#     """Real cosine similarity using numpy."""
#     dot = np.dot(a, b.T)
#     norm_a = np.linalg.norm(a, axis=1, keepdims=True)
#     norm_b = np.linalg.norm(b, axis=1, keepdims=True)
#     return dot / (norm_a * norm_b.T + 1e-10)


# sk_pw2.cosine_similarity = _mock_cosine_similarity
# sk_pw.pairwise = sk_pw2
# sk.metrics = sk_pw
# sys.modules["sklearn"] = sk
# sys.modules["sklearn.metrics"] = sk_pw
# sys.modules["sklearn.metrics.pairwise"] = sk_pw2

# # ===========================================================================
# # Now import the matcher
# # ===========================================================================
# from shared.schemas.report import (
#     FieldMatchScore,
#     MatchingResult,
#     NormalizedField,
#     NormalizationResult,
#     OCRResult,
#     OCRWord,
# )
# from pipeline_a.matching.matcher import (
#     _build_field_context,
#     _build_ocr_phrases,
#     run_matching,
# )

# # ===========================================================================
# # Test _build_field_context
# # ===========================================================================
# f1 = NormalizedField(
#     original_name="Hb", normalized_name="hemoglobin",
#     original_value="13.5", normalized_value="13.5",
#     unit="g/dL",
# )
# ctx = _build_field_context(f1)
# assert ctx == "hemoglobin 13.5 g/dL", f"Expected 'hemoglobin 13.5 g/dL', got '{ctx}'"
# print("✅ _build_field_context: 'hemoglobin 13.5 g/dL'")

# f2 = NormalizedField(
#     original_name="pcm", normalized_name="paracetamol",
#     original_value="500", normalized_value="500",
#     unit="mg",
# )
# assert _build_field_context(f2) == "paracetamol 500 mg"
# print("✅ _build_field_context: 'paracetamol 500 mg'")

# f3 = NormalizedField(
#     original_name="diag", normalized_name="diagnosis",
#     original_value="pneumonia", normalized_value="pneumonia",
#     unit=None,
# )
# assert _build_field_context(f3) == "diagnosis pneumonia"
# print("✅ _build_field_context: no unit → 'diagnosis pneumonia'")

# # ===========================================================================
# # Test _build_ocr_phrases
# # ===========================================================================
# phrases = _build_ocr_phrases("Hb 13.5 g/dL Normal range")
# assert len(phrases) > 5, f"Expected > 5 phrases, got {len(phrases)}"
# # Should contain 2-grams, 3-grams, etc. + unigrams
# assert "Hb 13.5" in phrases, "Should contain 2-gram 'Hb 13.5'"
# assert "Hb 13.5 g/dL" in phrases, "Should contain 3-gram"
# assert "Hb" in phrases, "Should contain unigram 'Hb'"
# assert "Normal" in phrases, "Should contain unigram 'Normal'"
# print(f"✅ _build_ocr_phrases: {len(phrases)} phrases (2-5 grams + unigrams)")

# # Edge: empty
# assert _build_ocr_phrases("") == []
# assert _build_ocr_phrases("   ") == []
# print("✅ _build_ocr_phrases: empty → []")

# # Verify deduplication
# phrases2 = _build_ocr_phrases("word word word")
# assert len(phrases2) == len(set(phrases2)), "Should be deduplicated"
# print("✅ _build_ocr_phrases: deduplicated")

# # ===========================================================================
# # Test run_matching (full pipeline)
# # ===========================================================================
# norm_result = NormalizationResult(fields=[
#     NormalizedField(
#         original_name="Hb", normalized_name="hemoglobin",
#         original_value="13.5", normalized_value="13.5",
#         unit="g/dL", reference_range="12.0-16.0",
#     ),
#     NormalizedField(
#         original_name="SGPT", normalized_name="alanine aminotransferase",
#         original_value="45", normalized_value="45",
#         unit="IU/L",
#     ),
# ])

# ocr_result = OCRResult(
#     raw_text="Patient: John Doe Hb 13.5 g/dL SGPT 45 IU/L Normal range 12.0-16.0",
#     words=[
#         OCRWord(text="Hb", confidence=0.95, bounding_box=[]),
#         OCRWord(text="13.5", confidence=0.92, bounding_box=[]),
#         OCRWord(text="g/dL", confidence=0.88, bounding_box=[]),
#         OCRWord(text="SGPT", confidence=0.90, bounding_box=[]),
#         OCRWord(text="45", confidence=0.91, bounding_box=[]),
#         OCRWord(text="IU/L", confidence=0.89, bounding_box=[]),
#     ],
#     avg_confidence=0.91,
#     low_confidence=False,
# )

# match_result = run_matching(norm_result, ocr_result, job_id="test-match-001")

# assert isinstance(match_result, MatchingResult)
# assert len(match_result.field_scores) == 2
# print(f"✅ run_matching: returned {len(match_result.field_scores)} field scores")

# # Check first field
# fs0 = match_result.field_scores[0]
# assert isinstance(fs0, FieldMatchScore)
# assert fs0.field_name == "hemoglobin"
# assert fs0.llm_value == "13.5"
# assert fs0.ocr_best_phrase != ""  # should have found a match
# assert 0 <= fs0.fuzzy_score <= 100
# assert 0 <= fs0.semantic_score <= 1.0
# assert 0 <= fs0.combined_score <= 1.0
# print(f"✅ field[0]: {fs0.field_name} → phrase='{fs0.ocr_best_phrase}' "
#       f"fuzzy={fs0.fuzzy_score} semantic={fs0.semantic_score:.4f} "
#       f"combined={fs0.combined_score:.4f}")

# # Check second field
# fs1 = match_result.field_scores[1]
# assert fs1.field_name == "alanine aminotransferase"
# assert fs1.llm_value == "45"
# assert fs1.ocr_best_phrase != ""
# print(f"✅ field[1]: {fs1.field_name} → phrase='{fs1.ocr_best_phrase}' "
#       f"fuzzy={fs1.fuzzy_score} combined={fs1.combined_score:.4f}")

# # Verify combined_score formula: 0.6 * (fuzzy/100) + 0.4 * semantic
# expected_combined = 0.6 * (fs0.fuzzy_score / 100.0) + 0.4 * fs0.semantic_score
# assert abs(fs0.combined_score - round(expected_combined, 4)) < 0.01, \
#     f"Combined score mismatch: {fs0.combined_score} vs {round(expected_combined, 4)}"
# print("✅ combined_score formula verified: 0.6*(fuzzy/100) + 0.4*semantic")

# # Uses ocr_best_phrase (not ocr_best_token)
# assert hasattr(fs0, "ocr_best_phrase")
# assert not hasattr(fs0, "ocr_best_token")
# print("✅ Uses ocr_best_phrase (NOT ocr_best_token)")

# # ===========================================================================
# # Test empty inputs
# # ===========================================================================
# empty1 = run_matching(NormalizationResult(fields=[]), ocr_result, "empty-test")
# assert len(empty1.field_scores) == 0
# print("✅ Empty fields → empty result")

# empty_ocr = OCRResult(raw_text="", words=[], avg_confidence=0.0, low_confidence=True)
# empty2 = run_matching(norm_result, empty_ocr, "empty-ocr")
# assert len(empty2.field_scores) == 0
# print("✅ Empty OCR → empty result")

# # ===========================================================================
# # Verify source code compliance
# # ===========================================================================
# source = Path("pipeline_a/matching/matcher.py").read_text()
# assert "build_phrase_windows" in source, "Must use build_phrase_windows from shared.utils.text"
# assert "token_set_ratio" in source, "Must use token_set_ratio scorer"
# assert "all-MiniLM-L6-v2" in source, "Must use all-MiniLM-L6-v2 model"
# assert "_get_embedding_model" in source, "Must have _get_embedding_model"
# assert "ocr_best_phrase" in source, "Must use ocr_best_phrase"
# assert "0.6" in source and "0.4" in source, "Must use 0.6/0.4 weights"
# assert "phrase_window_count" in source, "Must log phrase_window_count"
# assert "avg_fuzzy_score" in source, "Must log avg_fuzzy_score"
# assert "avg_semantic_score" in source, "Must log avg_semantic_score"
# print("✅ Source code compliance: all blueprint requirements present")

# print()
# print("✅ ALL MATCHER TESTS PASSED")
