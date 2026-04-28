from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import boto3  # noqa: F401
except ImportError:
    boto3_stub = types.ModuleType("boto3")

    def _missing_client(*args, **kwargs):
        raise RuntimeError("boto3 is not installed in this test environment")

    boto3_stub.client = _missing_client
    sys.modules["boto3"] = boto3_stub
