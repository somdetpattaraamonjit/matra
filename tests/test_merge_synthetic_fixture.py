# Task 4'.2 review — Finding 1 (Critical): merge=True had ZERO portable test
# coverage. Every successful-placement assertion in tests/test_merge.py is
# @requires_corpus (out-of-tree 19MB raw file), so on a machine without that
# corpus the merge algorithm's core placement logic (slash/plain anchor rules,
# sequence-consistency discrimination, quarantine fallback) was NEVER exercised.
#
# This file is fully portable — no skipif, no corpus dependency — built on a
# small (40-row) hand-designed multi-doc fixture committed at
# tests/fixtures/merge_synthetic.json.
#
# ============================================================================
# FIXTURE LAYOUT SKETCH (hand-derivable — read this before touching the JSON)
# ============================================================================
#
# CODE DOC (doc index 0, doc_type="code"):
#   title: "ประมวลกฎหมายทดสอบ"
#   ภาค ๑ ทั่วไป
#     ลักษณะ ๑ ทั่วไป                    <- NOT the amendment target ภาค; its
#                                            existing max ลักษณะ base (1) is
#                                            lower than ภาค ๒'s (2), so
#                                            _phak_with_highest_laksana always
#                                            resolves to ภาค ๒, never ภาค ๑.
#       มาตรา ๕๐, ๕๑, ๕๒ (padding, no donor ever targets this span)
#   ภาค ๒ ความผิด                        <- the REAL scope for all 3 donors
#     ลักษณะ ๑ มั่นคง                     <- REAL candidate for donor (a)'s
#                                            slash ลักษณะ ๑/๑ insert: its own
#                                            NEXT sibling is literally
#                                            ลักษณะ ๒ (base+1) -> sequence_ok=True
#       หมวด ๑ กบฏ
#         มาตรา ๑๐๐ (+ a synthetic วรรคสอง continuation row, same sectionNo,
#                     folds into paragraphs by structure.py's matra-merge rule
#                     — proves padding never perturbs anchor math)
#       หมวด ๒ ก่อความไม่สงบ               <- N-1 anchor for donor (b)'s
#                                            plain หมวด ๓ (continuation_muad):
#                                            หมวด (๓-๑=๒) found as a direct
#                                            sibling inside THIS ลักษณะ (๑)
#         มาตรา ๑๐๑
#     ลักษณะ ๒ ปกครอง                     <- highest EXISTING ลักษณะ (base 2)
#                                            in the code doc -> pins the ภาค
#                                            that donor (c)'s plain ลักษณะ ๔
#                                            falls back into.
#       มาตรา ๑๕๐ (+ วรรคสอง continuation), ๑๕๑
#     ลักษณะ ๑ เดคอย-ผิดลำดับ              <- *** THE DECOY ***. Same base (1)
#                                            as the real มั่นคง candidate,
#                                            SAME ภาค ๒ scope, but its own next
#                                            sibling does not exist inside
#                                            ภาค ๒ (it is the last ลักษณะ) so
#                                            sequence_ok=False for it — proving
#                                            the sequence-consistency check
#                                            genuinely discriminates between
#                                            two same-numbered candidates in
#                                            the same scope, not just picks
#                                            "the first one it sees".
#       มาตรา ๑๖๐, ๑๖๑
#
# DONOR (a) — doc index 1 — forces `slash:sequence_consistent`:
#   title: "พระราชบัญญัติแก้ไข (ก) ก่อการร้าย"
#   recital + มาตรา ๑ + มาตรา ๒ (pre-heading boilerplate — never enters a
#     segment; _find_segments only starts a segment at the FIRST heading row)
#   ลักษณะ ๑/๑ ก่อการร้าย   <- slash number 1/1. Scope = the ภาค whose มาตรา
#                              span contains the segment's first payload base
#                              (100, from มาตรา ๑๐๐/๑ below) = ภาค ๒. Within
#                              that scope, TWO ลักษณะ ๑ headings exist (มั่นคง
#                              and the decoy); only มั่นคง is sequence-
#                              consistent (next sibling literally ลักษณะ ๒) ->
#                              unambiguous single sequence-consistent pick.
#     มาตรา ๑๐๐/๑, ๑๐๐/๒        <- payload; first base = 100, pins scope above
#   countersign (never part of any segment; sits after the last matra row)
#
# DONOR (b) — doc index 2 — forces `plain:continuation_muad`:
#   title: "พระราชบัญญัติแก้ไข (ข) หมวด ๓"
#   recital + มาตรา ๓ (pre-heading boilerplate)
#   หมวด ๓ ก่อวินาศกรรม     <- plain number 3. Payload base = 101 (from
#                              มาตรา ๑๐๑/๑) -> anchors the scope to the
#                              ลักษณะ whose มาตรา span contains 101 = ลักษณะ ๑
#                              มั่นคง (spans 100-101 incl. the already-applied
#                              donor-a payload, but even pre-merge the code's
#                              OWN มาตรา ๑๐๐/๑๐๑ already bracket it). Looks for
#                              หมวด numbered 3-1=2 inside that ลักษณะ -> finds
#                              หมวด ๒ ก่อความไม่สงบ -> inserts right after it.
#     มาตรา ๑๐๑/๑              <- payload; first base = 101, pins scope above
#   countersign
#
# DONOR (c) — doc index 3 — forces `plain:end_of_phak_fallback`:
#   title: "พระราชบัญญัติแก้ไข (ค) ลักษณะ ๔"
#   recital + มาตรา ๔ (pre-heading boilerplate)
#   ลักษณะ ๔ ศพ              <- plain number 4. _phak_with_highest_laksana
#                              picks ภาค ๒ (its existing max ลักษณะ base = 2,
#                              higher than ภาค ๑'s 1). Looks for ลักษณะ
#                              numbered 4-1=3 as a DIRECT sibling inside ภาค ๒
#                              -> none exists (only ๑, ๒, and the decoy ๑) ->
#                              falls back to inserting at the END of ภาค ๒'s
#                              span (== end of code doc here), which is
#                              exactly the `end_of_phak_fallback` rule label.
#     มาตรา ๒๐๐
#   countersign
#
# Merge order is by ascending donor doc index (a, then b, then c) — matches
# `merge_amendments`' donor_indices loop, which processes chronological ฉบับ
# order so a later donor can anchor against an earlier donor's already-merged
# structure (not needed here since each donor's scope pin is independent, but
# the ordering is asserted via TOC order below regardless).
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))
from matra.merge import merge_amendments
from matra.qa import qa_check
from matra.splitter import split_record
from matra.structure import build_docs, toc_of

FIX = pathlib.Path(__file__).parent / "fixtures/merge_synthetic.json"


def _record():
    data = json.loads(FIX.read_text(encoding="utf-8"))
    data = {k: v for k, v in data.items() if k != "_comment"}
    return data


def _arab(s):
    th = "๐๑๒๓๔๕๖๗๘๙"
    tr = {c: str(i) for i, c in enumerate(th)}
    return None if s is None else "".join(tr.get(c, c) for c in s)


# ======================================================================
# Core placement test — all 3 anchor rules, correct labels, decoy excluded,
# correct row order (via TOC / row-index order), conservation, idempotence.
# ======================================================================
def test_all_three_segments_applied_with_expected_rule_labels():
    record = _record()
    docs = split_record(record)
    merged, report = merge_amendments(docs)

    assert report["segments_found"] == 3
    assert report["segments_applied"] == 3
    assert report["segments_quarantined"] == 0

    rules_by_heading = {seg["heading"]: seg["anchor_rule"] for seg in report["per_segment"]}
    assert rules_by_heading["ลักษณะ ๑/๑ ก่อการร้าย"] == "slash:sequence_consistent"
    assert rules_by_heading["หมวด ๓ ก่อวินาศกรรม"] == "plain:continuation_muad"
    assert rules_by_heading["ลักษณะ ๔ ศพ"] == "plain:end_of_phak_fallback"


def test_decoy_laksana_never_chosen_as_slash_anchor():
    """The mislabeled ลักษณะ ๑ decoy (same base, same ภาค ๒ scope, but its own
    next sibling is not base+1) must never be the anchor for donor (a)'s slash
    insert — the sequence-consistency check must discriminate against it."""
    record = _record()
    docs = split_record(record)
    merged, report = merge_amendments(docs)
    code = next(d for d in merged if d["doc_type"] == "code")

    lak_headings = [(r["raw_type"], _arab(r["no"]), r["c"]) for r in code["rows"] if r["raw_type"] == 7]
    # exactly 2 headings literally numbered "1" survive (มั่นคง + the decoy) — the slash
    # insert (1/1) landed between มั่นคง and ลักษณะ ๒, NOT adjacent to the decoy.
    idx_1_1 = next(i for i, (t, no, c) in enumerate(lak_headings) if no == "1/1")
    assert "ก่อการร้าย" in lak_headings[idx_1_1][2]
    assert lak_headings[idx_1_1 - 1][1] == "1" and "มั่นคง" in lak_headings[idx_1_1 - 1][2], (
        f"slash insert must land immediately after มั่นคง, got sequence={lak_headings}"
    )
    assert lak_headings[idx_1_1 + 1][1] == "2" and "ปกครอง" in lak_headings[idx_1_1 + 1][2]
    # the decoy is still present, unmoved, further down — never touched by the merge
    decoy = [h for h in lak_headings if h[1] == "1" and "เดคอย" in h[2]]
    assert len(decoy) == 1, f"decoy heading missing or duplicated: {lak_headings}"


def test_placements_at_correct_row_indices_via_toc_order():
    """Placements assert via TOC order (structural-heading sequence), per the
    task's placement-correctness requirement — not raw row index numbers,
    which are an implementation detail of how many padding rows precede them."""
    record = _record()
    docs, flags = build_docs(record, merge=True)
    code = next(d for d in docs if d["doc_type"] == "code")
    toc = toc_of(code)

    headings_in_order = [t["heading"] for t in toc]
    # ภาค ๑ / ลักษณะ ๑ (ทั่วไป, untouched) come first, unaffected by any donor.
    assert headings_in_order[0] == "ภาค ๑ ทั่วไป"
    assert headings_in_order[1] == "ลักษณะ ๑ ทั่วไป"
    # ภาค ๒ subtree in the exact expected consolidated order:
    # ลักษณะ ๑ มั่นคง, หมวด ๑ กบฏ, หมวด ๒ ก่อความไม่สงบ, หมวด ๓ ก่อวินาศกรรม (b),
    # ลักษณะ ๑/๑ ก่อการร้าย (a), ลักษณะ ๒ ปกครอง, ลักษณะ ๑ เดคอย (untouched, last),
    # ลักษณะ ๔ ศพ (c, end-of-ภาค fallback — inserted at the very end of ภาค ๒).
    idx = headings_in_order.index
    assert idx("ภาค ๒ ความผิด") < idx("ลักษณะ ๑ มั่นคง") < idx("หมวด ๑ กบฏ") < idx("หมวด ๒ ก่อความไม่สงบ")
    assert idx("หมวด ๒ ก่อความไม่สงบ") < idx("หมวด ๓ ก่อวินาศกรรม") < idx("ลักษณะ ๑/๑ ก่อการร้าย")
    assert idx("ลักษณะ ๑/๑ ก่อการร้าย") < idx("ลักษณะ ๒ ปกครอง") < idx("ลักษณะ ๑ เดคอย-ผิดลำดับ")
    # ลักษณะ ๔ ศพ is the LAST heading overall (end-of-ภาค ๒ fallback == end of doc here)
    assert headings_in_order[-1] == "ลักษณะ ๔ ศพ"


def test_matra_payload_present_under_correct_new_containers():
    record = _record()
    docs, flags = build_docs(record, merge=True)
    code = next(d for d in docs if d["doc_type"] == "code")

    by_number = {n["number_arabic"]: n for n in code["structure"] if n["node_type"] == "matra"}
    for want in ["100/1", "100/2", "101/1", "200"]:
        assert want in by_number, f"payload มาตรา {want} missing from code doc after merge"

    parents = {n["node_id"]: n for n in code["structure"]}
    lak_1_1 = next(n for n in code["structure"] if n["node_type"] == "laksana" and n["number_arabic"] == "1/1")
    assert parents[by_number["100/1"]["parent_id"]]["node_id"] == lak_1_1["node_id"]
    assert parents[by_number["100/2"]["parent_id"]]["node_id"] == lak_1_1["node_id"]

    muad_3 = next(n for n in code["structure"] if n["node_type"] == "muad" and n["number_arabic"] == "3")
    assert parents[by_number["101/1"]["parent_id"]]["node_id"] == muad_3["node_id"]

    lak_4 = next(n for n in code["structure"] if n["node_type"] == "laksana" and n["number_arabic"] == "4")
    assert parents[by_number["200"]["parent_id"]]["node_id"] == lak_4["node_id"]


def test_conservation_balanced_on_synthetic_fixture():
    record = _record()
    docs = split_record(record)
    total_before = sum(len(d["rows"]) for d in split_record(record))
    merged, report = merge_amendments(docs)
    total_after = sum(len(d["rows"]) for d in merged)

    assert report["chars_moved_in"] == report["chars_moved_out"]
    per_seg_rows = sum(seg["rows"] for seg in report["per_segment"])
    assert per_seg_rows == report["rows_moved"]
    assert total_after == total_before, f"row conservation broken: {total_before} -> {total_after}"

    # donor docs post-merge hold no structural headings (everything applied, none quarantined)
    donor_headings = [n for d in merged if d["doc_type"] != "code"
                      for n in d["rows"] if n["raw_type"] in (7, 8, 9)]
    assert donor_headings == []


def test_idempotent_on_rerun():
    """Re-running merge_amendments on an already-merged result is a no-op —
    no segments left to find (donors hold only boilerplate now), row totals
    unchanged, PIPELINE.md design law #6 (idempotent + provenance)."""
    record = _record()
    docs = split_record(record)
    merged_once, _ = merge_amendments(docs)
    total_once = sum(len(d["rows"]) for d in merged_once)

    merged_twice, report_twice = merge_amendments(merged_once)
    total_twice = sum(len(d["rows"]) for d in merged_twice)

    assert report_twice["segments_found"] == 0
    assert report_twice["segments_applied"] == 0
    assert total_twice == total_once
    assert json.loads(json.dumps(merged_twice)) == json.loads(json.dumps(merged_once))


def test_qa_check_merge_conservation_ok_true_on_synthetic_fixture():
    record = _record()
    docs, flags = build_docs(record, merge=True)
    _, merge_report = merge_amendments(split_record(record))
    result = qa_check(record, docs, flags, merge_report=merge_report)

    assert result["checks"]["merge"]["segments_applied"] == 3
    assert result["checks"]["merge_conservation_ok"] is True
    assert result["checks"]["unmerged_amendment_structures"] == 0
    assert result["hard_fail"] is False


# ======================================================================
# Task 4'.2 review — Finding 1 (Important): intra-donor multi-segment ordering.
# A SINGLE donor carrying TWO structural segments in anchor-DESCENDING donor
# order (the later-anchor segment ลักษณะ ๒/๑ listed BEFORE the earlier-anchor
# segment ลักษณะ ๑/๑, split into two segments by an intervening non-structural
# recital row so _find_segments returns two spans). The OLD engine resolved
# both segments against ONE pre-insert code snapshot then applied them
# back-to-front by DONOR start index, which placed ลักษณะ ๒/๑ BEFORE ลักษณะ ๒
# — final order 1, 1/1, 2/1, 2 — while still reporting segments_applied=2,
# quarantined=0, conservation green (a silent placement defect). The fix
# resolves-and-applies one segment at a time against the CURRENT code rows,
# highest insertion index first, so both land correctly: 1, 1/1, 2, 2/1.
# Built inline (not in the shared fixture) so the shared fixture's own goldens
# stay untouched.
# ======================================================================
def _sec(type_id, no, content, name=None):
    return {"sectionTypeId": type_id, "sectionNo": no, "sectionName": name, "content": content}


def _two_segment_descending_donor_record():
    """Code doc: ภาค ๒ with ลักษณะ ๑ มั่นคง (มาตรา ๑๐๐) and ลักษณะ ๒ ปกครอง (มาตรา
    ๑๕๐). ONE donor act carries, in this order: segment A = ลักษณะ ๒/๑ (payload
    base 150 → anchors after ลักษณะ ๒, the HIGHER insertion index), then an
    intervening recital row (breaks the contiguous heading run into two
    segments), then segment B = ลักษณะ ๑/๑ (payload base 100 → anchors after
    ลักษณะ ๑, the LOWER insertion index). Donor segment order is thus anchor-
    DESCENDING — the exact case the old back-to-front-by-donor-index apply got
    wrong."""
    sections = [
        _sec(1, None, "ประมวลกฎหมายทดสอบ"),
        _sec(6, "2", "ภาค ๒ ความผิด"),
        _sec(7, "1", "ลักษณะ ๑ มั่นคง"),
        _sec(4, "100", "มาตรา ๑๐๐ ข้อความ มั่นคง"),
        _sec(7, "2", "ลักษณะ ๒ ปกครอง"),
        _sec(4, "150", "มาตรา ๑๕๐ ข้อความ ปกครอง"),
        # donor amendment act AFTER the code doc
        _sec(1, None, "พระราชบัญญัติแก้ไขเพิ่มเติมประมวลกฎหมายทดสอบ"),
        _sec(4, "2", "มาตรา ๒ พระราชบัญญัตินี้ให้ใช้บังคับ"),
        _sec(7, "2/1", "ลักษณะ ๒/๑ ความผิดหมวดปกครองเพิ่ม"),   # segment A head (higher anchor)
        _sec(4, "150/1", "มาตรา ๑๕๐/๑ ข้อความปกครองเพิ่ม"),
        _sec(3, None, "บทบัญญัติคั่นกลาง (recital) เพื่อแยกสองเซกเมนต์"),  # non-structural → breaks the run
        _sec(7, "1/1", "ลักษณะ ๑/๑ ความผิดมั่นคงเพิ่ม"),        # segment B head (lower anchor)
        _sec(4, "100/1", "มาตรา ๑๐๐/๑ ข้อความมั่นคงเพิ่ม"),
        _sec(14, None, "ผู้รับสนองพระบรมราชโองการ"),
    ]
    return {"law_code": "SYNTH2", "timeline_code": "SYNTH2-1B-0001-00",
            "reference_url": None, "sections": sections}


def test_intra_donor_multisegment_anchor_descending_order_correct():
    """RED on old code (produced 1, 1/1, 2/1, 2). Both segments must apply, in
    the correct final TOC order 1, 1/1, 2, 2/1, with conservation green."""
    record = _two_segment_descending_donor_record()
    docs = split_record(record)
    # precondition: this donor really does carry TWO separate structural segments
    from matra.merge import _find_segments, _primary_code_index
    scratch = [{**d, "rows": list(d["rows"])} for d in docs]
    ci = _primary_code_index(scratch)
    donor_seg_counts = [len(_find_segments(scratch[di]["rows"])) for di in range(ci + 1, len(scratch))]
    assert 2 in donor_seg_counts, f"fixture must have a 2-segment donor; got {donor_seg_counts}"

    total_before = sum(len(d["rows"]) for d in split_record(record))
    merged, report = merge_amendments(docs)
    total_after = sum(len(d["rows"]) for d in merged)
    code = next(d for d in merged if d["doc_type"] == "code")

    lak_seq = [_arab(r["no"]) for r in code["rows"] if r["raw_type"] == 7]
    assert lak_seq == ["1", "1/1", "2", "2/1"], (
        f"intra-donor multi-segment ordering defect: got {lak_seq}, "
        f"expected ['1', '1/1', '2', '2/1'] (ลักษณะ ๒/๑ must follow ลักษณะ ๒, not precede it)"
    )
    # both applied, none quarantined
    assert report["segments_found"] == 2
    assert report["segments_applied"] == 2
    assert report["segments_quarantined"] == 0
    # conservation green (same axes qa checks)
    assert report["chars_moved_in"] == report["chars_moved_out"]
    assert sum(seg["rows"] for seg in report["per_segment"]) == report["rows_moved"]
    assert total_after == total_before, f"row conservation broken: {total_before} -> {total_after}"

    # end-to-end qa: conservation ok, no unmerged structures, no hard fail
    docs2, flags2 = build_docs(record, merge=True)
    _, merge_report = merge_amendments(split_record(record))
    result = qa_check(record, docs2, flags2, merge_report=merge_report)
    assert result["checks"]["merge_conservation_ok"] is True
    assert result["checks"]["unmerged_amendment_structures"] == 0
    assert result["hard_fail"] is False


# ======================================================================
# Task 4'.2 review — Finding 4 (Important): merge char-conservation must be a
# REAL check, not self-referential. The old code added the SAME full_chars to
# both chars_moved_in and chars_moved_out, so chars_moved_in == chars_moved_out
# held by construction and could never fail. The fix measures the two sides
# independently (donor-side pre-removal count vs. code-doc growth). These two
# tests prove the check is now genuinely fireable.
# ======================================================================
def test_defective_move_ledger_trips_qa_conservation_false():
    """A move where the donor LOSES more chars than the code GAINS (chars_moved_in
    != chars_moved_out) must make merge_conservation_ok False and hard_fail True.
    Under the old self-referential ledger this state was unrepresentable (both
    numbers were the same variable); now the two are independent, so qa can and
    does catch it. This is the ledger-math check the brief pins."""
    # a defective merge_report: donor lost 100 chars, code grew by only 60
    defective = {"chars_moved_in": 100, "chars_moved_out": 60, "rows_moved": 2,
                 "per_segment": [{"rows": 2}], "rows_total_before": 10, "rows_total_after": 10}
    record = {"sections": [], "timeline_code": "DEFECTIVE-MOVE"}
    result = qa_check(record, [], [], merge_report=defective)
    assert result["checks"]["merge_conservation_ok"] is False
    assert result["hard_fail"] is True

    # control: a balanced report (chars_moved_in == chars_moved_out) is OK — proving
    # the check discriminates, not just always-fails.
    balanced = dict(defective, chars_moved_out=100)
    ok = qa_check(record, [], [], merge_report=balanced)
    assert ok["checks"]["merge_conservation_ok"] is True


def test_defective_physical_move_trips_internal_assert(monkeypatch):
    """Directly exercise the merge_amendments physical-move ledger: monkeypatch
    _content_chars so the code doc's measured growth UNDER-reports (simulating a
    move that mangled/dropped payload chars on the code side). Because
    chars_moved_out is now measured from the code doc independently of
    chars_moved_in, the internal conservation assert genuinely trips — under the
    old code (same number added twice) it could not."""
    import matra.merge as merge_mod

    record = _two_segment_descending_donor_record()
    docs = split_record(record)

    orig = merge_mod._content_chars
    state = {"calls": 0}

    def under_reporting_content_chars(rows):
        # every 2nd call is the post-insert measurement in an apply step; shave 5
        # chars off it so code growth < donor loss → chars_moved_out < chars_moved_in.
        state["calls"] += 1
        v = orig(rows)
        return v - 5 if state["calls"] % 2 == 0 else v

    monkeypatch.setattr(merge_mod, "_content_chars", under_reporting_content_chars)
    with pytest.raises(AssertionError, match="char conservation broken"):
        merge_mod.merge_amendments(docs)
