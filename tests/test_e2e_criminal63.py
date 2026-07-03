# Task 4′.3 — end-to-end run of the full Thai Criminal Code -63 through the
# complete Matra pipeline WITH the merge engine, as an in-process, corpus-
# guarded pytest (the `@requires_corpus` pattern from tests/test_merge.py) so
# the repo suite stays green on machines without the raw corpus while still
# being fully repo-testable wherever the corpus exists.
#
# This does NOT shell out to docs/run_e2e_criminal63.py (that script is the
# reproducible artifact-producing runner for the daily-progress deliverable);
# instead it calls build_docs_merged + qa_check directly, in-process, and
# asserts the SAME golden numbers the runner validates — a second, independent
# path to the same truth (mirrors tests/test_merge.py's existing style).
import json
import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))
from jsonschema import Draft202012Validator

from matra.structure import build_docs_merged, toc_of
from matra.qa import qa_check, primary_doc


def _resolve_corpus():
    """Locate the raw -63 corpus (1956-11.jsonl) portably — no machine-specific
    session path hard-coded (Task 4'.2 review Finding 2). Resolution order:
      1. env MATRA_CORPUS — a path to 1956-11.jsonl OR a directory holding it;
      2. ~/.aice/legalrag/raw/1956-11.jsonl — the standard local engine layout;
      3. glob /sessions/*/mnt/.aice/legalrag/raw/1956-11.jsonl — any Cowork
         session mount (portable across future session names, not just this one).
    Returns the first existing path, or a non-existent sentinel so
    `requires_corpus` cleanly skips corpus tests where none is present.
    """
    env = os.environ.get("MATRA_CORPUS")
    if env:
        p = pathlib.Path(env)
        if p.is_dir():
            p = p / "1956-11.jsonl"
        if p.exists():
            return p
    home = pathlib.Path.home() / ".aice/legalrag/raw/1956-11.jsonl"
    if home.exists():
        return home
    for match in sorted(pathlib.Path("/sessions").glob("*/mnt/.aice/legalrag/raw/1956-11.jsonl")):
        if match.exists():
            return match
    return home  # non-existent standard path → skipif triggers


RAW = _resolve_corpus()
requires_corpus = pytest.mark.skipif(not RAW.exists(), reason="raw -63 corpus not present on this machine")

TIMELINE_CODE = "ป0006-1D-0003-63"
REPO_ROOT = pathlib.Path(__file__).parents[1]
SCHEMA = json.loads((REPO_ROOT / "schemas" / "matra-0.2.json").read_text(encoding="utf-8"))

EXPECTED_TOC_COUNTS = {"phak": 3, "laksana": 16, "muad": 37, "suan": 3}
EXPECTED_DOC_COUNT = 34

# matra_range values are Thai-digit verbatim (toc_of() builds them from
# node["number"], the schema's verbatim field — see schemas/matra-0.2.json
# "'๙๐/๑' style kept verbatim; arabic mirror in number_arabic").
EXPECTED_MERGED_STRUCTURES = [
    {"heading_contains": "ก่อการร้าย", "level": "laksana", "matra_range": "๑๓๕/๑–๑๓๕/๔"},
    {"heading_contains": "บัตรอิเล็กทรอนิกส์", "level": "muad", "matra_range": "๒๖๙/๑–๒๖๙/๗"},
    {"heading_contains": "หนังสือเดินทาง", "level": "muad", "matra_range": "๒๖๙/๘–๒๖๙/๑๕"},
    {"heading_contains": "ศพ", "level": "laksana", "matra_range": "๓๖๖/๑–๓๖๖/๔"},
]

DIGIT_DEFECT_SECTION_ID = 6466038


def _row_63_record():
    rows = [json.loads(l) for l in RAW.read_text(encoding="utf-8").splitlines() if l.strip()]
    return next(r for r in rows if r["timeline_code"] == TIMELINE_CODE)


# ======================================================================
# Golden: whole-record raw census (docs/merge_answer_key.md +
# private data-audit evidence (2026-07-02)).
# ======================================================================
@requires_corpus
def test_raw_record_census_matches_golden():
    from collections import Counter
    record = _row_63_record()
    assert len(record["sections"]) == 1031
    c = Counter(s.get("sectionTypeId") for s in record["sections"])
    assert c.get(6, 0) == EXPECTED_TOC_COUNTS["phak"]
    assert c.get(7, 0) == EXPECTED_TOC_COUNTS["laksana"]
    assert c.get(8, 0) == EXPECTED_TOC_COUNTS["muad"]
    assert c.get(9, 0) == EXPECTED_TOC_COUNTS["suan"]
    assert c.get(1, 0) == EXPECTED_DOC_COUNT


# ======================================================================
# Golden: full pipeline via build_docs_merged (single execution, same API
# the CLI uses) -> every doc validates against schemas/matra-0.2.json.
# ======================================================================
@requires_corpus
def test_e2e_docs_validate_against_schema():
    record = _row_63_record()
    docs, flags, merge_report = build_docs_merged(record)
    assert len(docs) == EXPECTED_DOC_COUNT
    validator = Draft202012Validator(SCHEMA)
    errors = []
    for i, doc in enumerate(docs):
        for err in validator.iter_errors(doc):
            errors.append(f"doc[{i}] doc_id={doc.get('doc_id')!r}: {err.message}")
    assert errors == [], f"{len(errors)} schema errors:\n" + "\n".join(errors[:10])


# ======================================================================
# Golden: qa verdict PASS, merge_conservation_ok True, DEFECT#8 fully closed.
# ======================================================================
@requires_corpus
def test_e2e_qa_verdict_pass_and_merge_conservation_ok():
    record = _row_63_record()
    docs, flags, merge_report = build_docs_merged(record)
    result = qa_check(record, docs, flags, merge_report=merge_report)
    checks, hard_fail = result["checks"], result["hard_fail"]

    assert hard_fail is False, f"hard_fail True; checks={checks}"
    assert checks["merge_conservation_ok"] is True
    assert checks["unmerged_amendment_structures"] == 0
    assert checks["merge"]["segments_applied"] == 4
    assert checks["merge"]["segments_quarantined"] == 0


# ======================================================================
# Golden: post-merge code-doc TOC counts == whole-record census, and the 4
# merged structures present, correctly parented, with correct มาตรา ranges.
# ======================================================================
@requires_corpus
def test_e2e_post_merge_toc_matches_census_and_4_structures_placed():
    record = _row_63_record()
    docs, flags, merge_report = build_docs_merged(record)
    code = primary_doc(docs)
    toc = toc_of(code)

    toc_counts = {"phak": 0, "laksana": 0, "muad": 0, "suan": 0}
    for entry in toc:
        if entry["level"] in toc_counts:
            toc_counts[entry["level"]] += 1
    assert toc_counts == EXPECTED_TOC_COUNTS, f"TOC counts {toc_counts} != census {EXPECTED_TOC_COUNTS}"

    for target in EXPECTED_MERGED_STRUCTURES:
        matches = [e for e in toc if target["heading_contains"] in (e["heading"] or "")]
        assert len(matches) == 1, f"{target['heading_contains']!r}: expected 1 TOC match, got {len(matches)}"
        entry = matches[0]
        assert entry["level"] == target["level"], (
            f"{target['heading_contains']!r}: level {entry['level']} != {target['level']}")
        assert entry["matra_range"] == target["matra_range"], (
            f"{target['heading_contains']!r}: matra_range {entry['matra_range']!r} != {target['matra_range']!r}")


# ======================================================================
# Bot check: does -63 contain typeId 13 (บทเฉพาะกาล)? Live-verified: no —
# record this fact rather than assume from memory (Berkson rule: log the
# invisible, never guess). If a future corpus refresh DOES introduce typeId
# 13, this test must be revisited (it would then need a 'bot' TOC assertion
# instead of an absence assertion) — not silently loosened.
# ======================================================================
@requires_corpus
def test_e2e_bot_check_typeid_13_absent_in_63():
    from collections import Counter
    record = _row_63_record()
    c = Counter(s.get("sectionTypeId") for s in record["sections"])
    assert c.get(13, 0) == 0, (
        "typeId 13 (บทเฉพาะกาล) now present in -63 — this test's absence "
        "assumption is stale; add a 'bot' TOC-entry assertion instead of "
        "asserting absence (see docs/run_e2e_criminal63.py bot check)."
    )
    docs, flags, merge_report = build_docs_merged(record)
    code = primary_doc(docs)
    toc = toc_of(code)
    assert not any(e["level"] == "bot" for e in toc)


# ======================================================================
# Digit-fidelity Known Defect (merge_answer_key.md §Deliverable 3): sectionId
# 6466038's structural (typeId 7) row reads sectionNo "1" but the record's
# own source_toc (sectionId 6465658) independently calls the same section
# "ลักษณะ ๑๒". Data must remain unmutated — this test asserts the defect is
# still there (a "fix" that silently corrects it without updating the answer
# key and this test would be a scope violation, not a bugfix).
# ======================================================================
@requires_corpus
def test_e2e_digit_fidelity_known_defect_recorded_not_mutated():
    record = _row_63_record()
    target = next(s for s in record["sections"] if s.get("sectionId") == DIGIT_DEFECT_SECTION_ID)
    assert target["sectionTypeId"] == 7
    assert target["sectionNo"] == "1", (
        "digit-fidelity Known Defect sectionNo has changed from the documented "
        "\"1\" — re-verify against docs/merge_answer_key.md §Deliverable 3 "
        "before updating this assertion; do not silently adjust."
    )
    # independent cross-check: the record's own (pipeline-discarded) source_toc
    # (sectionId 6465658, sectionTypeId 16) independently calls the SAME
    # section "ลักษณะ ๑๒" — confirming this is a genuine source-data defect.
    # source_toc is a LONG text split across multiple raw rows sharing the
    # same sectionId (contentNo 1..9 here, ~2,417 chars joined) — the "ลักษณะ
    # ๑๒" substring only appears once the rows are joined in contentNo order
    # (found empirically: joining reveals it at offset 2007, right after
    # "...หมิ่นประมาท๓๒๖-๓๓๓" and before "ความผิดเกี่ยวกับทรัพย์ หมวด ๑...").
    # A single-row content check would miss this (row contentNo=1 alone cuts
    # off mid-sentence at "...หมวด ๔" and never reaches ลักษณะ ๑๒).
    toc_rows = [s for s in record["sections"] if s.get("sectionId") == 6465658]
    assert len(toc_rows) >= 1 and all(s["sectionTypeId"] == 16 for s in toc_rows)
    full_toc_text = "".join(s["content"] for s in sorted(toc_rows, key=lambda s: s["contentNo"]))
    assert "ลักษณะ ๑๒ ความผิดเกี่ยวกับทรัพย์" in full_toc_text
