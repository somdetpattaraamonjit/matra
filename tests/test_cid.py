# Task 6′ — src/matra/cid.py: matra_cid + eId/wId + extract_refs (pure functions)
#
# Design decisions binding this file (docs/akn_adoption_verdicts.md §Design
# decisions 1-5, Lindy Gate run 2026-07-02):
#   1. matra_cid = f"{law_group_code}:{number_arabic}" VERBATIM — never
#      normalize inside cid (spaces/Thai suffix survive, e.g. "335 ทวิ").
#   2. eId = ASCII structural id, AKN element names (matra->art, phak->part,
#      laksana->title, muad->chapter, suan->subchapter, kho->clause,
#      bot->transitional). Containers hierarchically qualified
#      (part_2__title_1_1) because ลักษณะ numbering restarts per ภาค; matra
#      unqualified (art_135_1) because มาตรา numbers are continuous per doc.
#   3. eId collisions (real digit-defect case, sectionId 6466038, puts a
#      second title_1 under part_2 in -63): deterministic __d2/__d3 suffix in
#      order-order + eid_collision flag on the later node.
#   4. wId = eId at first assignment (v0: wId == eId).
#   5. Schema delta: structure.items.properties += optional eId, wId.
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

from matra.cid import assign_cids, assign_eids, extract_refs
from matra.structure import build_docs
from matra.qa import primary_doc

FIX = pathlib.Path(__file__).parent / "fixtures/criminal_code_sample.jsonl"


def _fixture_records():
    return [json.loads(l) for l in FIX.read_text(encoding="utf-8").splitlines() if l.strip()]


# ======================================================================
# Test 1 (plan-mandated): basic matra_cid assignment
# ======================================================================
def test_assign_cids_basic_plan_mandated():
    nodes = [{"node_type": "matra", "number_arabic": "90/1"}]
    out = assign_cids(nodes, "ป0006-1D-0003")
    assert out[0]["matra_cid"] == "ป0006-1D-0003:90/1"


# ======================================================================
# Test 2: verbatim space+Thai suffix survives inside matra_cid (never
# normalized — that normalization only happens inside eId, not cid).
# ======================================================================
def test_assign_cids_verbatim_space_and_thai_suffix():
    nodes = [{"node_type": "matra", "number_arabic": "335 ทวิ"}]
    out = assign_cids(nodes, "ป0006-1D-0003")
    assert out[0]["matra_cid"] == "ป0006-1D-0003:335 ทวิ"


# ======================================================================
# Test 3: non-matra nodes get NO matra_cid key at all (not None — absent).
# ======================================================================
def test_assign_cids_non_matra_nodes_get_no_key():
    nodes = [
        {"node_type": "phak", "number_arabic": "1"},
        {"node_type": "laksana", "number_arabic": "2"},
    ]
    out = assign_cids(nodes, "ป0006-1D-0003")
    for n in out:
        assert "matra_cid" not in n


# ======================================================================
# Test 4: eId forms — matra normalization (slash->underscore, Thai suffix
# word -> bis/ter/quater) and hierarchically-qualified container id.
# ======================================================================
def test_assign_eids_matra_forms():
    nodes = [
        {"node_id": "n1", "node_type": "matra", "number_arabic": "135/1", "parent_id": None},
        {"node_id": "n2", "node_type": "matra", "number_arabic": "335 ทวิ", "parent_id": None},
    ]
    out = assign_eids(nodes)
    by_id = {n["node_id"]: n for n in out}
    assert by_id["n1"]["eId"] == "art_135_1"
    assert by_id["n2"]["eId"] == "art_335_bis"


def test_assign_eids_full_suffix_set_no_silent_sanitize():
    # Review 6' Minor #2: structure.py recognizes suffix words beyond the 3
    # originally-profiled ones; every one must map, never silently sanitize.
    cases = {"335 เบญจ": "art_335_quinquies", "335 ฉ": "art_335_sexies",
             "335 สัตต": "art_335_septies", "335 อัฏฐ": "art_335_octies",
             "335 นว": "art_335_novies", "335 ทศ": "art_335_decies"}
    for raw, want in cases.items():
        out = assign_eids([{"node_id": "n1", "node_type": "matra",
                            "number_arabic": raw, "parent_id": None}])
        assert out[0]["eId"] == want, (raw, out[0]["eId"])
        assert not out[0].get("eid_sanitized"), f"{raw} silently sanitized"


def test_assign_eids_container_hierarchically_qualified():
    # laksana "1/1" under phak "2" -> part_2__title_1_1
    nodes = [
        {"node_id": "p1", "node_type": "phak", "number_arabic": "2", "parent_id": None},
        {"node_id": "l1", "node_type": "laksana", "number_arabic": "1/1", "parent_id": "p1"},
    ]
    out = assign_eids(nodes)
    by_id = {n["node_id"]: n for n in out}
    assert by_id["p1"]["eId"] == "part_2"
    assert by_id["l1"]["eId"] == "part_2__title_1_1"


# ======================================================================
# Test 5: collision handling — two laksana number "1" under the same phak
# must get distinct eIds; the second (in order-order) gets a deterministic
# __d2 suffix and an eid_collision flag. Original number/number_arabic must
# NOT be mutated (conservation law).
# ======================================================================
def test_assign_eids_collision_gets_distinct_ids_and_flag():
    nodes = [
        {"node_id": "p1", "node_type": "phak", "number_arabic": "2", "parent_id": None, "order": 1},
        {"node_id": "l1", "node_type": "laksana", "number_arabic": "1", "parent_id": "p1", "order": 2},
        # decoy/defect: a SECOND laksana "1" under the same phak, appearing
        # later in order (real case: digit-defect sectionId 6466038 in -63)
        {"node_id": "l2", "node_type": "laksana", "number_arabic": "1", "parent_id": "p1", "order": 3},
    ]
    out = assign_eids(nodes)
    by_id = {n["node_id"]: n for n in out}

    assert by_id["l1"]["eId"] == "part_2__title_1"
    assert by_id["l2"]["eId"] == "part_2__title_1__d2"
    assert by_id["l2"]["eid_collision"] is True
    assert "eid_collision" not in by_id["l1"]
    # conservation law: never mutate number_arabic on the flagged node
    assert by_id["l2"]["number_arabic"] == "1"


# ======================================================================
# Test 6: wId == eId for every node that got an eId assigned.
# ======================================================================
def test_assign_eids_wid_equals_eid():
    nodes = [
        {"node_id": "p1", "node_type": "phak", "number_arabic": "2", "parent_id": None, "order": 1},
        {"node_id": "m1", "node_type": "matra", "number_arabic": "50", "parent_id": "p1", "order": 2},
    ]
    out = assign_eids(nodes)
    for n in out:
        if n.get("eId") is not None:
            assert n["wId"] == n["eId"]


# ======================================================================
# eId skip rule: nodes with number_arabic None/empty (promulgation, recital,
# paragraph rows...) get eId = None, skipped silently (no eid_sanitized /
# eid_collision flag).
# ======================================================================
def test_assign_eids_none_number_arabic_skips_silently():
    nodes = [
        {"node_id": "r1", "node_type": "recital", "number_arabic": None, "parent_id": None},
        {"node_id": "r2", "node_type": "promulgation", "number_arabic": "", "parent_id": None},
    ]
    out = assign_eids(nodes)
    by_id = {n["node_id"]: n for n in out}
    assert by_id["r1"]["eId"] is None
    assert by_id["r2"]["eId"] is None
    assert "eid_sanitized" not in by_id["r1"]
    assert "eid_collision" not in by_id["r1"]


# ======================================================================
# eid_sanitized flag: residual non-[A-Za-z0-9_] characters get dropped and
# flagged (distinct from the collision flag).
# ======================================================================
def test_assign_eids_sanitizes_residual_chars_and_flags():
    nodes = [
        {"node_id": "n1", "node_type": "matra", "number_arabic": "90-ก", "parent_id": None},
    ]
    out = assign_eids(nodes)
    n = out[0]
    assert n["eId"] is not None
    assert set(n["eId"]) <= set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
    assert n["eid_sanitized"] is True
    assert n["number_arabic"] == "90-ก"  # never mutated


# ======================================================================
# Test 7 (plan-mandated): extract_refs finds a มาตรา + แห่ง reference.
# ======================================================================
def test_extract_refs_finds_matra_and_law_reference():
    text = "ให้นำมาตรา ๕๖ แห่งประมวลกฎหมายอาญา มาใช้บังคับ"
    refs = extract_refs(text)
    assert len(refs) == 1
    assert refs[0]["target_matra"] == "56"
    assert "อาญา" in refs[0]["target_doc"]


# ======================================================================
# Test 8: no-overmatch — text without มาตรา references returns [].
# ======================================================================
def test_extract_refs_no_overmatch_returns_empty():
    text = "ผู้ใดเอาทรัพย์ของผู้อื่นไปโดยทุจริต ผู้นั้นกระทำความผิดฐานลักทรัพย์"
    assert extract_refs(text) == []


# ======================================================================
# extract_refs: matra reference WITHOUT a แห่ง<law> suffix still matches,
# target_doc is None (the "with optional แห่ง<law>" contract).
# ======================================================================
def test_extract_refs_without_haeng_law_suffix():
    text = "ตามมาตรา 335 ทวิ ที่กล่าวมาข้างต้น"
    refs = extract_refs(text)
    assert len(refs) == 1
    assert refs[0]["target_matra"] == "335 ทวิ"
    assert refs[0]["target_doc"] is None


# ======================================================================
# extract_refs: Thai-digit reference is translated to arabic in target_matra.
# ======================================================================
def test_extract_refs_thai_digit_translated_to_arabic():
    text = "มาตรา ๑๓๕/๑ บัญญัติไว้"
    refs = extract_refs(text)
    assert len(refs) == 1
    assert refs[0]["target_matra"] == "135/1"


# ======================================================================
# Test 9 (falsification test — MANDATORY): cid-stability across versions.
# Load BOTH fixture records, build code-doc nodes for each via the real
# pipeline API (matra.structure.build_docs + matra.qa.primary_doc — the same
# path tests/test_e2e_criminal63.py and tests/test_merge_synthetic_fixture.py
# use), assign cids with the SAME law_group_code; intersect matra
# number_arabic sets; assert intersection >= 10 AND every common number gets
# an IDENTICAL cid in -00 and -63.
# ======================================================================
def test_cid_stability_across_versions_falsification():
    records = _fixture_records()
    r00 = next(r for r in records if r["timeline_code"].endswith("-00"))
    r63 = next(r for r in records if r["timeline_code"].endswith("-63"))
    assert r00["law_code"] == r63["law_code"] == "ป0006-1D-0003"
    law_group_code = r00["law_code"]

    docs00, _flags00 = build_docs(r00, merge=False)
    docs63, _flags63 = build_docs(r63, merge=False)
    code00 = primary_doc(docs00)
    code63 = primary_doc(docs63)
    assert code00 is not None and code63 is not None

    nodes00 = assign_cids(code00["structure"], law_group_code)
    nodes63 = assign_cids(code63["structure"], law_group_code)

    matra00 = {n["number_arabic"]: n["matra_cid"] for n in nodes00 if n["node_type"] == "matra"}
    matra63 = {n["number_arabic"]: n["matra_cid"] for n in nodes63 if n["node_type"] == "matra"}

    common = set(matra00) & set(matra63)
    assert len(common) >= 10, f"expected >=10 common matra numbers, got {len(common)}: {sorted(common)}"
    for number in common:
        assert matra00[number] == matra63[number] == f"{law_group_code}:{number}", (
            f"cid instability for matra {number!r}: -00={matra00[number]!r} -63={matra63[number]!r}"
        )


# ======================================================================
# Test 10: schema — eId/wId present in structure.items.properties (optional,
# ["string","null"]); existing minimal_doc fixture still validates (fields
# are additive/optional, so a doc predating this task keeps validating).
# ======================================================================
def test_schema_has_eid_wid_and_minimal_doc_still_validates():
    from jsonschema import Draft202012Validator

    schema_path = pathlib.Path(__file__).parents[1] / "schemas/matra-0.2.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    node_props = schema["properties"]["structure"]["items"]["properties"]

    assert node_props["eId"]["type"] == ["string", "null"]
    assert node_props["wId"]["type"] == ["string", "null"]

    doc = json.loads((pathlib.Path(__file__).parent / "fixtures/minimal_doc.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(doc)
