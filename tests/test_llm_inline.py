# """Inline tests for pipeline_a/llm_extraction/ modules."""
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

# from shared.schemas.report import ExtractedField, DocumentType
# from pathlib import Path

# # =======================================================================
# # Test fallback.py
# # =======================================================================
# from pipeline_a.llm_extraction.fallback import regex_extract

# lab_text = """
# Patient: John Doe
# Hemoglobin: 13.5 g/dL
# WBC Count: 8500 cells/cumm
# Platelet Count: 150000 cells/cumm
# Blood Sugar: 95 mg/dL
# SGPT: 45 IU/L
# Creatinine: 1.2 mg/dL
# """
# fields = regex_extract(lab_text, DocumentType.lab_report)
# assert len(fields) >= 4, f"Expected >= 4 fields, got {len(fields)}: {[f.name for f in fields]}"
# names = [f.name for f in fields]
# assert any("hemoglobin" in n for n in names)
# assert any("sgpt" in n for n in names)
# assert all(isinstance(f, ExtractedField) for f in fields)
# print(f"✅ fallback: lab report → {len(fields)} fields")

# rx_text = "Tab. Amoxicillin 500mg 1-0-1, Cap Pantoprazole 40mg OD"
# rx_fields = regex_extract(rx_text, DocumentType.prescription)
# assert len(rx_fields) >= 2, f"Expected >= 2 rx fields, got {len(rx_fields)}"
# print(f"✅ fallback: prescription → {len(rx_fields)} fields")

# assert regex_extract("", DocumentType.lab_report) == []
# assert regex_extract("Hello world", DocumentType.lab_report) == []
# print("✅ fallback: empty/no-match → []")

# # =======================================================================
# # Test parser.py
# # =======================================================================
# from pipeline_a.llm_extraction.parser import parse_llm_response, strip_markdown_fences

# # Clean JSON array
# raw = '[{"name": "hemoglobin", "value": "13.5", "unit": "g/dL"}]'
# f1 = parse_llm_response(raw)
# assert len(f1) == 1 and f1[0].name == "hemoglobin"
# print("✅ parser: clean JSON → 1 field")

# # Markdown fenced
# fenced = '```json\n[{"name": "wbc", "value": "8500"}]\n```'
# f2 = parse_llm_response(fenced)
# assert len(f2) == 1 and f2[0].name == "wbc"
# print("✅ parser: markdown fenced → parsed")

# # Preamble text
# preamble = 'Here are the results:\n[{"name": "plt", "value": "150000"}]'
# f3 = parse_llm_response(preamble)
# assert len(f3) == 1 and f3[0].name == "plt"
# print("✅ parser: preamble stripped → parsed")

# # Single object
# single = '{"name": "hb", "value": "12.0", "unit": "g/dL"}'
# f4 = parse_llm_response(single)
# assert len(f4) == 1
# print("✅ parser: single object → list")

# # Fields wrapper
# wrapper = '{"fields": [{"name": "a", "value": "1"}, {"name": "b", "value": "2"}]}'
# f5 = parse_llm_response(wrapper)
# assert len(f5) == 2
# print('✅ parser: {"fields": [...]} → unwrapped')

# # Trailing comma
# trailing = '[{"name": "x", "value": "1",}]'
# f6 = parse_llm_response(trailing)
# assert len(f6) == 1
# print("✅ parser: trailing comma → fixed")

# # Missing required fields
# missing = '[{"name": "good", "value": "1"}, {"foo": "bar"}]'
# f7 = parse_llm_response(missing)
# assert len(f7) == 1 and f7[0].name == "good"
# print("✅ parser: missing name/value → skipped")

# # Empty/invalid
# assert parse_llm_response("") == []
# assert parse_llm_response("   ") == []
# assert parse_llm_response("not json") == []
# print("✅ parser: empty/invalid → []")

# # Multiple with optionals
# multi = """[
#   {"name": "hemoglobin", "value": "13.5", "unit": "g/dL", "reference_range": "12.0-16.0", "collection_date": "2026-04-10"},
#   {"name": "wbc", "value": "8500", "unit": "cells/uL"}
# ]"""
# f8 = parse_llm_response(multi)
# assert len(f8) == 2
# assert f8[0].reference_range == "12.0-16.0"
# assert f8[0].collection_date == "2026-04-10"
# assert f8[1].reference_range is None
# print("✅ parser: optionals handled")

# # strip_markdown_fences
# assert strip_markdown_fences("```json\n[1,2,3]\n```") == "[1,2,3]"
# assert strip_markdown_fences("```\n{\"a\":1}\n```") == '{"a":1}'
# assert strip_markdown_fences("Hello\n[1,2]") == "[1,2]"
# assert strip_markdown_fences("") == ""
# print("✅ strip_markdown_fences: all cases")

# # Prompt template
# p = Path("pipeline_a/llm_extraction/prompts/prescription_prompt.txt")
# assert p.exists()
# content = p.read_text()
# assert "JSON" in content and "name" in content and len(content) > 200
# print(f"✅ prescription_prompt.txt ({len(content)} chars)")

# print()
# print("✅ ALL LLM EXTRACTION MODULE TESTS PASSED")
