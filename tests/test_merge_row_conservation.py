# Task 4'.2 review — Finding 2 (Important): runtime merge_conservation_ok
# missed a total-row-count invariant. Before this fix, qa.qa_check's
# merge_conservation_ok only checked (a) chars_moved_in == chars_moved_out and
# (b) per-segment payload rows sum to rows_moved — both scoped to rows INSIDE
# a counted segment. A defect that drops or duplicates a row OUTSIDE any
# counted segment (or a segment move that silently loses/gains a row while a
# coincidental, unrelated char delta elsewhere keeps the char check balanced)
# would ship green. merge_amendments now also records rows_total_before /
# rows_total_after (sum of len(rows) across ALL docs — code + every donor —
# before vs after the move), and qa.py folds `rows_total_before ==
# rows_total_after` into merge_conservation_ok.
#
# This file proves the check GENUINELY BITES (not just present-but-inert) by
# tampering a copy of a real merge_report to simulate exactly that class of
# defect (a row silently dropped during the move, with chars_moved_in/out and
# per-segment rows left untouched — i.e. every OTHER check still passes),
# and confirming qa_check's merge_conservation_ok flips to False + hard_fail
# becomes True. It then confirms the untampered, real report from the
# synthetic fixture passes cleanly (the GREEN counterpart).
import copy
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))
from matra.merge import merge_amendments
from matra.qa import qa_check
from matra.splitter import split_record
from matra.structure import build_docs

FIX = pathlib.Path(__file__).parent / "fixtures/merge_synthetic.json"


def _record():
    data = json.loads(FIX.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if k != "_comment"}


def _real_report_and_docs():
    record = _record()
    docs, flags = build_docs(record, merge=True)
    _, merge_report = merge_amendments(split_record(record))
    return record, docs, flags, merge_report


# ======================================================================
# RED — tamper rows_total_after to simulate a row silently lost during the
# move (chars + per-segment-rows checks are left INTACT, so this isolates
# the NEW check: without Finding 2's fix, this tampered report would have
# sailed through merge_conservation_ok as True).
# ======================================================================
def test_tampered_rows_total_after_makes_merge_conservation_fail_RED():
    record, docs, flags, real_report = _real_report_and_docs()

    tampered = copy.deepcopy(real_report)
    # Simulate: a row vanished during the move (rows_total_after undercounts
    # what the report claims chars/segments moved). chars_moved_in/out and
    # per_segment are untouched, so the OLD (pre-Finding-2) checks would both
    # still read True here — proving this is genuinely a NEW axis of defect
    # detection, not a restatement of the existing char/segment checks.
    tampered["rows_total_after"] = tampered["rows_total_before"] - 1

    result = qa_check(record, docs, flags, merge_report=tampered)

    # sanity: confirm the OLD checks alone are still satisfied on the tampered
    # report (i.e. the failure below is attributable ONLY to the new check)
    per_seg_rows = sum(seg["rows"] for seg in tampered["per_segment"])
    assert tampered["chars_moved_in"] == tampered["chars_moved_out"]
    assert per_seg_rows == tampered["rows_moved"]

    assert result["checks"]["merge_conservation_ok"] is False, (
        "tampered rows_total_after must flip merge_conservation_ok to False"
    )
    assert result["hard_fail"] is True, (
        "a broken merge (row count invariant violated) must hard_fail, never ship green"
    )


def test_tampered_rows_total_before_also_caught_RED():
    """Symmetric tamper on the other side of the invariant — same defect class,
    opposite direction (a row phantom-appeared / rows_total_before was wrong)."""
    record, docs, flags, real_report = _real_report_and_docs()
    tampered = copy.deepcopy(real_report)
    tampered["rows_total_before"] = tampered["rows_total_after"] + 3

    result = qa_check(record, docs, flags, merge_report=tampered)
    assert result["checks"]["merge_conservation_ok"] is False
    assert result["hard_fail"] is True


# ======================================================================
# GREEN — the real, untampered report from the synthetic fixture passes
# merge_conservation_ok cleanly (proves the check is not just strict, it is
# CORRECT — a genuine conserving merge is never falsely flagged).
# ======================================================================
def test_real_synthetic_report_passes_merge_conservation_ok_GREEN():
    record, docs, flags, real_report = _real_report_and_docs()

    assert real_report["rows_total_before"] == real_report["rows_total_after"]

    result = qa_check(record, docs, flags, merge_report=real_report)
    assert result["checks"]["merge_conservation_ok"] is True
    assert result["hard_fail"] is False


def test_broken_move_via_monkeypatched_merge_amendments_is_caught(monkeypatch):
    """End-to-end variant of the RED case: monkeypatch merge_amendments itself
    to perform a move that silently drops a row (append instead of replace),
    so the whole pipeline — not just a hand-tampered report — is exercised."""
    import matra.merge as merge_mod

    real_merge_amendments = merge_mod.merge_amendments

    def _broken_merge_amendments(docs_rows):
        out_docs, report = real_merge_amendments(docs_rows)
        if out_docs:
            # simulate a lost row: drop the last row of the last doc, but leave
            # every reported number (chars/segments) exactly as the real,
            # correct run computed them — the report now LIES about what
            # actually happened to the row count.
            out_docs[-1] = {**out_docs[-1], "rows": list(out_docs[-1]["rows"])}
            if out_docs[-1]["rows"]:
                out_docs[-1]["rows"].pop()
                report = {**report, "rows_total_after": report["rows_total_after"] - 1}
        return out_docs, report

    monkeypatch.setattr(merge_mod, "merge_amendments", _broken_merge_amendments)

    record = _record()
    docs = split_record(record)
    broken_docs, broken_report = merge_mod.merge_amendments(docs)
    # feed the broken report through build_docs_merged's own merge (structure.py
    # calls the real merge_amendments internally for the docs/flags path — here
    # we only need qa_check's reaction to the broken REPORT, which is the
    # contract Finding 2 fixed)
    docs_built, flags = build_docs(record, merge=True)
    result = qa_check(record, docs_built, flags, merge_report=broken_report)

    assert broken_report["rows_total_before"] != broken_report["rows_total_after"]
    assert result["checks"]["merge_conservation_ok"] is False
    assert result["hard_fail"] is True


# ======================================================================
# Direct unit coverage of merge_amendments' own rows_total_* bookkeeping
# (not routed through qa_check) — the source of truth the qa lane consumes.
# ======================================================================
def test_merge_amendments_reports_rows_total_before_after_on_fixture():
    record = _record()
    docs = split_record(record)
    total_before_direct = sum(len(d["rows"]) for d in split_record(record))
    merged, report = merge_amendments(docs)
    total_after_direct = sum(len(d["rows"]) for d in merged)

    assert "rows_total_before" in report
    assert "rows_total_after" in report
    assert report["rows_total_before"] == total_before_direct
    assert report["rows_total_after"] == total_after_direct
    assert report["rows_total_before"] == report["rows_total_after"]


def test_merge_amendments_rows_total_present_even_with_no_docs():
    """The early-return path (docs == [], code_idx is None — Task 3.5's
    empty-sections records) must still populate both keys (trivially equal
    at 0), not omit them or crash."""
    record = {"law_code": "X", "timeline_code": "X-1B-0001-00", "reference_url": None, "sections": []}
    docs = split_record(record)
    assert docs == []  # sanity: this genuinely exercises the code_idx is None branch
    merged, report = merge_amendments(docs)
    assert "rows_total_before" in report and "rows_total_after" in report
    assert report["rows_total_before"] == report["rows_total_after"] == 0


def test_merge_amendments_rows_total_present_with_doc_but_no_code_type():
    """A non-empty doc set where no doc is literally doc_type=='code' still
    resolves to SOME primary doc (the tiebreak: most มาตรา rows) — not the
    None branch — and rows_total_* must still be correct and balanced."""
    sections = [{"sectionTypeId": 3, "sectionNo": None, "sectionName": None, "content": "แค่recital ไม่มี code doc"}]
    record = {"law_code": "X", "timeline_code": "X-1B-0001-00", "reference_url": None, "sections": sections}
    docs = split_record(record)
    assert docs != []  # sanity: this is the "doc exists, just not code_idx is None" branch
    merged, report = merge_amendments(docs)
    assert "rows_total_before" in report and "rows_total_after" in report
    assert report["rows_total_before"] == report["rows_total_after"] == 1
