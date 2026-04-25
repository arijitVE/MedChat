# tests/pipeline_a/conftest.py
import sys, types

def _install_structlog_mock():
    ms = types.ModuleType("structlog")
    # ... (the mock body, once, shared)
    sys.modules["structlog"] = ms

_install_structlog_mock()