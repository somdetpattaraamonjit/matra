#!/usr/bin/env python3
"""Task 4'.1 -- amendment-directive grammar survey scanner (Matra project).

Read-only, idempotent, pure stdlib + matra package. Never writes to any path
under raw/ or sampling_dl/. Produces a single JSON report (stdout, and a copy
to /tmp/matra_survey_output.json for the report-writing step) that every
number in docs/merge_grammar.md and docs/merge_answer_key.md is derived from.

Run: cd <matra repo root> && python3 docs/survey_scan.py

What this script does, in order:
  1. Load the -63 record from the criminal-code group file, filtered
     explicitly by timeline_code (never assume position/line-index).
  2. Split it into docs (matra.splitter.split_record -- the RAW row-level
     API, not the tree-built normalize_record, because recital/remark rows
     that the tree stage demotes are exactly where directive language lives).
  3. Scan every amendment-act doc (doc index >= 2, i.e. everything after the
     code doc at index 1) for directive-verb patterns, with row context.
  4. Collect all laksana (typeId 7) AND muad/phak heading rows in
     doc-then-row order across the whole -63 record (code doc + every
     amendment act) for the digit-fidelity probe -- since golden targets
     show laksana/muad headings get INJECTED by amendment acts, not just
     living in the base code doc.
  5. Also scan the raw source_toc (typeId 16, DISCARDed by the pipeline)
     rows of the code doc for internal numbering cross-checks (this is what
     surfaces the digit-fidelity defect -- see report).
  6. Run the same verb-pattern scan across all sampling_dl/*.jsonl files'
     non-code docs.
  7. Locate the 4 golden targets by mapping their known matra numbers to the
     amendment-act doc that contains them, then pull that doc's full row
     dump, heading row, and payload row stats (count + char length).
  8. Detect true matra-number gaps (missing consecutive integers) inside
     each -63 amendment-act doc's matra rows, to check finding #4 (directive
     sentence absence correlates with a raw-source row gap) systematically
     across all 32 acts, not just the terrorism (kokankai) example.

Every regex used below is documented next to its definition so a future
reader can see exactly what counted as a "hit" -- per the brief's method
rule ("no LLM-imagination of legal formulas", "every claim carries a
row-level example").
"""
import glob
import json
import os
import pathlib
import re
import sys

# Portable paths — no machine-specific session path hard-coded (Task 4'.2 review
# Finding 2). The matra src dir is derived from THIS file's own location (docs/
# is a sibling of src/ in the repo). Corpus + sampling dir resolve via env →
# ~/.aice/legalrag → any /sessions/*/mnt Cowork mount (glob, portable across
# future session names).
MATRA_SRC = str(pathlib.Path(__file__).resolve().parents[1] / "src")
sys.path.insert(0, MATRA_SRC)
from matra.splitter import split_record, clean, TYPE_MAP  # noqa: E402


def _resolve_corpus():
    """Path to 1956-11.jsonl: env MATRA_CORPUS (file or dir) → ~/.aice/legalrag/
    raw/1956-11.jsonl → glob /sessions/*/mnt/.aice/legalrag/raw/1956-11.jsonl."""
    env = os.environ.get("MATRA_CORPUS")
    if env:
        p = pathlib.Path(env)
        if p.is_dir():
            p = p / "1956-11.jsonl"
        if p.exists():
            return str(p)
    home = pathlib.Path.home() / ".aice/legalrag/raw/1956-11.jsonl"
    if home.exists():
        return str(home)
    for match in sorted(pathlib.Path("/sessions").glob("*/mnt/.aice/legalrag/raw/1956-11.jsonl")):
        return str(match)
    return str(home)


def _resolve_sampling_dir():
    """Dir holding sampling_dl/*.jsonl: env MATRA_SAMPLING_DIR → ~/.aice/legalrag/
    work/sampling_dl → glob /sessions/*/mnt/.aice/legalrag/work/sampling_dl."""
    env = os.environ.get("MATRA_SAMPLING_DIR")
    if env and pathlib.Path(env).is_dir():
        return env
    home = pathlib.Path.home() / ".aice/legalrag/work/sampling_dl"
    if home.is_dir():
        return str(home)
    for match in sorted(pathlib.Path("/sessions").glob("*/mnt/.aice/legalrag/work/sampling_dl")):
        return str(match)
    return str(home)


RAW_63_PATH = _resolve_corpus()
SAMPLING_DIR = _resolve_sampling_dir()
TARGET_TIMELINE = "ป0006-1D-0003-63"

OUT_JSON = "/tmp/matra_survey_output.json"

# ---------------------------------------------------------------------------
# Directive-verb pattern inventory.
#
# Seed list from the brief + prior scans (ให้เพิ่มความ, ให้ยกเลิกความ,
# ให้ยกเลิก, และให้ใช้ความต่อไปนี้แทน, ให้เพิ่ม, ให้แก้ไขเพิ่มเติม),
# EXPANDED per the task instructions to also catch: ตัด/แทรก/เปลี่ยน/ปรับ,
# and anything ending in "แทน" or starting with "ให้" near a
# มาตรา/ลักษณะ/หมวด/วรรค token. Each pattern is a (family_name, regex)
# pair; regex is intentionally loose (verb phrase only, not the full
# formula) so scan_row_for_directives() can report every candidate hit with
# surrounding context, and the human-authored .md files then classify hits
# into formula families using the row text itself (never invented).
# ---------------------------------------------------------------------------
DIRECTIVE_VERB_PATTERNS = [
    ("ADD_khwaam", re.compile(r"ให้เพิ่มความต่อไปนี้เป็น")),
    ("ADD_generic", re.compile(r"ให้เพิ่ม(?!เติมประมวล)")),  # exclude boilerplate title-verb "แก้ไขเพิ่มเติมประมวลกฎหมาย..."
    ("REPLACE_yoklerk_khwaam_taen", re.compile(r"ให้ยกเลิกความ.*?และให้ใช้ความต่อไปนี้แทน", re.S)),
    ("REPLACE_taen_generic", re.compile(r"แทน(?:ความเดิม)?(?:$|[^ก-ู])")),  # rows ending in/containing "taen" as replacement marker
    ("REPEAL_yoklerk", re.compile(r"ให้ยกเลิก(?!ความ)")),
    ("AMEND_kaekhai_permtoem", re.compile(r"ให้แก้ไขเพิ่มเติม")),
    ("EDIT_tat", re.compile(r"ให้ตัด")),
    ("EDIT_saek", re.compile(r"ให้แทรก")),
    ("EDIT_plian", re.compile(r"ให้เปลี่ยน")),
    ("EDIT_prap", re.compile(r"ให้ปรับ")),
    ("GIVEN_near_anchor", re.compile(r"ให้[ก-ู]{0,20}(?:มาตรา|ลักษณะ|หมวด|วรรค)")),
]

# Anchor-token detector used to report which structural level a directive
# targets (laksana/muad = structure-level, matra = section-level,
# waraк = paragraph-level) -- reported alongside every hit.
ANCHOR_RE = re.compile(r"(ลักษณะ|หมวด|วรรค|มาตรา)\s*([๐-๙0-9/]+)?")

THAI_DIGIT_MAP = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def thai_to_int(s):
    """Convert a Thai-numeral matra number like the ticket 135/1 main
    integer part to an int for gap detection. Returns None if not parseable
    as a plain integer (e.g. keeps tawi/tri suffixed or slash-inserted
    numbers out of the gap check, matching the brief's 'only flag TRUE
    gaps' instruction).
    """
    if s is None:
        return None
    s2 = s.translate(THAI_DIGIT_MAP).strip()
    if re.fullmatch(r"\d+", s2):
        return int(s2)
    return None


def load_rec63():
    with open(RAW_63_PATH, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("timeline_code") == TARGET_TIMELINE:
                return rec
    raise RuntimeError(f"timeline_code {TARGET_TIMELINE} not found in {RAW_63_PATH}")


def scan_row_for_directives(row_text):
    """Return a list of {family, span_text} for every directive-verb pattern
    that matches this row's cleaned content. span_text is a short excerpt
    around the match for context (not the whole row, which can be 1000+
    chars for payload matra rows).
    """
    hits = []
    for family, pat in DIRECTIVE_VERB_PATTERNS:
        for m in pat.finditer(row_text):
            start = max(0, m.start() - 15)
            end = min(len(row_text), m.end() + 60)
            hits.append({"family": family, "match": m.group(0), "context": row_text[start:end]})
    return hits


def scan_doc_rows(doc, doc_idx, source_label):
    """Scan every row of one split_record doc for directive-verb hits.
    Returns list of hit records with full locator (source, doc_idx, row i,
    row type, sectionNo, verbatim context)."""
    out = []
    for r in doc["rows"]:
        hits = scan_row_for_directives(r["c"])
        for h in hits:
            out.append({
                "source": source_label,
                "doc_idx": doc_idx,
                "doc_title": doc["title"],
                "row_i": r["i"],
                "row_type": r["t"],
                "row_no": r["no"],
                "family": h["family"],
                "match": h["match"],
                "context": h["context"],
            })
    return out


def find_matra_gaps(doc):
    """Collect all sectionNo values under rows with t=='matra' in this doc,
    in row order, dedup consecutive repeats (a matra can span multiple raw
    rows -- waraк continuation rows share the same sectionNo). Then find
    TRUE gaps: consecutive plain-integer sectionNos where an integer is
    skipped. tawi/tri-suffixed or slash-inserted (e.g. 135/1) numbers are
    excluded from the integer gap check (expected insertions, not gaps)
    but kept in the ordered list for the report.
    """
    seen_order = []
    for r in doc["rows"]:
        if r["t"] != "matra":
            continue
        no = r["no"]
        if not seen_order or seen_order[-1] != no:
            seen_order.append(no)
    ints = [(no, thai_to_int(no)) for no in seen_order]
    plain_ints = [v for _, v in ints if v is not None]
    gaps = []
    for i in range(1, len(plain_ints)):
        prev, cur = plain_ints[i - 1], plain_ints[i]
        if cur - prev > 1:
            gaps.append({"after": prev, "before": cur, "missing": list(range(prev + 1, cur))})
    return {"matra_sequence": seen_order, "gaps": gaps}


def collect_structure_headings(docs, types=("phak", "laksana", "muad")):
    """Collect phak/laksana/muad heading rows across ALL docs (code doc +
    every amendment act) in doc-then-row order, since golden targets show
    laksana/muad headings get injected by amendment acts, not just living
    in the base code doc. Returns list with full locator + verbatim text.
    """
    out = []
    for di, d in enumerate(docs):
        for r in d["rows"]:
            if r["t"] in types:
                out.append({
                    "doc_idx": di,
                    "doc_title": d["title"],
                    "row_i": r["i"],
                    "type": r["t"],
                    "no": r["no"],
                    "text": r["c"],
                })
    return out


def collect_source_toc_rows(rec, docs):
    """The raw source_toc rows (sectionTypeId 16) are DISCARDed by the
    pipeline's tree-building stage (structure.py DISCARD set) but are still
    present in split_record's row-level output tagged t=='source_toc'. They
    carry the ORIGINAL law's own table-of-contents text, useful as an
    independent cross-check on structural numbering (digit-fidelity probe).
    """
    out = []
    for di, d in enumerate(docs):
        for r in d["rows"]:
            if r["t"] == "source_toc":
                out.append({"doc_idx": di, "doc_title": d["title"], "row_i": r["i"], "text": r["c"]})
    return out


def raw_grep_all_sections(rec, needle):
    """Grep the FULLY RAW (unsplit, unfiltered) rec['sections'] content for
    a literal substring, independent of TYPE_MAP/split_record, to catch
    anything that might live in an unmapped/unknown sectionTypeId. Returns
    list of dicts with global_i, sectionId, sectionTypeId, sectionNo,
    content.
    """
    out = []
    for i, s in enumerate(rec["sections"]):
        content = clean(s.get("content"))
        if needle in content:
            out.append({
                "global_i": i,
                "sectionId": s.get("sectionId"),
                "sectionTypeId": s.get("sectionTypeId"),
                "sectionNo": s.get("sectionNo"),
                "sectionName": s.get("sectionName"),
                "content": content,
            })
    return out


# ---------------------------------------------------------------------------
# Golden targets: known matra-number ranges from the brief, used to LOCATE
# (not assume) which amendment-act doc introduces each. Location is done by
# searching every amendment doc's matra rows for these numbers and reporting
# whichever doc(s) actually contain them -- if the brief's numbers don't
# match any doc, that is reported as a discrepancy, never silently patched.
# ---------------------------------------------------------------------------
GOLDEN_TARGETS = [
    {
        "name": "laksana 1/1 kokankai (terrorism)",
        "matra_probe": ["135/1", "135/2", "135/3", "135/4"],
        "expected_range": "135/1-135/4",
    },
    {
        "name": "muad khwaamphid electronic card",
        "matra_probe": ["269/1", "269/2", "269/3", "269/4", "269/5", "269/6", "269/7"],
        "expected_range": "269/1-269/7",
    },
    {
        "name": "muad khwaamphid passport",
        "matra_probe": ["269/8", "269/9", "269/10", "269/11", "269/12", "269/13", "269/14", "269/15"],
        "expected_range": "269/8-269/15",
    },
    {
        "name": "laksana 13 khwaamphid sop (corpse)",
        "matra_probe": ["366/1", "366/2", "366/3", "366/4"],
        "expected_range": "366/1-366/4",
    },
]


def locate_golden_target(docs, target):
    """Search amendment-act docs (idx>=2) for rows whose sectionNo matches
    any of the target's probe numbers. Returns per-doc hit counts so we can
    see if a target's matra numbers are split across >1 doc (should not
    happen per the data, but report honestly if it does) plus full row
    dump + heading rows + char-length sum for the winning doc.
    """
    doc_hits = {}
    for di, d in enumerate(docs):
        if di < 2:
            continue
        found = [r for r in d["rows"] if r["t"] == "matra" and r["no"] in target["matra_probe"]]
        if found:
            doc_hits[di] = found
    result = {"target": target["name"], "expected_range": target["expected_range"], "doc_hits_by_idx": {}}
    for di, rows in doc_hits.items():
        d = docs[di]
        headings = [r for r in d["rows"] if r["t"] in ("laksana", "muad")]
        matched_nos = sorted(set(r["no"] for r in rows), key=lambda x: (thai_to_int(x.split("/")[0]) or 0, x))
        payload_rows = [r for r in d["rows"] if r["t"] == "matra" and r["no"] in target["matra_probe"]]
        char_len = sum(len(r["c"]) for r in payload_rows)
        directive_hits = scan_doc_rows(d, di, "golden_target_doc")
        gaps = find_matra_gaps(d)
        result["doc_hits_by_idx"][di] = {
            "doc_title": d["title"],
            "matched_matra_nos": matched_nos,
            "payload_row_count": len(payload_rows),
            "payload_char_length": char_len,
            "heading_rows": [{"row_i": h["i"], "type": h["t"], "no": h["no"], "text": h["c"]} for h in headings],
            "directive_hits_in_doc": directive_hits,
            "matra_sequence_in_doc": gaps["matra_sequence"],
            "matra_gaps_in_doc": gaps["gaps"],
            "all_rows": [{"row_i": r["i"], "type": r["t"], "no": r["no"], "text": r["c"]} for r in d["rows"]],
        }
    return result


def scan_sampling_dl():
    """Scan every sampling_dl/*.jsonl file's non-code docs (i.e. every doc
    whose doc_type is NOT 'code' and NOT 'enacting_act' -- amendment-act-like
    docs) for the same directive-verb patterns. Each file may contain 1+
    JSON records (one per line); split each record independently.
    """
    files = sorted(glob.glob(os.path.join(SAMPLING_DIR, "*.jsonl")))
    all_hits = []
    per_file_doc_counts = {}
    total_non_code_docs = 0
    for fp in files:
        fname = os.path.basename(fp)
        with open(fp, encoding="utf-8") as f:
            for line_no, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                docs = split_record(rec)
                non_code_docs = [d for d in docs if d["doc_type"] not in ("code", "enacting_act")]
                total_non_code_docs += len(non_code_docs)
                per_file_doc_counts[f"{fname}:{line_no}"] = {
                    "law_code": rec.get("law_code"),
                    "timeline_code": rec.get("timeline_code"),
                    "n_docs": len(docs),
                    "n_non_code_docs": len(non_code_docs),
                }
                for di, d in enumerate(docs):
                    if d["doc_type"] in ("code", "enacting_act"):
                        continue
                    hits = scan_doc_rows(d, di, f"sampling_dl/{fname}:{line_no}")
                    all_hits.extend(hits)
    return {
        "n_files": len(files),
        "files": [os.path.basename(f) for f in files],
        "total_non_code_docs_scanned": total_non_code_docs,
        "per_record_doc_counts": per_file_doc_counts,
        "hits": all_hits,
    }


def main():
    report = {}

    # --- 1-2. Load + split the -63 record ---
    rec63 = load_rec63()
    report["rec63_meta"] = {
        "timeline_code": rec63.get("timeline_code"),
        "law_code": rec63.get("law_code"),
        "n_sections": len(rec63.get("sections", [])),
    }
    docs63 = split_record(rec63)
    report["rec63_docs_summary"] = [
        {"doc_idx": i, "doc_type": d["doc_type"], "title": d["title"], "n_rows": len(d["rows"])}
        for i, d in enumerate(docs63)
    ]

    # --- 3. Directive-verb scan across all -63 amendment-act docs (idx>=2) ---
    hits_63 = []
    for di, d in enumerate(docs63):
        if di < 2:
            continue
        hits_63.extend(scan_doc_rows(d, di, "rec63"))
    report["rec63_directive_hits"] = hits_63
    report["rec63_directive_hit_count"] = len(hits_63)

    # --- 4. All laksana/muad/phak heading rows across the WHOLE -63 record ---
    report["rec63_structure_headings"] = collect_structure_headings(docs63)

    # --- 5. source_toc rows (raw ToC, pipeline-discarded) for cross-check ---
    report["rec63_source_toc_rows"] = collect_source_toc_rows(rec63, docs63)
    # Direct raw-section grep (independent of split_record) for the digit
    # falsification: does "laksana 12" appear ANYWHERE in the raw -63 record?
    report["raw_grep_laksana_12"] = raw_grep_all_sections(rec63, "ลักษณะ ๑๒")
    # And the counterpart: what does the actual structural (typeId 7) row
    # for sap (thraphy - property) say, verbatim, with its exact sectionId?
    truey_rows = []
    for i, s in enumerate(rec63["sections"]):
        if s.get("sectionTypeId") == 7:
            c = clean(s.get("content"))
            if "ทรัพย์" in c:
                truey_rows.append({
                    "global_i": i, "sectionId": s.get("sectionId"),
                    "sectionTypeId": s.get("sectionTypeId"), "sectionNo": s.get("sectionNo"),
                    "content": c,
                })
    report["raw_laksana_typeid7_rows_containing_sap"] = truey_rows

    # --- 6. matra-number gap detection across all 32 -63 amendment acts ---
    gap_report = []
    for di, d in enumerate(docs63):
        if di < 2:
            continue
        g = find_matra_gaps(d)
        gap_report.append({
            "doc_idx": di, "doc_title": d["title"],
            "matra_sequence": g["matra_sequence"], "gaps": g["gaps"],
            "has_directive_hit": any(h["doc_idx"] == di for h in hits_63),
        })
    report["rec63_matra_gap_scan_all_32_acts"] = gap_report

    # --- 7. sampling_dl directive-verb scan ---
    report["sampling_dl_scan"] = scan_sampling_dl()

    # --- 8. Golden targets ---
    golden_results = []
    for t in GOLDEN_TARGETS:
        golden_results.append(locate_golden_target(docs63, t))
    report["golden_targets"] = golden_results

    # --- write output ---
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # --- concise stdout summary (full detail lives in OUT_JSON) ---
    print(f"[survey_scan] rec63: {report['rec63_meta']}")
    print(f"[survey_scan] rec63 docs: {len(docs63)} total, amendment acts (idx>=2): {len(docs63)-2}")
    print(f"[survey_scan] rec63 directive-verb hits (all families, docs idx>=2): {len(hits_63)}")
    n_acts_with_gaps = sum(1 for g in gap_report if g["gaps"])
    print(f"[survey_scan] rec63 amendment acts with TRUE matra-number gaps: {n_acts_with_gaps} / {len(gap_report)}")
    n_acts_with_directives = sum(1 for g in gap_report if g["has_directive_hit"])
    print(f"[survey_scan] rec63 amendment acts with >=1 directive-verb hit: {n_acts_with_directives} / {len(gap_report)}")
    sd = report["sampling_dl_scan"]
    print(f"[survey_scan] sampling_dl: {sd['n_files']} files, {sd['total_non_code_docs_scanned']} non-code docs scanned, {len(sd['hits'])} directive-verb hits")
    print(f"[survey_scan] raw grep 'laksana 12' anywhere in -63 sections: {len(report['raw_grep_laksana_12'])} hit(s)")
    print(f"[survey_scan] structural (typeId 7) rows containing 'sap/thraphy': {len(truey_rows)} -> {[r['content'] for r in truey_rows]}")
    for gr in golden_results:
        print(f"[survey_scan] golden target '{gr['target']}': found in doc_idx {list(gr['doc_hits_by_idx'].keys())}")
    print(f"[survey_scan] full JSON written to {OUT_JSON}")


if __name__ == "__main__":
    main()
