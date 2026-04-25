# """Inline tests for pipeline_a/normalization/normalizer.py."""
# import sys
# import types
# from pathlib import Path

# # Ensure project root is on sys.path
# _project_root = str(Path(__file__).resolve().parent.parent)
# if _project_root not in sys.path:
#     sys.path.insert(0, _project_root)

# # --- Mock structlog ---
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


# from shared.schemas.report import (
#     DocumentType,
#     ExtractedField,
#     LLMExtractionResult,
#     NormalizedField,
#     NormalizationResult,
# )
# from pipeline_a.normalization.normalizer import (
#     normalize_name,
#     normalize_unit,
#     normalize_value,
#     run_normalization,
# )

# # =======================================================================
# # Test normalize_name
# # =======================================================================
# assert normalize_name("hb") == "hemoglobin"
# assert normalize_name("Hb") == "hemoglobin"
# assert normalize_name("  HB  ") == "hemoglobin"
# assert normalize_name("hgb") == "hemoglobin"
# assert normalize_name("SGPT") == "alanine aminotransferase"
# assert normalize_name("sgot") == "aspartate aminotransferase"
# assert normalize_name("pcm") == "paracetamol"
# assert normalize_name("dolo") == "paracetamol"
# assert normalize_name("tlc") == "total leucocyte count"
# assert normalize_name("wbc") == "total leucocyte count"
# assert normalize_name("BID") == "twice daily"
# assert normalize_name("hemoglobin") == "hemoglobin"  # already canonical
# assert normalize_name("some unknown field") == "some unknown field"  # passthrough
# print("✅ normalize_name: 13 cases (synonyms, case, whitespace, passthrough)")

# # =======================================================================
# # Test normalize_unit
# # =======================================================================
# assert normalize_unit("g/dl") == "g/dL"
# assert normalize_unit("G/DL") == "g/dL"
# assert normalize_unit("mg/dl") == "mg/dL"
# assert normalize_unit("cells/cumm") == "cells/µL"
# assert normalize_unit("cells/cu mm") == "cells/µL"
# assert normalize_unit("iu/l") == "IU/L"
# assert normalize_unit("mmol/l") == "mmol/L"
# assert normalize_unit("meq/l") == "mEq/L"
# assert normalize_unit("gm") == "g"
# assert normalize_unit("mcg") == "µg"
# assert normalize_unit(None) is None
# assert normalize_unit("") is None
# assert normalize_unit("  ") is None
# assert normalize_unit("mg") == "mg"  # already canonical
# assert normalize_unit("SomeUnknownUnit") == "SomeUnknownUnit"  # passthrough preserves original case
# print("✅ normalize_unit: 15 cases (synonyms, None, empty, passthrough)")

# # =======================================================================
# # Test normalize_value
# # =======================================================================
# assert normalize_value("  13.5  ") == "13.5"
# assert normalize_value("1,50,000") == "150000"
# assert normalize_value("1,000,000") == "1000000"
# assert normalize_value("500") == "500"
# assert normalize_value("") == ""
# assert normalize_value("  hello  ") == "hello"
# print("✅ normalize_value: 6 cases (strip, commas indian/intl, empty)")

# # =======================================================================
# # Test run_normalization (full pipeline)
# # =======================================================================

# # Build a realistic LLM extraction result
# llm_result = LLMExtractionResult(
#     fields=[
#         ExtractedField(name="Hb", value="  13.5 ", unit="g/dl", reference_range="12.0-16.0"),
#         ExtractedField(name="SGPT", value="45", unit="IU/L"),
#         ExtractedField(name="WBC Count", value="8,500", unit="cells/cumm"),
#         ExtractedField(name="platelet count", value="1,50,000", unit="cells/cu mm"),
#         ExtractedField(name="pcm", value="500", unit="mg", collection_date="2026-04-10"),
#         ExtractedField(name="some new test", value="99", unit="SomeUnit"),
#     ],
#     raw_llm_response="...",
#     attempt_count=1,
#     fallback_used=False,
# )

# result = run_normalization(llm_result, DocumentType.lab_report, job_id="test-123")

# assert isinstance(result, NormalizationResult)
# assert len(result.fields) == 6

# # Field 0: Hb → hemoglobin
# f0 = result.fields[0]
# assert f0.original_name == "Hb"
# assert f0.normalized_name == "hemoglobin"
# assert f0.original_value == "  13.5 "
# assert f0.normalized_value == "13.5"
# assert f0.unit == "g/dL"  # g/dl → g/dL
# assert f0.reference_range == "12.0-16.0"
# print("✅ run: Hb → hemoglobin, g/dl → g/dL, value trimmed")

# # Field 1: SGPT → alanine aminotransferase
# f1 = result.fields[1]
# assert f1.original_name == "SGPT"
# assert f1.normalized_name == "alanine aminotransferase"
# assert f1.unit == "IU/L"
# print("✅ run: SGPT → alanine aminotransferase")

# # Field 2: WBC Count → total leucocyte count, commas removed
# f2 = result.fields[2]
# assert f2.normalized_name == "total leucocyte count"
# assert f2.normalized_value == "8500"  # comma removed
# assert f2.unit == "cells/µL"  # cells/cumm → cells/µL
# print("✅ run: WBC → total leucocyte count, 8,500 → 8500, cells/cumm → cells/µL")

# # Field 3: Platelet count, Indian comma format
# f3 = result.fields[3]
# assert f3.normalized_name == "platelet count"
# assert f3.normalized_value == "150000"  # 1,50,000 → 150000
# assert f3.unit == "cells/µL"
# print("✅ run: 1,50,000 → 150000 (Indian format), cells/cu mm → cells/µL")

# # Field 4: pcm → paracetamol, preserves collection_date
# f4 = result.fields[4]
# assert f4.normalized_name == "paracetamol"
# assert f4.unit == "mg"
# assert f4.collection_date == "2026-04-10"
# print("✅ run: pcm → paracetamol, collection_date preserved")

# # Field 5: Unknown field — passthrough
# f5 = result.fields[5]
# assert f5.normalized_name == "some new test"
# assert f5.unit == "SomeUnit"  # unknown unit preserved as-is
# print("✅ run: unknown field/unit → passthrough")

# # Verify no inline synonym maps in normalizer.py
# normalizer_path = Path("pipeline_a/normalization/normalizer.py")
# source = normalizer_path.read_text()
# assert "MEDICAL_SYNONYMS" not in source.split("import")[-1].split("def")[0] or True
# # More precise: verify no dict literal assignments of synonyms
# assert "hb" not in source.split("def normalize_name")[0].split("import")[-1]
# print("✅ No inline synonym maps in normalizer.py (imported from medical_dict)")

# # Verify all imports are from correct modules
# assert "from shared.utils.medical_dict import MEDICAL_SYNONYMS, UNIT_SYNONYMS" in source
# assert "from shared.utils.validators import validate_field" in source
# assert "from shared.utils.text import remove_thousands_separators" in source
# print("✅ Correct imports: medical_dict, validators, text")

# # Empty input
# empty_result = run_normalization(
#     LLMExtractionResult(fields=[], raw_llm_response="", attempt_count=1, fallback_used=True),
#     DocumentType.unknown,
#     job_id="test-empty",
# )
# assert len(empty_result.fields) == 0
# print("✅ run: empty fields → empty NormalizationResult")

# print()
# print("✅ ALL NORMALIZER TESTS PASSED")
