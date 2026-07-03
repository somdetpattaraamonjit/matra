"""Shared canonicalizer used by BOTH the golden generator and the golden test.

get_normalizer() is the single seam that provides the normalizer used to
produce (docs, flags) from a record. It now returns the vendored, pure
`matra.normalize_record` — the repo stands alone with no dependency on the
engine lane outside the repo (~/.aice/legalrag/pipeline/normalize.py) at
runtime. Keep all normalizer-resolution logic inside this function only.
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))  # src/ hardening: resolve `matra` under plain `python3` too, not just pytest's pythonpath ini
import matra


def get_normalizer():
    """Return fn(record) -> (docs, flags), backed by the vendored package."""
    return matra.normalize_record


def canonicalize(docs, flags) -> bytes:
    """Deterministic byte serialization of a normalize() result.

    Pins the only nondeterministic field (provenance.ingested_at) to a fixed
    sentinel, then serializes with sorted keys and stable indentation so the
    same logical result always produces identical bytes.
    """
    docs = copy.deepcopy(docs)
    flags = copy.deepcopy(flags)
    for doc in docs:
        doc["provenance"]["ingested_at"] = "1970-01-01T00:00:00"
    payload = {"docs": docs, "flags": flags}
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
    return text.encode("utf-8")
