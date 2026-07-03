# Vendored from ~/.aice/legalrag/pipeline/normalize.py (engine lane, 2026-07-02) on 2026-07-03; behavior locked byte-level by tests/golden/normalize_63.golden.json
"""matra — open Thai law data standard at the section (matra) level.

Public API: normalize_record(record) -> (docs, flags), the vendored,
behavior-identical replacement for the engine lane's normalize().

Task 4′.2 review Finding 3: also exports build_docs_merged(record) -> (docs,
flags, merge_report) — the single-merge-execution entry point a caller should
use when it needs the merge_report (e.g. for qa) instead of calling
normalize_record(record, merge=True) and separately re-deriving the report
via a second merge_amendments call (the double-merge bug this fixed).
"""
from .structure import build_docs as normalize_record
from .structure import build_docs_merged, toc_of
from .qa import qa_check
from .flat import FLAT_COLUMNS, enrich_docs, to_flat, work_expressions

__all__ = ["normalize_record", "build_docs_merged", "toc_of", "qa_check",
           "FLAT_COLUMNS", "enrich_docs", "to_flat", "work_expressions"]
