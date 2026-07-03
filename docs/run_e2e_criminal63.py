# Task 4′.3 — end-to-end run of the full Thai Criminal Code -63 (1,031
# sections) through the complete Matra pipeline WITH the merge engine.
# Task 5′ extends this with the ENRICH + PUBLISH-flat stages: CLI --merge
# --flat, then validates the flat export contract (column set, the 135/1
# ก่อการร้าย golden breadcrumb — only reachable post-merge, see Step 5b — and
# 1:1 row/matra-node conservation) plus the ELI work_expressions.json wrapper
# (built from every record of the -63 record's law_code group found in the
# same month-file corpus, per Task 5′'s own record-loading precedent — Step
# 5c mirrors Step 1's exact corpus-read + filename resolution).
#
# Extracts the -63 row from the raw corpus, invokes the CLI single-execution
# merge path (matra.cli main() with --merge, in-process so this stays
# reproducible without a subprocess dependency on argv/env), then validates
# every acceptance check named in the brief. Any failed check exits non-zero
# with the actual-vs-expected printed — no expectation is silently loosened
# to make a run go green (systematic-debugging rule: report reality, the
# controller adjudicates).
#
# Usage: python3 docs/run_e2e_criminal63.py
"""Runner: raw -63 row -> out/p0006-1D-0003-63.raw.json -> CLI --merge --flat
-> out/criminal-code-63/{docs_v02.json,qa_report.json,toc_generated.json,
flat.jsonl} -> validation -> out/criminal-code-63/{criminal-code_flat.jsonl,
work_expressions.json,SUMMARY.md}.
"""
import json
import os
import pathlib
import shutil
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from jsonschema import Draft202012Validator

from matra.cli import main as cli_main
from matra.flat import FLAT_COLUMNS, work_expressions


def _resolve_corpus():
    """Locate the raw -63 corpus (1956-11.jsonl) portably — no machine-specific
    session path hard-coded (Task 4'.2 review Finding 2). Resolution order:
      1. env MATRA_CORPUS — a path to 1956-11.jsonl OR a directory holding it;
      2. ~/.aice/legalrag/raw/1956-11.jsonl — the standard local engine layout;
      3. glob /sessions/*/mnt/.aice/legalrag/raw/1956-11.jsonl — any Cowork
         session mount (portable across future session names, not just this one).
    Returns the first existing path, else the standard local path (the runner
    then fails loudly in extract_raw_record if the corpus really is absent).
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
    return home


RAW = _resolve_corpus()
TIMELINE_CODE = "ป0006-1D-0003-63"
OUT_DIR = REPO_ROOT / "out" / "criminal-code-63"
RAW_RECORD_PATH = REPO_ROOT / "out" / "p0006-1D-0003-63.raw.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "matra-0.2.json"

# ---- Golden numbers (docs/merge_answer_key.md §Deliverable 2/3 + private
# data-audit evidence (2026-07-02) whole-record census, independently
# re-derived live from the raw row below by this same script before any
# check runs) ----
EXPECTED_TOC_COUNTS = {"phak": 3, "laksana": 16, "muad": 37, "suan": 3}
EXPECTED_DOC_COUNT = 34  # type-1 titles (34 docs total, per merge_answer_key.md/merge_grammar.md)

# the 4 merged structures + their มาตรา payload ranges (merge_answer_key.md §Deliverable 2).
# toc_of() (structure.py) builds matra_range from node["number"] — the VERBATIM
# Thai-digit form kept per the schema's own contract ("'๙๐/๑' style kept
# verbatim; arabic mirror in number_arabic", schemas/matra-0.2.json), not the
# arabic-normalized mirror — so expected ranges here are Thai-digit verbatim,
# matching what toc_generated.json actually contains.
EXPECTED_MERGED_STRUCTURES = [
    {"heading_contains": "ก่อการร้าย", "level": "laksana", "number": "1/1",
     "matra_range": "๑๓๕/๑–๑๓๕/๔"},
    {"heading_contains": "บัตรอิเล็กทรอนิกส์", "level": "muad", "number": "4",
     "matra_range": "๒๖๙/๑–๒๖๙/๗"},
    {"heading_contains": "หนังสือเดินทาง", "level": "muad", "number": "5",
     "matra_range": "๒๖๙/๘–๒๖๙/๑๕"},
    {"heading_contains": "ศพ", "level": "laksana", "number": "13",
     "matra_range": "๓๖๖/๑–๓๖๖/๔"},
]

# digit-fidelity Known Defect (merge_answer_key.md §Deliverable 3): sectionId
# 6466038's structural (typeId 7) row reads sectionNo "1" but the record's
# own source_toc (sectionId 6465658) independently calls the same section
# "ลักษณะ ๑๒" — a KRISDIKA source-data numbering error, noted not mutated.
DIGIT_DEFECT_SECTION_ID = 6466038
DIGIT_DEFECT_NOTE = (
    "sectionId 6466038 (ลักษณะ ทรัพย์, raw index 645): structural sectionNo "
    "reads \"1\" but should read \"12\" per this record's own source_toc "
    "(sectionId 6465658, \"สารบาญประมวลกฎหมายอาญา\", which independently "
    "labels the identical section ลักษณะ ๑๒) and its own row-position "
    "(immediately after ลักษณะ ๑๑, inside ภาค ๒). KRISDIKA source-data "
    "defect, not a pipeline artifact — see docs/merge_answer_key.md "
    "§Deliverable 3. Data left unmutated; recorded here only."
)


class CheckFailure(Exception):
    """Raised by a fail-loud check; caught once at the bottom to print + exit(1)."""


def fail(msg):
    raise CheckFailure(msg)


def log(msg):
    print(msg, flush=True)


# ======================================================================
# Step 1 — extract the -63 row from the raw corpus
# ======================================================================
def extract_raw_record():
    if not RAW.exists():
        fail(f"raw corpus not found at {RAW} — cannot run e2e without it")
    rows = [json.loads(l) for l in RAW.read_text(encoding="utf-8").splitlines() if l.strip()]
    matches = [r for r in rows if r.get("timeline_code") == TIMELINE_CODE]
    if len(matches) != 1:
        fail(f"expected exactly 1 row with timeline_code={TIMELINE_CODE!r}, found {len(matches)}")
    record = matches[0]
    RAW_RECORD_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_RECORD_PATH.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"[1/6] extracted {TIMELINE_CODE} ({len(record['sections'])} sections) -> {RAW_RECORD_PATH}")
    return record


# ======================================================================
# Step 2 — live census of the RAW record (independent of the pipeline —
# this is what the golden numbers above are checked AGAINST, so a golden
# number is never just trusted from a doc comment without a live recompute)
# ======================================================================
def live_census(record):
    from collections import Counter
    c = Counter(s.get("sectionTypeId") for s in record["sections"])
    census = {
        "total_sections": len(record["sections"]),
        "phak_raw6": c.get(6, 0), "laksana_raw7": c.get(7, 0),
        "muad_raw8": c.get(8, 0), "suan_raw9": c.get(9, 0),
        "doc_title_raw1": c.get(1, 0),
        "by_type": dict(sorted((str(k), v) for k, v in c.items())),
    }
    log(f"[2/6] live census: total={census['total_sections']} "
        f"ภาค={census['phak_raw6']} ลักษณะ={census['laksana_raw7']} "
        f"หมวด={census['muad_raw8']} ส่วน={census['suan_raw9']} "
        f"doc_titles={census['doc_title_raw1']}")
    if census["total_sections"] != 1031:
        fail(f"golden mismatch: total_sections expected 1031, got {census['total_sections']}")
    if census["phak_raw6"] != EXPECTED_TOC_COUNTS["phak"]:
        fail(f"golden mismatch: raw ภาค (typeId 6) expected {EXPECTED_TOC_COUNTS['phak']}, got {census['phak_raw6']}")
    if census["laksana_raw7"] != EXPECTED_TOC_COUNTS["laksana"]:
        fail(f"golden mismatch: raw ลักษณะ (typeId 7) expected {EXPECTED_TOC_COUNTS['laksana']}, got {census['laksana_raw7']}")
    if census["muad_raw8"] != EXPECTED_TOC_COUNTS["muad"]:
        fail(f"golden mismatch: raw หมวด (typeId 8) expected {EXPECTED_TOC_COUNTS['muad']}, got {census['muad_raw8']}")
    if census["suan_raw9"] != EXPECTED_TOC_COUNTS["suan"]:
        fail(f"golden mismatch: raw ส่วน (typeId 9) expected {EXPECTED_TOC_COUNTS['suan']}, got {census['suan_raw9']}")
    if census["doc_title_raw1"] != EXPECTED_DOC_COUNT:
        fail(f"golden mismatch: raw doc titles (typeId 1) expected {EXPECTED_DOC_COUNT}, got {census['doc_title_raw1']}")
    return census


# ======================================================================
# Step 3 — invoke the CLI single-execution merge path (in-process, so this
# script has no subprocess/PYTHONPATH fragility — same call cli.main() makes
# under `python3 -m matra.cli ... --merge --flat`).
# ======================================================================
def run_cli_merge():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    argv = [str(RAW_RECORD_PATH), str(OUT_DIR), "--merge", "--flat"]
    try:
        cli_main(argv)
        exit_code = 0
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else (1 if e.code else 0)
    log(f"[3/6] CLI --merge --flat run: exit={exit_code} (0=PASS, 2=hard_fail)")
    if exit_code != 0:
        fail(f"CLI exited {exit_code} (non-zero = hard_fail) — see qa_report.json for hard_checks")
    for name in ("docs_v02.json", "qa_report.json", "toc_generated.json", "flat.jsonl"):
        if not (OUT_DIR / name).exists():
            fail(f"CLI did not produce {name} in {OUT_DIR}")
    # brief-mandated deliverable filename: criminal-code_flat.jsonl (the CLI's
    # own generic --flat output is flat.jsonl; copy, don't move, so the CLI's
    # own contract stays independently inspectable too).
    shutil.copyfile(OUT_DIR / "flat.jsonl", OUT_DIR / "criminal-code_flat.jsonl")
    return exit_code


# ======================================================================
# Step 4 — schema validation: every doc in docs_v02.json against
# schemas/matra-0.2.json (jsonschema Draft 2020-12)
# ======================================================================
def validate_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    docs = json.loads((OUT_DIR / "docs_v02.json").read_text(encoding="utf-8"))
    errors = []
    for i, doc in enumerate(docs):
        for err in validator.iter_errors(doc):
            errors.append(f"doc[{i}] doc_id={doc.get('doc_id')!r}: {err.message} @ {list(err.absolute_path)}")
    log(f"[4/6] schema validation: {len(docs)} docs checked against {SCHEMA_PATH.name}, {len(errors)} errors")
    if errors:
        fail("schema validation FAILED:\n  " + "\n  ".join(errors[:20]) +
             (f"\n  ... +{len(errors) - 20} more" if len(errors) > 20 else ""))
    return len(docs)


# ======================================================================
# Step 5 — qa verdict + merge conservation + golden TOC numbers + 4 merged
# structures + bot check (typeId 13) + digit-fidelity note.
# ======================================================================
def validate_qa_and_goldens(census):
    qa_report = json.loads((OUT_DIR / "qa_report.json").read_text(encoding="utf-8"))
    checks = qa_report["hard_checks"]
    hard_fail = qa_report["hard_fail"]

    log(f"[5/6] qa verdict: hard_fail={hard_fail} "
        f"merge_conservation_ok={checks.get('merge_conservation_ok')} "
        f"unmerged_amendment_structures={checks.get('unmerged_amendment_structures')}")

    if hard_fail is not False:
        fail(f"qa hard_fail expected False, got {hard_fail!r} — hard_checks={json.dumps(checks, ensure_ascii=False)}")
    if checks.get("merge_conservation_ok") is not True:
        fail(f"merge_conservation_ok expected True, got {checks.get('merge_conservation_ok')!r}")
    if checks.get("unmerged_amendment_structures") != 0:
        fail(f"unmerged_amendment_structures expected 0, got {checks.get('unmerged_amendment_structures')!r} "
             f"(DEFECT#8 must be fully closed after merge)")

    # --- post-merge code-doc TOC must now equal the whole-record census ---
    toc = json.loads((OUT_DIR / "toc_generated.json").read_text(encoding="utf-8"))
    toc_counts = {"phak": 0, "laksana": 0, "muad": 0, "suan": 0}
    for entry in toc:
        lvl = entry["level"]
        if lvl in toc_counts:
            toc_counts[lvl] += 1
    log(f"    post-merge code-doc TOC counts: {toc_counts} (expected {EXPECTED_TOC_COUNTS})")
    mismatches = {k: (toc_counts[k], v) for k, v in EXPECTED_TOC_COUNTS.items() if toc_counts[k] != v}
    if mismatches:
        fail("TOC count golden mismatch (actual, expected): " +
             ", ".join(f"{k}: {a} != {e}" for k, (a, e) in mismatches.items()))

    # --- doc count golden: 34 docs total (34 type-1 titles) ---
    docs = json.loads((OUT_DIR / "docs_v02.json").read_text(encoding="utf-8"))
    if len(docs) != EXPECTED_DOC_COUNT:
        fail(f"docs total expected {EXPECTED_DOC_COUNT}, got {len(docs)}")

    # --- the 4 merged structures present in TOC, parented correctly, with their มาตรา ---
    toc_by_heading = {}
    for entry in toc:
        for target in EXPECTED_MERGED_STRUCTURES:
            if target["heading_contains"] in (entry["heading"] or ""):
                toc_by_heading[target["heading_contains"]] = entry

    merged_report_lines = []
    for target in EXPECTED_MERGED_STRUCTURES:
        key = target["heading_contains"]
        entry = toc_by_heading.get(key)
        if entry is None:
            fail(f"merged structure {key!r} not found in post-merge TOC at all")
        if entry["level"] != target["level"]:
            fail(f"merged structure {key!r}: level expected {target['level']}, got {entry['level']}")
        matra_range = entry.get("matra_range")
        expected_range = target["matra_range"]
        if matra_range != expected_range:
            fail(f"merged structure {key!r}: matra_range expected {expected_range!r}, got {matra_range!r}")
        merged_report_lines.append(f"{key} ({target['level']} {target['number']}): matra_range={matra_range}")
    log("    4 merged structures verified in TOC: " + " | ".join(merged_report_lines))

    # --- merge report highlights (4 segments, rows/chars — for SUMMARY.md) ---
    merge_report = checks.get("merge", {})
    per_segment = merge_report.get("per_segment", [])
    if merge_report.get("segments_applied") != 4:
        fail(f"merge_report segments_applied expected 4, got {merge_report.get('segments_applied')!r}")

    # --- bot check: does -63 contain typeId 13 (บทเฉพาะกาล)? ---
    has_typeid_13 = census["by_type"].get("13", 0) > 0
    if has_typeid_13:
        bot_entries = [e for e in toc if e["level"] == "bot"]
        if not bot_entries:
            fail("record contains typeId 13 (บทเฉพาะกาล) but no 'bot' entry found in TOC")
        bot_note = f"typeId 13 (บทเฉพาะกาล) present: {census['by_type']['13']} occurrence(s), TOC entry confirmed"
    else:
        bot_note = "no typeId 13 in -63 (confirmed via live census: by_type has no '13' key)"
    log(f"    bot check: {bot_note}")

    # --- typeIds 17/19 quarantine counts, if any occur in -63 (live census) ---
    quarantine = checks.get("quarantine", {})
    q17 = census["by_type"].get("17", 0)
    q19 = census["by_type"].get("19", 0)
    quarantine_note = (
        f"typeId 17 (อ้างอิงอำนาจ) count in -63: {q17}; typeId 19 (ลายเซ็น รมต.) count in -63: {q19}; "
        f"quarantine ledger (all unknown types): rows_in={quarantine.get('rows_in')} "
        f"rows_out={quarantine.get('rows_out')} by_type={quarantine.get('by_type')}"
    )
    log(f"    quarantine note: {quarantine_note}")

    # --- directive recognizer counts (merge_report; expect 0 genuine directives in -63) ---
    directives = merge_report.get("directives_recognized", {})
    directive_note = (
        f"directive recognizer: ADD={directives.get('ADD', 0)} REPLACE={directives.get('REPLACE', 0)} "
        f"REPEAL={directives.get('REPEAL', 0)} (all 0 expected — -63 has zero genuine directive sentences "
        f"per docs/merge_answer_key.md; the 4 golden targets are positional-only insertions)"
    )
    log(f"    {directive_note}")

    return {
        "toc_counts": toc_counts, "doc_count": len(docs), "per_segment": per_segment,
        "bot_note": bot_note, "quarantine_note": quarantine_note, "directive_note": directive_note,
        "merge_report": merge_report,
    }


# ======================================================================
# Step 5b (Task 5′) — flat export validations, per task5-brief.md §e2e runner
# additions:
#   1. every row: set(row) == set(FLAT_COLUMNS)
#   2. GOLDEN: the row with matra_no_arabic == "135/1" exists AND its
#      laksana heading contains "ก่อการร้าย" AND its phak heading contains
#      "ภาค ๒" (or equals the ภาค๒ heading verbatim — merge worked, breadcrumb
#      ลักษณะ ๑/๑ survived flattening) AND
#      matra_cid == "ป0006-1D-0003:135/1"
#   3. row count == matra node count across docs (1:1, no drop no dup)
# ======================================================================
def validate_flat_export():
    flat_path = OUT_DIR / "criminal-code_flat.jsonl"
    rows = [json.loads(l) for l in flat_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    log(f"    flat export: {len(rows)} rows read from {flat_path.name}")

    # --- check 1: every row's key set == set(FLAT_COLUMNS) exactly ---
    expected_keys = set(FLAT_COLUMNS)
    bad_rows = [i for i, r in enumerate(rows) if set(r) != expected_keys]
    if bad_rows:
        sample = bad_rows[0]
        fail(f"flat row key-set mismatch on {len(bad_rows)} row(s) (e.g. row {sample}: "
             f"got {sorted(set(rows[sample]))}, expected {sorted(expected_keys)})")
    log(f"    check 1/5 (flat): all {len(rows)} rows have keys == set(FLAT_COLUMNS) ({len(expected_keys)} cols)")

    # --- check 2 (GOLDEN, kickoff-mandated): 135/1 ก่อการร้าย breadcrumb ---
    target = next((r for r in rows if r.get("matra_no_arabic") == "135/1"), None)
    if target is None:
        fail("GOLDEN flat check failed: no row with matra_no_arabic == '135/1' found — "
             "merge did not land ลักษณะ ๑/๑ ก่อการร้าย into the flat export")
    if not target.get("laksana") or "ก่อการร้าย" not in target["laksana"]:
        fail(f"GOLDEN flat check failed: 135/1 row laksana expected to contain 'ก่อการร้าย', "
             f"got {target.get('laksana')!r}")
    phak = target.get("phak") or ""
    if "ภาค ๒" not in phak:
        fail(f"GOLDEN flat check failed: 135/1 row phak expected to contain 'ภาค ๒' "
             f"(or equal it verbatim), got {phak!r}")
    expected_cid = "ป0006-1D-0003:135/1"
    if target.get("matra_cid") != expected_cid:
        fail(f"GOLDEN flat check failed: 135/1 row matra_cid expected {expected_cid!r}, "
             f"got {target.get('matra_cid')!r}")
    log(f"    check 2/5 (GOLDEN): matra_no_arabic=135/1 row found — laksana={target['laksana']!r} "
        f"phak={phak!r} matra_cid={target['matra_cid']!r}")

    # --- check 3: row count == matra node count across ALL docs (1:1) ---
    docs = json.loads((OUT_DIR / "docs_v02.json").read_text(encoding="utf-8"))
    matra_node_count = sum(1 for d in docs for n in d["structure"] if n["node_type"] == "matra")
    if len(rows) != matra_node_count:
        fail(f"flat row count {len(rows)} != matra node count {matra_node_count} across {len(docs)} docs "
             f"(1:1 conservation broken — drop or dup somewhere in enrich_docs/to_flat)")
    log(f"    check 3/5 (flat): row count {len(rows)} == matra node count {matra_node_count} "
        f"across {len(docs)} docs (1:1, no drop no dup)")

    return {"flat_row_count": len(rows), "golden_135_1": {
        "laksana": target["laksana"], "phak": phak, "matra_cid": target["matra_cid"]}}


# ======================================================================
# Step 5c (Task 5′) — ELI work_expressions.json wrapper, built from EVERY
# record of the -63 record's law_code group found in the same month-file
# corpus (brief ambiguity resolution c: "if the runner's current record-
# loading only loads the -63 record, work_expressions may be built from all
# records of the group found in the same month-file — follow how existing
# code discovers them"). Step 1 (extract_raw_record) already reads and
# json.loads's every line of RAW to find the single -63 match; this step
# reuses that exact same read + json.loads pass, widening the filter from
# "timeline_code == TIMELINE_CODE" to "law_code == record['law_code']" so
# the discovery mechanism is identical, only the filter predicate differs.
#
# work_expressions only needs doc_id + timeline.{law_group_code,
# timeline_seq} (see src/matra/flat.py's own contract) — running the full
# split/build/merge pipeline on all 34 raw records (698-1,031 sections each)
# just to get 3 scalar fields per record would be 34x full pipeline
# executions for no additional truth; the 3 fields are read directly off
# each raw record (law_code, timeline_code, and timeline_code's own -NN
# suffix as timeline_seq, matching structure.py's identical
# `int(tl.rsplit("-", 1)[1])` derivation) into a doc-envelope-shaped dict
# carrying only the keys work_expressions reads.
# ======================================================================
def build_and_validate_work_expressions(record):
    law_code = record["law_code"]
    group_records = [
        r for r in (json.loads(l) for l in RAW.read_text(encoding="utf-8").splitlines() if l.strip())
        if r.get("law_code") == law_code
    ]
    if not group_records:
        fail(f"work_expressions: no records found for law_code={law_code!r} in {RAW}")
    if not any(r["timeline_code"] == TIMELINE_CODE for r in group_records):
        fail(f"work_expressions: group for law_code={law_code!r} does not include {TIMELINE_CODE!r} — "
             f"discovery predicate is wrong")

    light_envelopes = [
        {
            "doc_id": f"{r['timeline_code']}#doc0",
            "timeline": {
                "law_group_code": r["law_code"],
                "timeline_seq": int(r["timeline_code"].rsplit("-", 1)[1]),
            },
        }
        for r in group_records
    ]
    wrapper = work_expressions(light_envelopes)
    (OUT_DIR / "work_expressions.json").write_text(
        json.dumps(wrapper, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"    work_expressions.json written: {len(wrapper['expressions'])} expressions "
        f"(group size {len(group_records)}, law_code={law_code!r})")

    # --- check 4: exactly one expression has is_latest_computed == true,
    #     and its timeline_code ends -63 ---
    latest = [e for e in wrapper["expressions"] if e["is_latest_computed"]]
    if len(latest) != 1:
        fail(f"work_expressions.json check failed: expected exactly 1 expression with "
             f"is_latest_computed==true, got {len(latest)}: {latest}")
    if not latest[0]["timeline_code"].endswith("-63"):
        fail(f"work_expressions.json check failed: the sole is_latest_computed==true expression's "
             f"timeline_code expected to end '-63', got {latest[0]['timeline_code']!r}")
    log(f"    check 4/5 (work_expressions): exactly 1 latest expression, "
        f"timeline_code={latest[0]['timeline_code']!r} (ends -63 ✓)")

    return {"work_expressions_count": len(wrapper["expressions"]), "latest_timeline_code": latest[0]["timeline_code"]}


# ======================================================================
# Step 5d (Task 5′ FIX cycle, task5-fix-brief.md FIX 1) — validation #5:
# every flat row's is_latest_computed must equal (that row's timeline_code
# == the sole latest timeline_code recorded in work_expressions.json).
#
# This is an INDEPENDENT cross-check of the flat export (criminal-code_
# flat.jsonl, produced by the CLI's single-record --flat path) against the
# group ground truth (work_expressions.json, built in step 5c from the
# FULL 34-record law_code group loaded from the month-file corpus) — the
# same two truth sources the review finding named as conflicting (485
# rows said true / work_expressions said only 1-of-34 latest). A row's own
# timeline_code is recovered from its doc_id the same way work_expressions
# itself does (doc_id = f"{timeline_code}#doc{di}"; strip the "#docN"
# suffix), never re-derived by any other heuristic.
# ======================================================================
def validate_is_latest_computed_matches_work_expressions(work_expr_results):
    flat_path = OUT_DIR / "criminal-code_flat.jsonl"
    rows = [json.loads(l) for l in flat_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    sole_latest_timeline_code = work_expr_results["latest_timeline_code"]

    mismatches = []
    for i, row in enumerate(rows):
        row_timeline_code = row["doc_id"].split("#doc")[0]
        expected = (row_timeline_code == sole_latest_timeline_code)
        actual = row["is_latest_computed"]
        if actual != expected:
            mismatches.append((i, row_timeline_code, row.get("matra_no_arabic"), actual, expected))

    if mismatches:
        sample = mismatches[:10]
        fail(
            f"validation #5 FAILED: {len(mismatches)} flat row(s) have is_latest_computed "
            f"!= (timeline_code == sole latest {sole_latest_timeline_code!r}). Sample "
            f"(row_idx, timeline_code, matra_no_arabic, actual, expected): {sample}"
            + (f" ... +{len(mismatches) - 10} more" if len(mismatches) > 10 else "")
        )
    log(f"    check 5/5 (is_latest_computed cross-check): all {len(rows)} flat rows' "
        f"is_latest_computed matches (timeline_code == sole latest {sole_latest_timeline_code!r} "
        f"from work_expressions.json)")
    return {"rows_checked": len(rows)}


# ======================================================================
# Step 6 — digit-fidelity Known Defect: verify sectionId 6466038 is present
# in the raw record with sectionNo "1" (confirm the defect is still there,
# unmutated) and confirm the independent source_toc cross-check.
# ======================================================================
def verify_digit_defect_note(record):
    target = next((s for s in record["sections"] if s.get("sectionId") == DIGIT_DEFECT_SECTION_ID), None)
    if target is None:
        fail(f"digit-fidelity probe: sectionId {DIGIT_DEFECT_SECTION_ID} not found in raw record — "
             f"cannot confirm the Known Defect is still present/unmutated")
    if target.get("sectionTypeId") != 7:
        fail(f"digit-fidelity probe: sectionId {DIGIT_DEFECT_SECTION_ID} expected sectionTypeId 7, "
             f"got {target.get('sectionTypeId')!r}")
    if target.get("sectionNo") != "1":
        fail(f"digit-fidelity probe: sectionId {DIGIT_DEFECT_SECTION_ID} expected sectionNo \"1\" "
             f"(the still-unfixed defect), got {target.get('sectionNo')!r} — data may have changed upstream, "
             f"re-verify docs/merge_answer_key.md §Deliverable 3 before adjusting this note")
    log(f"[6/6] digit-fidelity Known Defect confirmed present + unmutated: "
        f"sectionId {DIGIT_DEFECT_SECTION_ID} sectionNo={target.get('sectionNo')!r} "
        f"content={target.get('content', '')[:40]!r}...")
    return DIGIT_DEFECT_NOTE


# ======================================================================
# SUMMARY.md — human-readable, <=15 lines, for the customer.
# ======================================================================
def write_summary(census, golden_results, digit_note, flat_results, work_expr_results):
    per_seg_by_heading = {seg["heading"]: seg for seg in golden_results["per_segment"]}
    # Match each of the 4 golden targets to its per_segment entry by the same
    # heading_contains substring used to verify the TOC above (robust — no
    # string-splitting on Thai headings, which have no reliable word-space rule).
    seg_summaries = []
    for target in EXPECTED_MERGED_STRUCTURES:
        seg = next((s for h, s in per_seg_by_heading.items() if target["heading_contains"] in h), None)
        label = f"{target['level']} {target['number']}"
        seg_summaries.append(f"{label}: {seg['rows']} rows/{seg['chars']} chars" if seg else f"{label}: MISSING")
    lines = [
        f"# Criminal Code -63 — E2E Merge+Flat Pipeline Run ({TIMELINE_CODE})",
        f"Produced {census['total_sections']} sections / {golden_results['doc_count']} docs -> "
        f"`out/criminal-code-63/{{docs_v02,qa_report,toc_generated,criminal-code_flat,work_expressions}}.json`. "
        f"QA verdict: PASS (hard_fail False).",
        "",
        "| Golden (post-merge code-doc TOC) | Expected | Actual |",
        "|---|---|---|",
        f"| ภาค | {EXPECTED_TOC_COUNTS['phak']} | {golden_results['toc_counts']['phak']} |",
        f"| ลักษณะ | {EXPECTED_TOC_COUNTS['laksana']} | {golden_results['toc_counts']['laksana']} |",
        f"| หมวด | {EXPECTED_TOC_COUNTS['muad']} | {golden_results['toc_counts']['muad']} |",
        f"| ส่วน | {EXPECTED_TOC_COUNTS['suan']} | {golden_results['toc_counts']['suan']} |",
        "",
        "Merge: 4/4 segments applied — " + "; ".join(seg_summaries) + ".",
        f"Flat export: {flat_results['flat_row_count']} rows (1:1 w/ matra nodes); GOLDEN 135/1 breadcrumb "
        f"laksana={flat_results['golden_135_1']['laksana']!r} matra_cid={flat_results['golden_135_1']['matra_cid']!r}.",
        f"ELI work_expressions.json: {work_expr_results['work_expressions_count']} expressions "
        f"(full law_code group); sole latest={work_expr_results['latest_timeline_code']!r}.",
        f"Known defects: (1) digit-fidelity — {digit_note.splitlines()[0][:140]}...; "
        f"(2) doc29 remark references a มาตรา ๓๐ amendment with no payload row in the record "
        f"(docs/merge_grammar.md Ambiguity #4); (3) {golden_results['bot_note']}.",
        f"{golden_results['quarantine_note'][:200]}",
        f"{golden_results['directive_note'][:200]}",
    ]
    text = "\n".join(lines) + "\n"
    (OUT_DIR / "SUMMARY.md").write_text(text, encoding="utf-8")
    log(f"wrote {OUT_DIR / 'SUMMARY.md'} ({len(lines)} lines)")
    return text


def main():
    try:
        record = extract_raw_record()
        census = live_census(record)
        run_cli_merge()
        n_docs_validated = validate_schema()
        golden_results = validate_qa_and_goldens(census)
        flat_results = validate_flat_export()
        work_expr_results = build_and_validate_work_expressions(record)
        validate_is_latest_computed_matches_work_expressions(work_expr_results)
        digit_note = verify_digit_defect_note(record)
        write_summary(census, golden_results, digit_note, flat_results, work_expr_results)
    except CheckFailure as e:
        log(f"\nFAIL: {e}")
        sys.exit(1)

    log(f"\nALL CHECKS GREEN — {n_docs_validated} docs schema-valid, qa PASS, "
        f"goldens matched, flat export validated ({flat_results['flat_row_count']} rows, "
        f"5/5 validations incl. is_latest_computed group-derived cross-check), "
        f"work_expressions.json validated ({work_expr_results['work_expressions_count']} expressions), "
        f"SUMMARY.md written.")
    sys.exit(0)


if __name__ == "__main__":
    main()
