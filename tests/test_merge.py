# Task 4′.2 — Merge Engine (defect #8) tests.
#
# Design basis: docs/merge_answer_key.md + docs/merge_grammar.md (verified
# against the raw -63 row before writing these tests). Raw-corpus tests are
# skipif-guarded so the repo suite still runs on machines without the corpus;
# the quarantine / directive-recognizer tests are corpus-independent (synthetic
# records) and always run.
import json
import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))
from matra.merge import merge_amendments, recognize_directives
from matra.splitter import split_record
from matra.structure import build_docs, toc_of
from matra.qa import qa_check


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

# ---- Thai-digit helper (tests only; mirrors the arabic normalization the engine uses) ----
_TH = "๐๑๒๓๔๕๖๗๘๙"
_TR = {c: str(i) for i, c in enumerate(_TH)}


def _arab(s):
    return None if s is None else "".join(_TR.get(c, c) for c in s)


def _row_63_record():
    rows = [json.loads(l) for l in RAW.read_text(encoding="utf-8").splitlines() if l.strip()]
    return next(r for r in rows if r["timeline_code"] == "ป0006-1D-0003-63")


# ======================================================================
# Test 1 — Golden 4 placements (from answer key). Assert ALL 4 land in the
# code doc's TOC in the correct order, each under the correct container, with
# the correct มาตรา payload present.
# ======================================================================
@requires_corpus
def test_four_golden_placements_in_code_toc():
    record = _row_63_record()
    docs = split_record(record)
    merged, report = merge_amendments(docs)
    # locate the code doc (the doc whose doc_type is "code")
    code = next(d for d in merged if d["doc_type"] == "code")
    rows = code["rows"]

    # helper: ordered structural-heading rows of the code doc, arabic-normalized
    def heads():
        out = []
        for r in rows:
            if r["raw_type"] in (6, 7, 8, 9):
                out.append((r["raw_type"], _arab(r["no"]), r["c"]))
        return out

    h = heads()

    # --- (a) ลักษณะ ๑/๑ ก่อการร้าย between ลักษณะ ๑ (มั่นคง) and ลักษณะ ๒ (การปกครอง) in ภาค ๒ ---
    lak_seq = [(no, c) for (t, no, c) in h if t == 7]
    # find the มั่นคง ลักษณะ ๑ (the sequence-consistent one), then assert next is 1/1 then 2
    idx_mankong = next(i for i, (no, c) in enumerate(lak_seq)
                       if no == "1" and "มั่นคง" in c)
    assert lak_seq[idx_mankong + 1][0] == "1/1", f"expected ลักษณะ ๑/๑ after มั่นคง, seq={lak_seq}"
    assert "ก่อการร้าย" in lak_seq[idx_mankong + 1][1]
    assert lak_seq[idx_mankong + 2][0] == "2" and "ปกครอง" in lak_seq[idx_mankong + 2][1]

    # --- (b) หมวด ๔ บัตรอิเล็กทรอนิกส์ and (c) หมวด ๕ หนังสือเดินทาง after หมวด ๓ under ลักษณะ ๗ ---
    # Walk the code doc; when inside ลักษณะ ๗, the หมวด sequence must contain 3,4,5 in order,
    # with 4=บัตร and 5=หนังสือเดินทาง, and end before ลักษณะ ๘.
    in_lak7 = False
    muad_in_lak7 = []
    for (t, no, c) in h:
        if t == 7:
            in_lak7 = (no == "7" and "ปลอม" in c)
        elif t == 8 and in_lak7:
            muad_in_lak7.append((no, c))
    muad_nos = [no for no, c in muad_in_lak7]
    assert muad_nos[:5] == ["1", "2", "3", "4", "5"], f"หมวด seq under ลักษณะ ๗ wrong: {muad_in_lak7}"
    assert "บัตรอิเล็กทรอนิกส์" in dict(muad_in_lak7)["4"]
    assert "หนังสือเดินทาง" in dict(muad_in_lak7)["5"]

    # --- (d) ลักษณะ ๑๓ ศพ as the last ลักษณะ of ภาค ๒ (before ภาค ๓'s rows) ---
    # Scan rows: find the ภาค ๓ heading; the last ลักษณะ heading before it must be ๑๓ ศพ.
    phak3_i = next(i for i, r in enumerate(rows) if r["raw_type"] == 6 and _arab(r["no"]) == "3")
    lak_before_phak3 = [r for r in rows[:phak3_i] if r["raw_type"] == 7]
    assert _arab(lak_before_phak3[-1]["no"]) == "13", "ลักษณะ ๑๓ must be last ลักษณะ of ภาค ๒"
    assert "ศพ" in lak_before_phak3[-1]["c"]

    # --- matra payloads present in code doc, parented under the correct new container ---
    matra_nos = {_arab(r["no"]) for r in rows if r["raw_type"] == 4}
    for want in ["135/1", "135/2", "135/3", "135/4",
                 "269/1", "269/7", "269/8", "269/15",
                 "366/1", "366/4"]:
        assert want in matra_nos, f"payload มาตรา {want} missing from code doc after merge"


# ======================================================================
# Test 2 — Merge conservation (the arithmetic the brief pins).
# ======================================================================
@requires_corpus
def test_merge_conservation_numbers():
    record = _row_63_record()
    docs = split_record(record)
    merged, report = merge_amendments(docs)

    # rows_moved = payload matra rows = 8+9+10+4 = 31 (heading rows are the anchors, counted separately)
    assert report["rows_moved"] == 31, f"rows_moved={report['rows_moved']}"

    # per-segment payload rows and chars per the answer key
    by_head = {seg["heading"]: seg for seg in report["per_segment"]}
    expected = {
        "ลักษณะ ๑/๑ ความผิดเกี่ยวกับการก่อการร้าย": (8, 1924),
        "หมวด ๔ ความผิดเกี่ยวกับบัตรอิเล็กทรอนิกส์": (9, 2109),
        "หมวด ๕ ความผิดเกี่ยวกับหนังสือเดินทาง": (10, 2409),
        "ลักษณะ ๑๓ ความผิดเกี่ยวกับศพ": (4, 649),
    }
    for head, (rows_exp, chars_exp) in expected.items():
        assert head in by_head, f"segment heading {head!r} not in report; got {list(by_head)}"
        assert by_head[head]["rows"] == rows_exp, f"{head}: rows {by_head[head]['rows']} != {rows_exp}"
        assert by_head[head]["chars"] == chars_exp, f"{head}: chars {by_head[head]['chars']} != {chars_exp}"

    # conservation: chars_moved_in == chars_moved_out (full physical move, headings + payload)
    assert report["chars_moved_in"] == report["chars_moved_out"], "char conservation broken"

    # donor docs post-merge contain NO structural headings (DEFECT#8 → 0)
    donor_headings = [n for d in merged if d["doc_type"] != "code"
                      for n in d["rows"] if n["raw_type"] in (7, 8, 9)]
    assert donor_headings == [], f"donor still holds structural headings: {donor_headings}"

    # total row count across ALL docs unchanged vs the un-merged split
    total_before = sum(len(d["rows"]) for d in split_record(record))
    total_after = sum(len(d["rows"]) for d in merged)
    assert total_after == total_before, f"row conservation broken: {total_before} -> {total_after}"

    # segments found/applied/quarantined bookkeeping
    assert report["segments_found"] == 4
    assert report["segments_applied"] == 4
    assert report["segments_quarantined"] == 0


@requires_corpus
def test_defect8_detector_zero_after_merge():
    record = _row_63_record()
    docs, flags = build_docs(record, merge=True)
    result = qa_check(record, docs, flags, merge_report=_merge_report_for(record))
    assert result["checks"]["unmerged_amendment_structures"] == 0
    assert result["checks"]["merge"]["segments_applied"] == 4
    assert result["checks"]["merge_conservation_ok"] is True
    assert result["hard_fail"] is False


def _merge_report_for(record):
    docs = split_record(record)
    _, report = merge_amendments(docs)
    return report


@requires_corpus
def test_anchor_rules_recorded():
    """The merge report must record WHICH anchor rule fired per segment (auditability)."""
    record = _row_63_record()
    docs = split_record(record)
    _, report = merge_amendments(docs)
    rules = {seg["heading"]: seg["anchor_rule"] for seg in report["per_segment"]}
    # ลักษณะ ๑/๑ → slash, sequence-consistent
    assert "slash" in rules["ลักษณะ ๑/๑ ความผิดเกี่ยวกับการก่อการร้าย"]
    # ลักษณะ ๑๓ ศพ → END-of-ภาค fallback (N-1 = ๑๒ not literally present)
    assert "end_of_phak" in rules["ลักษณะ ๑๓ ความผิดเกี่ยวกับศพ"] or \
           "fallback" in rules["ลักษณะ ๑๓ ความผิดเกี่ยวกับศพ"]
    # หมวด ๔/๕ → plain sequential (N-1 anchor)
    assert "plain" in rules["หมวด ๔ ความผิดเกี่ยวกับบัตรอิเล็กทรอนิกส์"]
    assert "plain" in rules["หมวด ๕ ความผิดเกี่ยวกับหนังสือเดินทาง"]


# ======================================================================
# Test 3 — merge=False untouched (golden safety). build_docs(record) with no
# merge arg must equal build_docs(record, merge=False), and the golden test
# (separate file) must still pass byte-identical — asserted here via the same
# canonicalizer for the code doc structure.
# ======================================================================
@requires_corpus
def test_merge_false_is_default_and_unchanged():
    record = _row_63_record()
    docs_default, flags_default = build_docs(record)
    docs_explicit, flags_explicit = build_docs(record, merge=False)
    # deep-equal except for the nondeterministic ingested_at timestamp
    def _strip(ds):
        out = json.loads(json.dumps(ds))
        for d in out:
            d["provenance"]["ingested_at"] = "SENTINEL"
        return out
    assert _strip(docs_default) == _strip(docs_explicit)
    assert flags_default == flags_explicit


@requires_corpus
def test_merge_false_leaves_defect8_present():
    """Sanity: without merge, DEFECT#8 detector still reports the 4 stranded structures
    (proving the OFF path is genuinely the pre-change behavior)."""
    record = _row_63_record()
    docs, flags = build_docs(record, merge=False)
    result = qa_check(record, docs, flags)
    assert result["checks"]["unmerged_amendment_structures"] >= 4


# ======================================================================
# Test 4 — Quarantine + directive-recognizer paths (synthetic, corpus-independent).
# ======================================================================
def _synthetic_record(sections):
    return {"law_code": "TEST", "timeline_code": "TEST-1B-0001-00",
            "reference_url": None, "sections": sections}


def _sec(type_id, no, content, name=None):
    return {"sectionTypeId": type_id, "sectionNo": no, "sectionName": name, "content": content}


def test_quarantine_unresolvable_anchor():
    """A donor segment whose anchor cannot be resolved (หมวด ๗ with no หมวด ๖ and no
    matra-span match) is NOT inserted, is quarantined + flagged, no crash, donor keeps
    its rows, and conservation still balances."""
    sections = [
        # code doc: one ลักษณะ ๑ with หมวด ๑ only (no หมวด ๖), matra ๑ (base 1, far from 999)
        _sec(1, None, "ประมวลกฎหมายทดสอบ"),
        _sec(6, "1", "ภาค ๑ ทดสอบ"),
        _sec(7, "1", "ลักษณะ ๑ ทดสอบ"),
        _sec(8, "1", "หมวด ๑ ทดสอบ"),
        _sec(4, "1", "มาตรา ๑ ข้อความ"),
        # donor amendment doc AFTER the code: หมวด ๗ (needs หมวด ๖; none exists), payload base 999
        _sec(1, None, "พระราชบัญญัติแก้ไขเพิ่มเติมประมวลกฎหมายทดสอบ"),
        _sec(4, "2", "มาตรา ๒ พระราชบัญญัตินี้ให้ใช้บังคับ"),
        _sec(8, "7", "หมวด ๗ ไม่มีที่ยึด"),
        _sec(4, "999/1", "มาตรา ๙๙๙/๑ ข้อความใหม่"),
    ]
    record = _synthetic_record(sections)
    docs = split_record(record)
    total_before = sum(len(d["rows"]) for d in split_record(record))
    merged, report = merge_amendments(docs)

    assert report["segments_found"] == 1
    assert report["segments_applied"] == 0
    assert report["segments_quarantined"] == 1
    assert report["rows_moved"] == 0
    # donor keeps its rows
    donor = merged[1]
    assert any(r["raw_type"] == 8 and r["no"] == "7" for r in donor["rows"]), "quarantined donor lost its heading"
    # a flag/unresolved entry was emitted
    assert len(report["unresolved"]) >= 1
    # conservation still balances (nothing moved)
    assert report["chars_moved_in"] == report["chars_moved_out"] == 0
    total_after = sum(len(d["rows"]) for d in merged)
    assert total_after == total_before


def test_directive_sentence_recognized_not_applied():
    """A directive sentence in a donor matra row is COUNTED (directives_recognized),
    flagged directive_unapplied, and NOT applied (directives_applied stays 0)."""
    sections = [
        _sec(1, None, "ประมวลกฎหมายทดสอบ"),
        _sec(4, "1", "มาตรา ๑ ข้อความ"),
        _sec(1, None, "พระราชบัญญัติแก้ไขเพิ่มเติมประมวลกฎหมายทดสอบ"),
        _sec(4, "3", "มาตรา ๓ ให้เพิ่มความต่อไปนี้เป็นมาตรา ๙ ทวิ แห่งประมวลกฎหมายทดสอบ \"มาตรา ๙ ทวิ ...\""),
        _sec(4, "5", "มาตรา ๕ ให้ยกเลิกความในมาตรา ๑๖ แห่งประมวลกฎหมายทดสอบ และให้ใช้ความต่อไปนี้แทน \"มาตรา ๑๖ ...\""),
        _sec(4, "7", "มาตรา ๗ ให้ยกเลิกพระราชบัญญัติอื่น พ.ศ. ๒๕๐๐"),
    ]
    record = _synthetic_record(sections)
    docs = split_record(record)
    merged, report = merge_amendments(docs)

    dr = report["directives_recognized"]
    assert dr.get("ADD", 0) == 1, f"ADD not recognized: {dr}"
    assert dr.get("REPLACE", 0) == 1, f"REPLACE not recognized: {dr}"
    assert dr.get("REPEAL", 0) == 1, f"REPEAL not recognized: {dr}"
    assert report["directives_applied"] == 0
    # each recognized directive raises a directive_unapplied unresolved entry
    unapplied = [u for u in report["unresolved"] if u.get("kind") == "directive_unapplied"]
    assert len(unapplied) == 3, f"expected 3 directive_unapplied, got {unapplied}"


def test_directive_false_positive_not_counted():
    """ให้นำ…มาใช้บังคับโดยอนุโลม is NOT a directive (survey §false-positives) — not counted."""
    sections = [
        _sec(1, None, "ประมวลกฎหมายทดสอบ"),
        _sec(4, "1", "มาตรา ๑ ข้อความ"),
        _sec(1, None, "พระราชบัญญัติแก้ไขเพิ่มเติมประมวลกฎหมายทดสอบ"),
        _sec(4, "5", "มาตรา ๕ ให้นำบทบัญญัติมาตรา ๓๐ มาใช้บังคับโดยอนุโลม"),
    ]
    record = _synthetic_record(sections)
    docs = split_record(record)
    merged, report = merge_amendments(docs)
    dr = report["directives_recognized"]
    assert sum(dr.values()) == 0, f"false-positive counted as directive: {dr}"
    assert report["directives_applied"] == 0


def test_recognize_directives_unit():
    """Direct unit test of the recognizer families over raw text lines."""
    add = "ให้เพิ่มความต่อไปนี้เป็นมาตรา ๙ ทวิ แห่งพระราชบัญญัติ..."
    replace = "ให้ยกเลิกความในมาตรา ๑๖ แห่ง... และให้ใช้ความต่อไปนี้แทน \"...\""
    repeal = "ให้ยกเลิกพระราชบัญญัติเก่า พ.ศ. ๒๕๐๐"
    fp = "ให้นำบทบัญญัติมาตรา ๓๐ มาใช้บังคับโดยอนุโลม"
    assert recognize_directives(add) == "ADD"
    assert recognize_directives(replace) == "REPLACE"
    assert recognize_directives(repeal) == "REPEAL"
    assert recognize_directives(fp) is None
    assert recognize_directives("มาตรา ๑ ผู้ใดกระทำ...") is None


def test_no_donor_segments_is_noop():
    """A record with a code doc but no donor structural segments produces an empty,
    balanced report and unchanged docs."""
    sections = [
        _sec(1, None, "ประมวลกฎหมายทดสอบ"),
        _sec(6, "1", "ภาค ๑ ทดสอบ"),
        _sec(7, "1", "ลักษณะ ๑ ทดสอบ"),
        _sec(4, "1", "มาตรา ๑ ข้อความ"),
    ]
    record = _synthetic_record(sections)
    docs = split_record(record)
    before = json.loads(json.dumps(docs))
    merged, report = merge_amendments(docs)
    assert report["segments_found"] == 0
    assert report["rows_moved"] == 0
    assert report["chars_moved_in"] == report["chars_moved_out"] == 0
    assert json.loads(json.dumps(merged)) == before


def test_merge_amendments_is_pure_no_input_mutation():
    """merge_amendments must not mutate its input docs list (pure function)."""
    sections = [
        _sec(1, None, "ประมวลกฎหมายทดสอบ"),
        _sec(6, "1", "ภาค ๑"),
        _sec(7, "1", "ลักษณะ ๑ มั่นคง"),
        _sec(4, "135", "มาตรา ๑๓๕ ข้อความ"),
        _sec(7, "2", "ลักษณะ ๒ การปกครอง"),
        _sec(4, "136", "มาตรา ๑๓๖ ข้อความ"),
        _sec(1, None, "พระราชบัญญัติแก้ไขเพิ่มเติมประมวลกฎหมายทดสอบ"),
        _sec(4, "2", "มาตรา ๒ บังคับใช้"),
        _sec(7, "1/1", "ลักษณะ ๑/๑ ก่อการร้าย"),
        _sec(4, "135/1", "มาตรา ๑๓๕/๑ ข้อความใหม่"),
    ]
    record = _synthetic_record(sections)
    docs = split_record(record)
    snapshot = json.loads(json.dumps(docs))
    merge_amendments(docs)
    assert json.loads(json.dumps(docs)) == snapshot, "merge_amendments mutated its input"
