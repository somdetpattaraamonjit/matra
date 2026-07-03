# Task 5′ — src/matra/flat.py: flat export (1 row = 1 มาตรา) + ELI wrapper +
# enrich wiring.
#
# Design basis: docs/akn_adoption_verdicts.md §Design decisions (esp. #6 ELI
# wrapper), schemas/matra-0.2.json flat_profile.columns (THE column contract),
# src/matra/cid.py (assign_cids/assign_eids/extract_refs — consumed, never
# modified), src/matra/structure.py (build_docs/build_docs_merged, doc
# envelope shape, hierarchy_path convention — NOT parsed as a string; flat.py
# walks parent_id itself per the brief).
#
# HARD RULE (golden lock protection): enrich_docs is a SEPARATE stage applied
# AFTER build_docs_merged returns. It must never be wired inside
# build_docs/build_docs_merged/normalize — this suite's own test 8 (full
# existing-suite regression) is the proof that wiring stayed outside those
# paths.
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

from matra.cid import extract_refs
from matra.structure import build_docs
from matra.qa import primary_doc
from matra.flat import FLAT_COLUMNS, enrich_docs, to_flat, work_expressions, compute_is_latest

FIX = pathlib.Path(__file__).parent / "fixtures/criminal_code_sample.jsonl"
SCHEMA_PATH = pathlib.Path(__file__).parents[1] / "schemas/matra-0.2.json"


def _fixture_records():
    return [json.loads(l) for l in FIX.read_text(encoding="utf-8").splitlines() if l.strip()]


def _record(suffix):
    return next(r for r in _fixture_records() if r["timeline_code"].endswith(suffix))


def _enriched_code_doc(suffix="-63"):
    """Build one real doc envelope from the small fixture record via the
    actual pipeline API (build_docs, merge=False — matches tests/test_cid.py's
    own pattern), then run it through enrich_docs. Returns (doc, record)."""
    record = _record(suffix)
    docs, _flags = build_docs(record, merge=False)
    code = primary_doc(docs)
    enriched = enrich_docs([code], record["law_code"])
    return enriched[0], record


def _record_ctx(record, doc):
    """Minimal record_ctx per the brief: law_group_code/reference_url/
    is_latest_computed from record/envelope context. record_ctx shape is
    ours to design (brief ambiguity resolution b) — plain dict derived from
    the record + doc's own timeline block, no invented business logic."""
    return {
        "law_group_code": record["law_code"],
        "reference_url": record.get("reference_url"),
        "is_latest_computed": doc["timeline"]["is_latest_computed"],
    }


# ======================================================================
# Test 1: FLAT_COLUMNS == schema const list (read schema independently in
# the test, not by importing flat.py's own already-loaded copy — proves the
# module genuinely loaded from the schema file, not a hardcoded parallel list).
# ======================================================================
def test_flat_columns_matches_schema_const():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    expected = schema["properties"]["flat_profile"]["properties"]["columns"]["const"]
    assert FLAT_COLUMNS == expected
    assert isinstance(FLAT_COLUMNS, list)


# ======================================================================
# Test 2: to_flat on a fixture-built enriched code doc — row count == matra
# count in the doc; every row's keys == set(FLAT_COLUMNS) exactly (no extra,
# no missing).
# ======================================================================
def test_to_flat_row_count_and_exact_keys():
    doc, record = _enriched_code_doc()
    ctx = _record_ctx(record, doc)
    rows = to_flat(doc, ctx)

    matra_count = sum(1 for n in doc["structure"] if n["node_type"] == "matra")
    assert len(rows) == matra_count
    assert matra_count > 0, "fixture must contain at least one matra node"
    for row in rows:
        assert set(row) == set(FLAT_COLUMNS), (
            f"row keys {sorted(set(row))} != FLAT_COLUMNS {sorted(set(FLAT_COLUMNS))}"
        )


# ======================================================================
# Test 3 (falsification #1 — plan-mandated): breadcrumb survives flattening.
# At least one row has a non-None laksana or muad ancestor heading — proves
# to_flat walks parent_id, not just direct-parent shortcuts.
# ======================================================================
def test_to_flat_breadcrumb_survives_flattening():
    doc, record = _enriched_code_doc()
    ctx = _record_ctx(record, doc)
    rows = to_flat(doc, ctx)
    assert any(r["laksana"] is not None or r["muad"] is not None for r in rows), (
        "expected at least one row with a non-None laksana/muad ancestor heading"
    )


# ======================================================================
# Test 4: verbatim — a row's matra_no / matra_no_arabic / text byte-equal to
# the source node's number / number_arabic / joined paragraph text. ZERO
# mutation anywhere in the to_flat path.
# ======================================================================
def test_to_flat_verbatim_number_and_text():
    doc, record = _enriched_code_doc()
    ctx = _record_ctx(record, doc)
    rows = to_flat(doc, ctx)
    by_cid = {n["matra_cid"]: n for n in doc["structure"] if n.get("node_type") == "matra"}

    for row in rows:
        node = by_cid[row["matra_cid"]]
        assert row["matra_no"] == node["number"]
        assert row["matra_no_arabic"] == node["number_arabic"]
        expected_text = "\n".join(p["text"] for p in node.get("paragraphs", []))
        assert row["text"] == expected_text


# ======================================================================
# Test 5: refs_out populated via the REAL extract_refs on a matra whose text
# contains a มาตรา cross-reference; deka_refs == [] (phase 2, always empty).
#
# UPDATED (Task 5′ FIX cycle, task5-fix-brief.md FIX 2): refs_out is no
# longer the raw, unfiltered extract_refs(text) output — every มาตรา's own
# heading at position 0 of its text would otherwise self-match and pollute
# refs_out for essentially every row (the defect the fix cycle closes).
# This test now asserts refs_out equals extract_refs(text) with that one
# position-0-self-reference dropped (see test_to_flat_refs_out_suppresses_
# self_reference / _retains_genuine_midtext_crossref / _fixture_level_no_
# self_pollution below for the fix's own dedicated RED/GREEN coverage) —
# still proving refs_out is derived from the REAL extract_refs, never a
# stub, just against the corrected (filtered) contract instead of the
# stale pre-fix one.
# ======================================================================
def test_to_flat_refs_out_via_real_extract_refs_and_deka_refs_empty():
    doc, record = _enriched_code_doc()
    ctx = _record_ctx(record, doc)
    rows = to_flat(doc, ctx)

    found_with_ref = False
    for row in rows:
        raw_refs = extract_refs(row["text"])
        # the fix's own filter, replicated here (not imported) so this test
        # independently verifies row["refs_out"] against the documented
        # public contract rather than reaching into flat.py's private helper.
        own = row["matra_no_arabic"]
        expected_refs = [
            r for i, r in enumerate(raw_refs)
            if not (i == 0 and r["target_matra"] == own and row["text"].startswith("มาตรา"))
        ]
        assert row["refs_out"] == expected_refs, (
            "refs_out must equal real extract_refs(text) with only the "
            "position-0 self-reference dropped, not a stub and not "
            "over-filtered"
        )
        assert row["deka_refs"] == []
        if expected_refs:
            found_with_ref = True
    assert found_with_ref, "expected at least one row in the fixture whose text carries a มาตรา cross-reference"


# ======================================================================
# Test 6: enrich_docs does NOT mutate number/number_arabic/text and adds
# matra_cid/eId/wId (spot-check on one matra node).
# ======================================================================
def test_enrich_docs_no_mutation_and_adds_ids():
    record = _record("-63")
    docs, _flags = build_docs(record, merge=False)
    code = primary_doc(docs)

    # snapshot BEFORE enrich (deep copy so post-enrich mutation, if any, is caught)
    import copy
    before = copy.deepcopy(code["structure"])
    before_by_id = {n["node_id"]: n for n in before}

    enriched = enrich_docs([code], record["law_code"])
    after = enriched[0]["structure"]

    matra_checked = 0
    for n in after:
        b = before_by_id[n["node_id"]]
        assert n["number"] == b["number"]
        assert n["number_arabic"] == b["number_arabic"]
        assert n.get("paragraphs") == b.get("paragraphs")
        if n["node_type"] == "matra":
            assert "matra_cid" in n and n["matra_cid"] is not None
            matra_checked += 1
        if n.get("number_arabic"):
            assert "eId" in n and n["eId"] is not None
            assert "wId" in n and n["wId"] == n["eId"]
    assert matra_checked > 0


# ======================================================================
# Test 7: work_expressions on the 2 fixture records (-00 and -63) — 2
# expressions, only -63 is_latest_computed True, eli:is_realized_by lists
# both timeline codes.
# ======================================================================
def test_work_expressions_two_records_only_63_latest():
    records = _fixture_records()
    r00 = next(r for r in records if r["timeline_code"].endswith("-00"))
    r63 = next(r for r in records if r["timeline_code"].endswith("-63"))
    assert r00["law_code"] == r63["law_code"]
    law_group_code = r00["law_code"]

    docs00, _f00 = build_docs(r00, merge=False)
    docs63, _f63 = build_docs(r63, merge=False)
    code00 = primary_doc(docs00)
    code63 = primary_doc(docs63)

    wrapper = work_expressions([code00, code63])

    assert wrapper["work"] == law_group_code
    assert wrapper["schema"] == "matra-work-expressions/v0"
    assert len(wrapper["expressions"]) == 2

    latest_flags = [e["is_latest_computed"] for e in wrapper["expressions"]]
    assert sum(1 for f in latest_flags if f) == 1

    latest_expr = next(e for e in wrapper["expressions"] if e["is_latest_computed"])
    assert latest_expr["timeline_code"].endswith("-63")

    codes = {e["timeline_code"] for e in wrapper["expressions"]}
    assert set(wrapper["eli:is_realized_by"]) == codes
    assert r00["timeline_code"] in codes and r63["timeline_code"] in codes


# ======================================================================
# Test 8: golden-lock regression — this test file's own existence/collection
# must not perturb the pre-existing 73; the REAL proof is the full-suite run
# at the end of the task (brief §Tests item 8: "existing full suite green
# (73 before you; must be ≥73 after, 0 skip)"). This in-file check is a cheap
# sanity companion: importing flat.py must not raise, and the schema file
# flat.py reads from must not have been mutated by this task (columns still
# match the pre-Task-5′ committed const — belt-and-suspenders vs test 1).
# ======================================================================
def test_golden_lock_schema_untouched_flat_profile_const_stable():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["properties"]["flat_profile"]["properties"]["columns"]["const"] == [
        "matra_cid", "law_group_code", "doc_id", "doc_type", "law_title_th",
        "phak", "laksana", "muad", "suan", "matra_no", "matra_no_arabic",
        "status", "effective_from", "effective_until", "text", "refs_out",
        "deka_refs", "reference_url", "is_latest_computed",
    ]


# ======================================================================
# Test 9 (e2e, corpus-gated like existing e2e tests — brief: "they currently
# do NOT skip — 0-skip suite"): run enrich_docs + to_flat on the REAL -63
# code doc post-merge (build_docs_merged, the same single-execution API the
# CLI/e2e runner uses) and assert the golden breadcrumb: the row with
# matra_no_arabic == "135/1" exists, its laksana heading contains
# "ก่อการร้าย", its phak heading contains "ภาค ๒", and its matra_cid ==
# "ป0006-1D-0003:135/1" — the merge-then-enrich-then-flatten chain proven
# end-to-end on the real corpus, mirroring tests/test_e2e_criminal63.py's own
# @requires_corpus style (no skip decorator; the corpus is expected present).
# ======================================================================
import os  # noqa: E402  (grouped near the corpus resolver it serves, matching test_e2e_criminal63.py style)


def _resolve_corpus():
    """Identical resolver to docs/run_e2e_criminal63.py / tests/test_e2e_criminal63.py
    (env MATRA_CORPUS -> ~/.aice/legalrag/raw/ -> /sessions/*/mnt glob)."""
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
    return home


_RAW = _resolve_corpus()
_TIMELINE_CODE = "ป0006-1D-0003-63"


def _row_63_record_real():
    rows = [json.loads(l) for l in _RAW.read_text(encoding="utf-8").splitlines() if l.strip()]
    return next(r for r in rows if r["timeline_code"] == _TIMELINE_CODE)


def test_e2e_golden_breadcrumb_135_1_kokanray_post_merge_enrich_flatten():
    from matra.structure import build_docs_merged

    assert _RAW.exists(), f"real -63 corpus not found at {_RAW} — e2e test 9 requires it (0-skip suite)"
    record = _row_63_record_real()
    docs, _flags, _merge_report = build_docs_merged(record)
    code = primary_doc(docs)
    law_group_code = record["law_code"]

    enriched = enrich_docs([code], law_group_code)[0]
    ctx = {
        "law_group_code": law_group_code,
        "reference_url": record.get("reference_url"),
        "is_latest_computed": enriched["timeline"]["is_latest_computed"],
    }
    rows = to_flat(enriched, ctx)

    target = next((r for r in rows if r["matra_no_arabic"] == "135/1"), None)
    assert target is not None, "row with matra_no_arabic=='135/1' not found post-merge"
    assert target["laksana"] is not None and "ก่อการร้าย" in target["laksana"]
    assert target["phak"] is not None and "ภาค ๒" in target["phak"]
    assert target["matra_cid"] == "ป0006-1D-0003:135/1"


# ======================================================================
# Task 5′ FIX cycle (review findings, task5-fix-brief.md) — FIX 1
#
# Problem: flat rows sourced is_latest_computed from
# d["timeline"]["is_latest_computed"] (structure.py's hardcoded True per
# record — it never sees a sibling group). Real run: all 485 flat rows said
# true while work_expressions.json correctly said only 1/34 (-63) is latest.
#
# Fix: ONE reusable function `compute_is_latest(timeline_seq, group_seqs)`
# in flat.py implementing `is_latest = (timeline_seq == max(group_seqs))`,
# consumed by BOTH work_expressions (refactored to stop duplicating its own
# inline max-seq arithmetic) and by every record_ctx assembly site
# (cli.py's --flat path, docs/run_e2e_criminal63.py) — group derived, never
# the envelope hardcode.
# ======================================================================

def test_compute_is_latest_group_derived_basic():
    """Direct unit test of the reusable derivation function itself: True iff
    timeline_seq equals the max of the group's seqs."""
    assert compute_is_latest(63, [0, 63]) is True
    assert compute_is_latest(0, [0, 63]) is False
    assert compute_is_latest(5, [5]) is True
    assert compute_is_latest(3, [1, 2, 3, 3]) is True  # tie at the max is still latest


def test_to_flat_is_latest_computed_is_group_derived_not_envelope_hardcode():
    """RED signal for FIX 1: build flat rows for the fixture's -00 record
    with group context = BOTH fixture records (-00 and -63 together). Every
    -00 flat row must have is_latest_computed == False (today's bug: -00's
    own doc envelope carries the structure.py hardcode
    timeline.is_latest_computed == True, unconditionally, since
    _build_trees never sees a sibling group — so reading that field
    directly, as the pre-fix code did, would make this assertion fail:
    that failure IS the RED signal proving the hardcode is currently being
    read). Companion: -63 rows must have is_latest_computed == True.
    """
    doc00, record00 = _enriched_code_doc("-00")
    doc63, record63 = _enriched_code_doc("-63")
    assert record00["law_code"] == record63["law_code"]

    group_seqs = [doc00["timeline"]["timeline_seq"], doc63["timeline"]["timeline_seq"]]

    ctx00 = {
        "law_group_code": record00["law_code"],
        "reference_url": record00.get("reference_url"),
        "is_latest_computed": compute_is_latest(doc00["timeline"]["timeline_seq"], group_seqs),
    }
    ctx63 = {
        "law_group_code": record63["law_code"],
        "reference_url": record63.get("reference_url"),
        "is_latest_computed": compute_is_latest(doc63["timeline"]["timeline_seq"], group_seqs),
    }

    rows00 = to_flat(doc00, ctx00)
    rows63 = to_flat(doc63, ctx63)
    assert len(rows00) > 0 and len(rows63) > 0, "fixture must yield matra rows on both records"

    assert all(r["is_latest_computed"] is False for r in rows00), (
        "-00 flat rows must all have is_latest_computed == False when compared "
        "against the -63 sibling in the same group (group-derived, not the "
        "structure.py envelope hardcode which is unconditionally True)"
    )
    assert all(r["is_latest_computed"] is True for r in rows63), (
        "-63 flat rows must all have is_latest_computed == True (it is the max "
        "timeline_seq in the 2-record fixture group)"
    )


def test_work_expressions_uses_compute_is_latest_single_source_of_truth():
    """work_expressions must be refactored to call compute_is_latest rather
    than duplicating its own inline max-seq comparison — proven by
    monkeypatching compute_is_latest and confirming work_expressions'
    per-expression is_latest_computed values change accordingly (i.e. the
    wrapper actually delegates, it doesn't just happen to agree)."""
    import matra.flat as flat_mod

    records = _fixture_records()
    r00 = next(r for r in records if r["timeline_code"].endswith("-00"))
    r63 = next(r for r in records if r["timeline_code"].endswith("-63"))
    docs00, _f00 = build_docs(r00, merge=False)
    docs63, _f63 = build_docs(r63, merge=False)
    code00 = primary_doc(docs00)
    code63 = primary_doc(docs63)

    calls = []
    real_fn = flat_mod.compute_is_latest

    def spy(timeline_seq, group_seqs):
        calls.append((timeline_seq, list(group_seqs)))
        return real_fn(timeline_seq, group_seqs)

    original = flat_mod.compute_is_latest
    flat_mod.compute_is_latest = spy
    try:
        wrapper = flat_mod.work_expressions([code00, code63])
    finally:
        flat_mod.compute_is_latest = original

    assert len(calls) >= 2, (
        "work_expressions must call compute_is_latest at least once per "
        "expression — it must not keep its own duplicated max-seq logic"
    )
    latest_flags = [e["is_latest_computed"] for e in wrapper["expressions"]]
    assert sum(1 for f in latest_flags if f) == 1


# ======================================================================
# Task 5′ FIX cycle — FIX 2 (directed Minor): refs_out self-citation
# pollution.
#
# Problem: every มาตรา's text begins with its own heading "มาตรา <n> …" so
# extract_refs (cid.py, generic/untouchable) emits a self-reference in
# essentially every row — genuine cross-references get drowned out.
#
# Fix location: flat.py's to_flat ONLY. Filter: drop any ref whose regex
# match starts at position 0 of the (Thai-to-arabic-translated, matching
# extract_refs' own internal translation) text AND whose target_matra
# equals the row's own number_arabic. Keep every other ref.
# ======================================================================

def test_to_flat_refs_out_suppresses_self_reference():
    """(a) Self-ref suppression: a node whose text is like
    'มาตรา ๑๓๕/๑ ผู้ใด…' must have NO self-reference to 135/1 in refs_out.
    Uses a real fixture matra (any one whose own heading would otherwise
    self-match, which — pre-fix — is EVERY matra row, e.g. มาตรา ๑)."""
    doc, record = _enriched_code_doc("-63")
    ctx = {
        "law_group_code": record["law_code"],
        "reference_url": record.get("reference_url"),
        "is_latest_computed": True,
    }
    rows = to_flat(doc, ctx)
    matra_1 = next(r for r in rows if r["matra_no_arabic"] == "1")
    assert matra_1["text"].startswith("มาตรา ๑ "), (
        f"expected fixture มาตรา 1 text to start with its own heading, got {matra_1['text'][:30]!r}"
    )
    self_refs = [r for r in matra_1["refs_out"] if r["target_matra"] == "1"]
    assert self_refs == [], (
        f"expected NO self-reference to '1' in มาตรา 1's refs_out, got {self_refs}"
    )


def test_to_flat_refs_out_retains_genuine_midtext_crossref():
    """(b) Retention: a node whose text contains a real cross-ref (e.g.
    '…ให้นำมาตรา ๕๖ แห่งประมวลกฎหมายอาญา มาใช้…') must keep that
    cross-ref — only position-0 self-refs get dropped, not all refs, and
    not refs to other sections found elsewhere in the text.

    Uses a synthetic node (constructed the same shape to_flat already
    consumes) so this test does not depend on which fixture matra happens
    to carry a matching mid-text citation — deterministic and explicit
    about exactly the (a)/(b) contrast the brief specifies.
    """
    doc = {
        "doc_id": "test-doc#doc0",
        "doc_type": "code",
        "title": {"th": "ทดสอบ"},
        "structure": [
            {
                "node_id": "n1", "node_type": "matra", "parent_id": None,
                "number": "๕๗", "number_arabic": "57", "matra_cid": "TEST:57",
                "paragraphs": [{
                    "text": "มาตรา ๕๗ ผู้ใดกระทำการตามที่บัญญัติไว้ ให้นำมาตรา ๕๖ "
                            "แห่งประมวลกฎหมายอาญา มาใช้บังคับโดยอนุโลม",
                }],
            },
        ],
    }
    ctx = {"law_group_code": "TEST", "reference_url": None, "is_latest_computed": True}
    rows = to_flat(doc, ctx)
    assert len(rows) == 1
    row = rows[0]

    self_refs = [r for r in row["refs_out"] if r["target_matra"] == "57"]
    assert self_refs == [], f"self-ref to '57' (own number) must be dropped, got {self_refs}"

    cross_refs = [r for r in row["refs_out"] if r["target_matra"] == "56"]
    assert len(cross_refs) == 1, (
        f"genuine mid-text cross-reference to มาตรา ๕๖ must survive the "
        f"self-ref filter, got refs_out={row['refs_out']}"
    )


def test_to_flat_refs_out_fixture_level_no_self_pollution_but_crossrefs_survive():
    """(c) Fixture-level check: after the fix, run the flat export against
    the fixture code doc (-63) and assert:
      (i) at least one row still has non-empty refs_out (real cross-refs
          exist in the fixture corpus — the filter must not be
          over-aggressive and wipe out genuine references too), and
      (ii) the count of rows where self-reference pollution remains == 0
          across the whole fixture flat output.
    """
    doc, record = _enriched_code_doc("-63")
    ctx = {
        "law_group_code": record["law_code"],
        "reference_url": record.get("reference_url"),
        "is_latest_computed": True,
    }
    rows = to_flat(doc, ctx)
    assert len(rows) > 0

    rows_with_refs = [r for r in rows if r["refs_out"]]
    assert rows_with_refs, (
        "expected at least one row with non-empty refs_out after the fix — "
        "the self-ref filter must not suppress genuine cross-references too"
    )

    polluted = [
        r for r in rows
        if any(ref["target_matra"] == r["matra_no_arabic"] for ref in r["refs_out"])
    ]
    assert len(polluted) == 0, (
        f"expected 0 rows with self-reference pollution remaining, found "
        f"{len(polluted)}: e.g. matra_no_arabic={polluted[0]['matra_no_arabic']!r} "
        f"refs_out={polluted[0]['refs_out']!r}"
    )
