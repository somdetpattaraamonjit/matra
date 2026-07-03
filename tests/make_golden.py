#!/usr/bin/env python3
"""One-time generator for tests/golden/normalize_63.golden.json.

Loads the fixture row whose timeline_code ends with "-63" from
tests/fixtures/criminal_code_sample.jsonl, runs it through get_normalizer(),
and writes the canonical bytes to the golden file. Committed for provenance —
re-run only when the intended behavior changes on purpose (a deliberate
golden update), never to paper over an unexplained drift.

Provenance: the golden bytes were ORIGINALLY generated (Task 3'.1) against
the engine lane at ~/.aice/legalrag/pipeline/normalize.py. As of the Task
3'.2 vendoring, get_normalizer() resolves to the vendored src/matra package
instead — running this script now regenerates against the vendored, pure
functions, not the external engine file. The bytes are unchanged
(SHA256-verified byte-identical) because the vendoring was behavior-locked
against this same golden file.

Usage: python3 tests/make_golden.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))  # tests-dir hardening: resolve `canon` regardless of invocation cwd
from canon import canonicalize, get_normalizer

FIX = pathlib.Path(__file__).parent / "fixtures/criminal_code_sample.jsonl"
GOLDEN = pathlib.Path(__file__).parent / "golden/normalize_63.golden.json"


def _row_63():
    rows = [json.loads(l) for l in FIX.read_text(encoding="utf-8").splitlines() if l.strip()]
    return next(r for r in rows if r["timeline_code"].endswith("-63"))


def main():
    normalize = get_normalizer()
    docs, flags = normalize(_row_63())
    payload = canonicalize(docs, flags)
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_bytes(payload)
    print(f"wrote {len(payload)} bytes to {GOLDEN}")


if __name__ == "__main__":
    main()
