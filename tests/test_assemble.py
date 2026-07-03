"""Cross-record code assembly (src/matra/assemble.py).

Two independent paths to the same truth:
  * a PORTABLE synthetic family (always runs) — gates the cover priority,
    amendment-act exclusion, and anti-contamination guarantees with no corpus;
  * a CORPUS-GUARDED civil golden — proves the real Civil & Commercial Code
    (ป0003-1D-0002) assembles to all 1,755 มาตรา, contiguous, conservation-clean.
"""
import json
import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))
from matra.assemble import (assemble_code, needs_assembly, completeness_of,
                            family_union, matra_numbers, to_int, complete_code_record)
from matra.structure import build_docs_merged
from matra.qa import qa_check, primary_doc


# ---------------------------------------------------------------- unit: completeness
def test_completeness_contiguous():
    c = completeness_of([1, 2, 3, 4, 5])
    assert c == {"present": 5, "min": 1, "max": 5, "contiguous": True, "gaps": []}


def test_completeness_reports_interior_gaps():
    c = completeness_of([1, 2, 5, 6, 10])
    assert c["contiguous"] is False
    assert c["gaps"] == [[3, 4], [7, 9]]


# ---------------------------------------------------------------- portable synthetic family
def _matra(no, text):
    return {"sectionTypeId": 4, "sectionNo": str(no), "content": f"มาตรา {no} {text}"}

def _book_record(tc, doc_title, lo, hi, tag, code_name="ประมวลกฎหมายทดสอบ"):
    # doc_title = the enacting/amendment instrument's own title (section 0);
    # code_name = the canonical CODE name carried in the record's `title` field.
    secs = [{"sectionTypeId": 1, "sectionNo": None, "content": doc_title}]
    secs += [_matra(n, f"{tag} ข้อความมาตรา {n}") for n in range(lo, hi + 1)]
    return {"law_code": "ท0001-1D-0001", "timeline_code": tc, "title": code_name,
            "reference_url": f"http://x/{tc}", "sections": secs}

def _synthetic_family():
    # Two clean code Books (1-50, 51-100) as separate enacting records, PLUS a
    # NEWER amendment act carrying its OWN มาตรา 1-50 that must NOT contaminate.
    return {
        "ท0001-1D-0001-00": _book_record("ท0001-1D-0001-00",
            "พระราชกฤษฎีกา ให้ใช้บทบัญญัติแห่งประมวลกฎหมายทดสอบ", 1, 50, "CODE"),
        "ท0001-1D-0001-01": _book_record("ท0001-1D-0001-01",
            "พระราชกฤษฎีกา ให้ใช้บทบัญญัติ บรรพ ๒ แห่งประมวลกฎหมายทดสอบ", 51, 100, "CODE"),
        "ท0001-1D-0001-09": _book_record("ท0001-1D-0001-09",
            "พระราชบัญญัติ แก้ไขเพิ่มเติมประมวลกฎหมายทดสอบ (ฉบับที่ ๙)", 1, 50, "AMEND"),
    }

def test_needs_assembly_true_when_no_single_record_holds_the_code():
    fam = _synthetic_family()
    assert needs_assembly(fam) is True          # union 100, best single 50
    assert len(family_union(fam)) == 100

def test_needs_assembly_false_for_single_complete_record():
    fam = {"ท0001-1D-0001-00": _book_record("ท0001-1D-0001-00",
           "พระราชกฤษฎีกา ให้ใช้บทบัญญัติแห่งประมวลกฎหมายทดสอบ", 1, 100, "CODE")}
    assert needs_assembly(fam) is False

def test_assembly_covers_union_without_duplication():
    fam = _synthetic_family()
    rec, report = assemble_code(fam, "ท0001-1D-0001")
    assert report["matra_present"] == 100
    assert report["duplicate_matra"] == 0
    assert report["covers_union"] is True
    assert report["completeness"]["contiguous"] is True

def test_amendment_act_excluded_no_contamination():
    """The newer amendment act (-09) has its own มาตรา 1; it must be excluded so
    มาตรา 1 keeps the CODE text, never the amendment's."""
    fam = _synthetic_family()
    rec, report = assemble_code(fam, "ท0001-1D-0001")
    assert "ท0001-1D-0001-09" not in report["source_records_used"]
    m1 = [s for s in rec["sections"] if s.get("sectionTypeId") == 4 and s["sectionNo"] == "1"]
    assert len(m1) == 1 and "CODE" in m1[0]["content"] and "AMEND" not in m1[0]["content"]

def test_assembled_record_builds_code_and_conserves():
    fam = _synthetic_family()
    rec, report = assemble_code(fam, "ท0001-1D-0001")
    docs, flags, merge_report = build_docs_merged(rec)
    qa = qa_check(rec, docs, flags, merge_report)
    assert qa["hard_fail"] is False
    assert primary_doc(docs)["doc_type"] == "code"
    assert sum(1 for n in primary_doc(docs)["structure"] if n["node_type"] == "matra") == 100


# ---------------------------------------------------------------- review-finding regressions
def _code_record(tc, lo, hi, tag, gap=None,
                 doc_title="พระราชกฤษฎีกา ให้ใช้บทบัญญัติแห่งประมวลกฎหมายทดสอบ",
                 code_name="ประมวลกฎหมายทดสอบ"):
    secs = [{"sectionTypeId": 1, "sectionNo": None, "content": doc_title}]
    secs += [_matra(n, f"{tag} txt{n}") for n in range(lo, hi + 1) if n != gap]
    return {"law_code": "ท0009-1D-0001", "timeline_code": tc, "title": code_name,
            "reference_url": "", "sections": secs}

def _act_record(tc, preamble, lo, hi, tag):
    secs = [{"sectionTypeId": 1, "sectionNo": None,
             "content": "พระราชบัญญัติ ให้ใช้บทบัญญัติบรรพ ๙ แห่งประมวลกฎหมายทดสอบ"}]
    secs += [_matra(n, f"ACTPREAMBLE {n}") for n in preamble]
    secs += [_matra(n, f"{tag} txt{n}") for n in range(lo, hi + 1)]
    return {"law_code": "ท0009-1D-0001", "timeline_code": tc, "title": "ประมวลกฎหมายทดสอบ",
            "reference_url": "", "sections": secs}

def test_to_int_handles_all_subnumber_forms():   # I2
    assert to_int("335/1") == 335
    assert to_int("๓๓๕/๑") == 335
    assert to_int("335 ทวิ") == 335
    assert to_int("๓๓๕ ทวิ") == 335
    assert to_int("มาตรา") is None and to_int(None) is None

def test_overlapping_books_never_double_emit():   # C1
    fam = {"ท0009-1D-0001-00": _code_record("ท0009-1D-0001-00", 1, 50, "A"),
           "ท0009-1D-0001-05": _code_record("ท0009-1D-0001-05", 40, 100, "B")}
    rec, rep = assemble_code(fam, "ท0009-1D-0001")
    assert rep["duplicate_matra"] == 0 and rep["matra_present"] == 100
    m45 = [s for s in rec["sections"] if s.get("sectionTypeId") == 4 and s["sectionNo"] == "45"]
    assert len(m45) == 1 and "B" in m45[0]["content"]   # overlap resolved to newer source, once

def test_interior_gap_book_keeps_both_sides():   # C2
    fam = {"ท0009-1D-0001-00": _code_record("ท0009-1D-0001-00", 1, 100, "A", gap=51)}
    rec, rep = assemble_code(fam, "ท0009-1D-0001")
    assert rep["matra_present"] == 99                    # NOT just the longest run (~50)
    assert rep["completeness"]["gaps"] == [[51, 51]]

def test_amendment_reenactment_variant_excluded():   # C3
    fam = {"ท0009-1D-0001-00": _code_record("ท0009-1D-0001-00", 1, 60, "CODE"),
           "ท0009-1D-0001-09": _code_record("ท0009-1D-0001-09", 1, 60, "AMD",
                                             doc_title="ประมวลกฎหมายทดสอบ (ฉบับที่ ๙)")}
    rec, rep = assemble_code(fam, "ท0009-1D-0001")
    assert "ท0009-1D-0001-09" not in rep["source_records_used"]
    m1 = [s for s in rec["sections"] if s.get("sectionTypeId") == 4 and s["sectionNo"] == "1"]
    assert "CODE" in m1[0]["content"] and "AMD" not in m1[0]["content"]

def test_act_preamble_dropped():   # preamble contamination guard
    fam = {"ท0009-1D-0001-00": _act_record("ท0009-1D-0001-00", [1, 2, 3], 500, 600, "BODY")}
    rec, rep = assemble_code(fam, "ท0009-1D-0001")
    nums = {s["sectionNo"] for s in rec["sections"] if s.get("sectionTypeId") == 4}
    assert "1" not in nums and "500" in nums and rep["matra_present"] == 101

def test_assembly_deterministic():   # I3
    fam = _synthetic_family()
    a = assemble_code(fam, "ท0001-1D-0001")[1]["source_records_used"]
    b = assemble_code(fam, "ท0001-1D-0001")[1]["source_records_used"]
    assert a == b

def test_complete_code_record_fills_gap_conservation_safe():   # merge-completion (gap-fill)
    secs = [{"sectionTypeId": 1, "sectionNo": None, "content": "ประมวลกฎหมายทดสอบ"}]
    secs += [_matra(n, f"CODE txt{n}") for n in (1, 2, 3, 4, 6, 7, 8, 9, 10)]   # code missing ม.5
    secs += [{"sectionTypeId": 1, "sectionNo": None,
              "content": "พระราชบัญญัติ แก้ไขเพิ่มเติมประมวลกฎหมายทดสอบ (ฉบับที่ ๒)"},
             _matra(1, "AMEND ชื่อพระราชบัญญัติ"), _matra(2, "AMEND วันใช้บังคับ"),
             _matra(5, "ใหม่แทนที่ของเดิม")]                                      # substantive ม.5 parked here
    rec = {"law_code": "ท0010-1D-0001", "timeline_code": "ท0010-1D-0001-02",
           "title": "ประมวลกฎหมายทดสอบ", "reference_url": "", "sections": secs}
    new, filled = complete_code_record(rec)
    assert filled == [5]
    assert len(new["sections"]) == len(rec["sections"])          # relocated, not dropped/duplicated
    docs, fl, mr = build_docs_merged(new)
    qa = qa_check(new, docs, fl, mr)
    assert qa["hard_fail"] is False and qa["checks"]["char_roundtrip_delta_pct"] == 0.0
    code = primary_doc(docs)
    bases = {to_int(n.get("number_arabic")) for n in code["structure"] if n["node_type"] == "matra"}
    assert {1, 2, 3, 4, 5, 6, 7, 8, 9, 10} <= bases              # code body now navigable-complete
    m5 = [n for n in code["structure"] if n["node_type"] == "matra" and to_int(n.get("number_arabic")) == 5]
    assert m5 and "ใหม่แทนที่" in m5[0]["paragraphs"][0]["text"]  # the substantive donor, in place


# ---------------------------------------------------------------- corpus-guarded civil golden
def _resolve_corpus_dirs():
    dirs = []
    for env in ("MATRA_CORPUS_DL", "MATRA_CORPUS_RAW"):
        v = os.environ.get(env)
        if v and pathlib.Path(v).is_dir():
            dirs.append(pathlib.Path(v))
    for pat in ("*/mnt/.aice/legalrag/work/sampling_dl", "*/mnt/.aice/legalrag/raw"):
        dirs += [p for p in sorted(pathlib.Path("/sessions").glob(pat)) if p.is_dir()]
    home = pathlib.Path.home() / ".aice/legalrag/work/sampling_dl"
    if home.is_dir():
        dirs.append(home)
    return dirs

def _load_civil():
    recs = {}
    for d in _resolve_corpus_dirs():
        for f in sorted(d.glob("*.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("law_code") == "ป0003-1D-0002":
                    recs[r.get("timeline_code")] = r
    return recs

CIVIL = _load_civil()
requires_civil = pytest.mark.skipif(len(CIVIL) < 6, reason="civil corpus (ป0003-1D-0002) not present")

@requires_civil
def test_civil_is_fragmented():
    assert needs_assembly(CIVIL) is True
    assert len(family_union(CIVIL)) == 1755
    assert max(len(matra_numbers(r)) for r in CIVIL.values()) == 845   # fullest single = บรรพ 3 only

@requires_civil
def test_civil_assembles_to_all_1755_clean():
    rec, report = assemble_code(CIVIL, "ป0003-1D-0002")
    assert report["matra_present"] == 1755
    assert report["duplicate_matra"] == 0
    assert report["covers_union"] is True
    assert report["completeness"] == {"present": 1755, "min": 1, "max": 1755,
                                       "contiguous": True, "gaps": []}
    # clean cover: original books + revised-Book-5 code doc; the contaminated
    # act-form revised Book 1 (-37) and older Book-5 (-13) must lose the cover.
    used = set(report["source_records_used"])
    assert used == {"ป0003-1D-0002-00", "ป0003-1D-0002-01", "ป0003-1D-0002-03",
                    "ป0003-1D-0002-31", "ป0003-1D-0002-15"}

@requires_civil
def test_civil_matra1_is_code_not_amendment():
    rec, _ = assemble_code(CIVIL, "ป0003-1D-0002")
    m1 = [s for s in rec["sections"] if s.get("sectionTypeId") == 4 and s.get("sectionNo") == "1"]
    assert len(m1) == 1
    assert "ให้เรียกว่า ประมวลกฎหมายแพ่งและพาณิชย์" in m1[0]["content"]
    assert "พระราชบัญญัตินี้เรียกว่า" not in m1[0]["content"]

@requires_civil
def test_civil_assembled_builds_code_and_conserves():
    rec, _ = assemble_code(CIVIL, "ป0003-1D-0002")
    docs, flags, merge_report = build_docs_merged(rec)
    qa = qa_check(rec, docs, flags, merge_report)
    assert qa["hard_fail"] is False
    assert qa["checks"]["char_roundtrip_delta_pct"] == 0.0
    code = primary_doc(docs)
    assert code["doc_type"] == "code"
    # 1,755 base มาตรา + 41 ทวิ/ตรี sub-numbered forms = 1,796 distinct matra nodes;
    # completeness is measured on the 1,755 base numbers (see report.completeness).
    assert sum(1 for n in code["structure"] if n["node_type"] == "matra") == 1796
