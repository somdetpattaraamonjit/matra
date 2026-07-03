import json
import pathlib

import matra
from matra.qa import qa_check, primary_doc

FIX = pathlib.Path(__file__).parent / "fixtures/gate_regressions"

TIMELINE_CODES = [
    "ว0018-1B-0017-01",
    "ว0020-1B-0003-07",
    "ว0025-1B-0001-00",
    "อท019-1B-0001-00",
]

EMPTY_TIMELINE_CODE = "ก0016-1B-0001-16"  # real record, sections: [] (Task 3.5)


def _record(timeline_code):
    path = FIX / f"{timeline_code}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _run(timeline_code):
    record = _record(timeline_code)
    docs, flags = matra.normalize_record(record)
    result = qa_check(record, docs, flags)
    return record, docs, flags, result


def test_all_4_gate_regressions_pass_conservation():
    """Every one of the 4 groups the 2026-07-02 sampling gate failed must now
    pass qa_check hard_fail honestly (nothing dropped, everything counted)."""
    for tl in TIMELINE_CODES:
        _, _, _, result = _run(tl)
        assert result["hard_fail"] is False, f"{tl}: hard_fail True, checks={result['checks']}"


def test_v0025_bot_node_and_quarantined_unknown_20():
    """ว0025-1B-0001-00 has typeId 13 (บทเฉพาะกาล) + typeId 20 (junk). typeId 13
    must become a displayed 'bot' container that pops the whole hierarchy stack
    (parents directly under doc root) with subsequent มาตรา parented to it; the
    TOC must carry the bot entry; typeId 20 must be quarantined (hidden)."""
    record, docs, flags, result = _run("ว0025-1B-0001-00")
    assert result["hard_fail"] is False, result["checks"]

    code = max(docs, key=lambda d: (d["doc_type"] == "code",
                                     sum(1 for n in d["structure"] if n["node_type"] == "matra")))
    structure = code["structure"]

    bot_nodes = [n for n in structure if n["node_type"] == "bot"]
    assert len(bot_nodes) == 1, f"expected exactly one bot node, got {len(bot_nodes)}"
    bot = bot_nodes[0]
    assert bot["display"] is True
    assert "บทเฉพาะกาล" in (bot["heading"] or "")

    # at least one matra node after it parents to the bot node
    bot_order = bot["order"]
    later_matra = [n for n in structure if n["node_type"] == "matra" and n["order"] > bot_order]
    assert later_matra, "no matra nodes found after the bot node"
    assert any(n["parent_id"] == bot["node_id"] for n in later_matra), \
        "no matra node after บทเฉพาะกาล parents to the bot node"

    # its unknown_20 node is quarantined (hidden)
    unknown_20_nodes = [n for n in structure if n["node_type"] == "unknown_20"]
    assert len(unknown_20_nodes) == 1, f"expected exactly one unknown_20 node, got {len(unknown_20_nodes)}"
    assert unknown_20_nodes[0]["display"] is False

    # TOC contains the bot entry
    toc = matra.structure.toc_of(code)
    assert any(t["level"] == "bot" for t in toc), f"TOC missing bot entry: {toc}"


def test_v0018_two_unknown_18_quarantined_content_preserved():
    """ว0018-1B-0017-01 (typeId 18 x2) — quarantined, content preserved verbatim,
    charΔ stays within tolerance now that both lanes are counted."""
    record, docs, flags, result = _run("ว0018-1B-0017-01")
    assert result["hard_fail"] is False, result["checks"]

    unknown_18_nodes = [n for d in docs for n in d["structure"] if n["node_type"] == "unknown_18"]
    assert len(unknown_18_nodes) == 2, f"expected two unknown_18 nodes, got {len(unknown_18_nodes)}"
    for n in unknown_18_nodes:
        assert n["display"] is False
        paras = n.get("paragraphs", [])
        assert paras and paras[0]["text"].strip(), "unknown_18 content must be preserved, non-empty"

    assert result["checks"]["char_roundtrip_delta_pct"] <= 0.5


def test_v0020_four_unknown_20_quarantined_ledger_balanced():
    """ว0020-1B-0003-07 (typeId 20 x4, junk figure-space rows) — all quarantined,
    hidden, and the quarantine ledger balances rows_in == rows_out == 4."""
    record, docs, flags, result = _run("ว0020-1B-0003-07")
    assert result["hard_fail"] is False, result["checks"]

    unknown_20_nodes = [n for d in docs for n in d["structure"] if n["node_type"] == "unknown_20"]
    assert len(unknown_20_nodes) == 4, f"expected four unknown_20 nodes, got {len(unknown_20_nodes)}"
    for n in unknown_20_nodes:
        assert n["display"] is False

    q = result["checks"]["quarantine"]
    assert q["rows_in"] == q["rows_out"] == 4, f"quarantine ledger not balanced: {q}"


def test_att019_hard_fail_false_quarantine_balanced():
    """อท019-1B-0001-00 (typeId 20 x1) — hard_fail False, quarantine ledger balanced."""
    record, docs, flags, result = _run("อท019-1B-0001-00")
    assert result["hard_fail"] is False, result["checks"]

    q = result["checks"]["quarantine"]
    assert q["rows_in"] == q["rows_out"], f"quarantine ledger not balanced: {q}"


def test_muad_after_bot_ordering_edge():
    """Synthetic test: หมวด ๑ then มาตรา under it, then บทเฉพาะกาล (bot), then มาตรา
    under bot, then หมวด ๒ after bot. Verify:
    - matra after bot has parent_id == bot node_id (bot's child)
    - หมวด after bot has parent_id None (new top-level sibling, NOT bot's child)
    - bot node itself: display True, parent_id None
    """
    # Build synthetic record with specific typeId sequence
    record = {
        "law_code": "ทดสอบ",
        "timeline_code": "ทดสอบ-1B-0001-00",
        "title": "พระราชบัญญัติทดสอบ",
        "category": "code",
        "filename": "synthetic_test.jsonl",
        "is_latest": True,
        "reference_url": "http://example.com",
        "publish_date": "2026-01-01",
        "year": 2026,
        "month": 1,
        "sections": [
            {"sectionId": 1, "sectionTypeId": 1, "contentNo": 1, "content": "พระราชบัญญัติทดสอบ"},
            {"sectionId": 2, "sectionTypeId": 8, "sectionNo": "1", "contentNo": 1, "sectionName": "หมวด ๑", "content": "หมวด ๑ ความผิดต่อชีวิต"},
            {"sectionId": 3, "sectionTypeId": 4, "sectionNo": "1", "contentNo": 1, "content": "มาตรา ๑ text under หมวด ๑"},
            {"sectionId": 4, "sectionTypeId": 13, "contentNo": 1, "content": "บทเฉพาะกาล"},
            {"sectionId": 5, "sectionTypeId": 4, "sectionNo": "99", "contentNo": 1, "content": "มาตรา ๙๙ text under bot"},
            {"sectionId": 6, "sectionTypeId": 8, "sectionNo": "2", "contentNo": 1, "sectionName": "หมวด ๒", "content": "หมวด ๒ ความผิดต่อร่างกาย"},
        ]
    }

    docs, flags = matra.normalize_record(record)
    assert len(docs) > 0, "normalize_record should produce at least one doc"

    doc = docs[0]
    structure = doc["structure"]

    # Find the bot node (should be exactly one, typeId 13)
    bot_nodes = [n for n in structure if n["node_type"] == "bot"]
    assert len(bot_nodes) == 1, f"expected exactly one bot node, got {len(bot_nodes)}"
    bot = bot_nodes[0]
    assert bot["display"] is True, "bot node should have display=True"
    assert bot["parent_id"] is None, "bot node should have parent_id=None (top-level)"

    # Find the matra nodes
    matra_nodes = [n for n in structure if n["node_type"] == "matra"]
    assert len(matra_nodes) >= 2, f"expected at least 2 matra nodes, got {len(matra_nodes)}"

    # First muad (หมวด ๑)
    muad_1 = [n for n in structure if n["node_type"] == "muad"]
    assert len(muad_1) >= 1, "should have at least one muad node"

    # Matra after bot should parent to bot
    bot_order = bot["order"]
    matra_after_bot = [n for n in matra_nodes if n["order"] > bot_order]
    assert matra_after_bot, "should have matra nodes after bot"
    for m in matra_after_bot:
        assert m["parent_id"] == bot["node_id"], \
            f"matra after bot (order {m['order']}) should parent to bot (id {bot['node_id']}), got parent_id={m['parent_id']}"

    # Second muad (หมวด ๒) after bot should be top-level (parent_id=None), not child of bot
    muad_2 = [n for n in structure if n["node_type"] == "muad" and n["order"] > bot_order]
    assert len(muad_2) == 1, f"expected exactly one muad after bot, got {len(muad_2)}"
    m2 = muad_2[0]
    assert m2["parent_id"] is None, \
        f"หมวด ๒ after bot should be top-level (parent_id=None), got parent_id={m2['parent_id']}"


def test_primary_doc_returns_none_for_empty_docs():
    """primary_doc([]) must return None, not crash with max() arg is an
    empty sequence (Task 3.5 — population-scale sampling gate finding)."""
    assert primary_doc([]) is None


def test_empty_sections_record_no_crash_flagged_not_silent():
    """ก0016-1B-0001-16 (real record, sections: []) must not crash qa_check.
    Berkson rule: visible, never silent, never crash. Conservation math runs
    with 0 rows both lanes (0==0, hard_fail stays False), a review flag
    reason=='empty_record' is appended so it's COUNTED (not vacuously PASS
    like the old silent engine gate), and code_tree/matra_nodes_code read as
    empty/zero since there is no primary doc."""
    record = _record(EMPTY_TIMELINE_CODE)
    assert record["sections"] == [], "fixture must be the real empty-sections record"

    docs, flags = matra.normalize_record(record)
    assert docs == [] and flags == [], "sanity: confirms normalize_record's ([], []) for this record"

    result = qa_check(record, docs, flags)  # must not raise

    assert result["hard_fail"] is False, result["checks"]

    checks = result["checks"]
    assert checks["rows_in_vs_out"] == (0, 0, True)
    assert checks["char_roundtrip_delta_pct"] == 0.0
    assert checks["code_tree"] in ({}, {lv: 0 for lv in matra.structure.HIER_LEVELS})
    assert checks["matra_nodes_code"] == 0
    assert checks["docs_split"] == 0
    assert checks["quarantine"]["rows_in"] == checks["quarantine"]["rows_out"] == 0

    empty_flags = [f for f in result["flags"] if f.get("reason") == "empty_record"]
    assert len(empty_flags) == 1, f"expected exactly one empty_record flag, got {result['flags']}"
