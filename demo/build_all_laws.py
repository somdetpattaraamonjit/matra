#!/usr/bin/env python3
"""Build EVERY law group in the local corpus into demo data (idempotent).

COLD-French-Law principle: the whole corpus, one standard, one pass.
For each law group found locally: latest record -> build_docs_merged ->
enrich (cid/eId) -> flat rows -> work_expressions. Conservation-checked;
failures are SKIPPED AND LOGGED, never silently dropped (Berkson rule).

Cross-record code assembly: a few codes (the Civil & Commercial Code) are
stored one enacting instrument per บรรพ (Book) with NO single consolidated
record. Picking the fullest single record drops 5 of 6 Books. Such families
are detected and consolidated from the clean code-body holder per Book
(matra.assemble); every built law also carries a `completeness` descriptor.

Usage:  PYTHONPATH=src python3 demo/build_all_laws.py
Output: demo/public/data/laws/l****.flat.jsonl + .we.json
        demo/public/data/laws.json   (manifest, sorted by title)
        demo/public/data/build_report.json (totals + skip list, honesty)
"""
import glob, json, os, pathlib, sys, unicodedata

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from matra.structure import build_docs_merged
from matra.flat import enrich_docs, to_flat, work_expressions
from matra.qa import qa_check
from matra.assemble import (needs_assembly, assemble_code, completeness_of,
                            matra_numbers, family_union, to_int, complete_code_record)

CORPUS_DIRS = [
    os.environ.get("MATRA_CORPUS_DL", "/sessions/practical-adoring-ride/mnt/.aice/legalrag/work/sampling_dl"),
    os.environ.get("MATRA_CORPUS_RAW", "/sessions/practical-adoring-ride/mnt/.aice/legalrag/raw"),
]
OUT = REPO / "demo/public/data"
LAWDIR = OUT / "laws"
LAWDIR.mkdir(parents=True, exist_ok=True)

def norm_title(t):
    return unicodedata.normalize("NFC", (t or "").strip())

def seq_of(r):
    try: return int(r["timeline_code"].rsplit("-", 1)[1])
    except Exception: return -1

# ---- 1. gather every record of every group across the whole local corpus ----
groups = {}          # law_code -> {timeline_code: record}
files = []
for d in CORPUS_DIRS:
    files += sorted(glob.glob(os.path.join(d, "*.jsonl")))
for f in files:
    for line in open(f, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except Exception: continue
        lc, tc = r.get("law_code"), r.get("timeline_code")
        if not lc or not tc: continue
        groups.setdefault(lc, {})[tc] = r     # dedupe across files

# ---- 2. build each group ----
manifest, skips = [], []
tot_rows = 0
recovered = 0
assembled_count = 0
gap_filled_total = 0
for i, (lc, recs) in enumerate(sorted(groups.items())):
    # The source's newest record is sometimes an EMPTY placeholder — taking it
    # blindly drops whole codes (ป.พ.พ. / วิ.แพ่ง / วิ.อาญา / รัษฎากร were lost
    # this way). Fall back down the timeline to the newest record that actually
    # HAS sections. Conservation gate + skip log still apply (law = sacred).
    abs_latest = max(recs.values(), key=seq_of)
    nonempty = [r for r in recs.values() if r.get("sections")]
    if "-1D-" in lc and nonempty:
        # Code family: canonical text = the FULLEST consolidated record (most
        # sections = the code body, NOT a small amendment act or an empty
        # placeholder), newest seq wins ties. The source's newest record is
        # often an empty placeholder or a 3-มาตรา amendment — taking it blindly
        # drops or truncates whole codes (ป.พ.พ./วิ.แพ่ง/วิ.อาญา/รัษฎากร).
        latest = max(nonempty, key=lambda r: (len(r["sections"]), seq_of(r)))
        if seq_of(latest) != seq_of(abs_latest): recovered += 1
    elif abs_latest.get("sections"):
        latest = abs_latest                       # normal law: newest consolidated version
    elif nonempty:
        latest = max(nonempty, key=lambda r: (len(r["sections"]), seq_of(r)))
        recovered += 1
    else:
        latest = abs_latest
    # Cross-record code assembly: when a code family (-1D-) is fragmented across
    # records (no single record holds the whole code — e.g. the Civil Code's 6
    # บรรพ live in 6 separate enacting instruments), consolidate from the clean
    # code-body holder per Book instead of shipping only the fullest fragment.
    # Assembly detection is scoped to -1D- code families (the Thai code-family
    # naming convention — ประมวล…): only those are stored one enacting instrument
    # per บรรพ. Scanning every family's cross-record union is O(whole corpus), so
    # the scope is declared in build_report rather than run everywhere (never silent).
    assembled, asm_report = False, None
    if "-1D-" in lc and len(recs) > 1 and needs_assembly(recs):
        cand_rec, cand_rep = assemble_code(recs, lc)
        # adopt only if internally consistent (0 duplicate มาตรา) AND no worse than
        # the fullest single record; covers_union is carried into the manifest so
        # any shortfall is auditable, never silent.
        if cand_rep["duplicate_matra"] == 0 and cand_rep["matra_present"] >= len(matra_numbers(latest)):
            latest, asm_report, assembled = cand_rec, cand_rep, True
            assembled_count += 1
    # within-record gap completion: a code's มาตรา is sometimes parked in a
    # trailing amendment doc instead of the code body (the "amendment at the end"
    # pattern). Relocate those into the code body so the code is navigable-complete
    # (verbatim reorder, conservation-safe). No-op for the already-complete
    # assembled civil record (single doc).
    if "-1D-" in lc:
        latest, _filled = complete_code_record(latest)
        gap_filled_total += len(_filled)
    # canonical group name comes from the newest record (even when it is the
    # empty placeholder — it still carries the proper "ประมวลกฎหมาย…" title);
    # fall back to the content record's title, then the code.
    title = norm_title(abs_latest.get("title")) or norm_title(latest.get("title")) or lc
    try:
        if not latest.get("sections"):
            raise ValueError("empty record (no sections in any version)")
        docs, flags, merge_report = build_docs_merged(latest)
        qa = qa_check(latest, docs, flags, merge_report)
        if qa["hard_fail"]:
            raise ValueError(f"qa hard_fail: charDelta={qa['checks'].get('char_roundtrip_delta_pct')} "
                             f"mergeOK={qa['checks'].get('merge_conservation_ok')}")
        docs = enrich_docs(docs, lc)
        envs = [{"doc_id": f"{r['timeline_code']}#doc0",
                 "timeline": {"law_group_code": lc, "timeline_seq": seq_of(r)}}
                for r in recs.values()]
        we = work_expressions(envs)
        ctx = {"law_group_code": lc,
               "reference_url": latest.get("reference_url", ""),
               "is_latest_computed": True}
        rows = []
        for d in docs:
            rows += to_flat(d, ctx)
        if not rows:
            raise ValueError("0 matra rows")
        # main doc = doc_id with most matra rows
        cnt = {}
        for row in rows: cnt[row["doc_id"]] = cnt.get(row["doc_id"], 0) + 1
        main_doc = max(cnt, key=cnt.get)
        main_type = next(r["doc_type"] for r in rows if r["doc_id"] == main_doc)
        # Code-family main-doc resolves to `code`: an enacting instrument
        # (พระราชบัญญัติ/พระราชกฤษฎีกา ให้ใช้ประมวล…) heads the code body itself,
        # so for a -1D- family the dominant doc IS the code — relabel the wrapper
        # type so consumers see `code`, not the enacting shell.
        if "-1D-" in lc and main_type in {"enacting_act", "royal_decree"}:
            for row in rows:
                if row["doc_id"] == main_doc: row["doc_type"] = "code"
            main_type = "code"
        lid = f"l{i:04d}"
        with open(LAWDIR / f"{lid}.flat.jsonl", "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        (LAWDIR / f"{lid}.we.json").write_text(json.dumps(we, ensure_ascii=False), encoding="utf-8")
        # completeness: coverage of the consolidated CODE BODY (main doc) base
        # มาตรา numbers (ทวิ/ตรี share a base number). Each interior gap is then
        # classified honestly: `gaps_unmerged` = numbers that DO exist elsewhere
        # in the law's records (a later amendment not yet merged into the code
        # body — a known merge-engine limit, NOT missing data); `gaps_absent` =
        # numbers truly absent from the corpus (a real, declared coverage gap).
        main_base = [n for n in (to_int(r["matra_no_arabic"]) for r in rows
                                 if r["doc_id"] == main_doc) if n is not None]
        all_base = {n for n in (to_int(r["matra_no_arabic"]) for r in rows) if n is not None}
        comp = completeness_of(main_base)
        gap_nums = [n for lo, hi in comp["gaps"] for n in range(lo, hi + 1)]
        comp["present_in_corpus"] = len(all_base)
        comp["gaps_unmerged"] = [n for n in gap_nums if n in all_base]
        comp["gaps_absent"] = [n for n in gap_nums if n not in all_base]
        entry = {"id": lid, "title": title, "law_code": lc,
                 "flat": f"data/laws/{lid}.flat.jsonl", "we": f"data/laws/{lid}.we.json",
                 "n_matra_main": cnt[main_doc], "n_rows": len(rows),
                 "n_expr": len(we["expressions"]), "main_doc_type": main_type,
                 "completeness": comp}
        if assembled:
            entry["assembled"] = True
            entry["assembly_sources"] = asm_report["source_records_used"]
            comp["covers_union"] = asm_report["covers_union"]
            comp["family_union"] = asm_report["family_union"]
        # preserve curated deka samples (data/deka/<id>.json) across rebuilds
        if (OUT / "deka" / f"{lid}.json").exists():
            entry["deka"] = f"data/deka/{lid}.json"
        manifest.append(entry)
        tot_rows += len(rows)
    except Exception as e:
        skips.append({"law_code": lc, "title": title, "reason": str(e)[:160]})

manifest.sort(key=lambda m: m["title"])
(OUT / "laws.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=0), encoding="utf-8")
report = {"generated": "build_all_laws", "corpus_files": len(files),
          "groups_found": len(groups), "built": len(manifest),
          "skipped": len(skips), "recovered_by_fallback": recovered,
          "assembled_code_families": assembled_count,
          "gap_filled_matra": gap_filled_total,
          "assembly_scope": "law_code contains -1D- (Thai code-family convention)",
          "total_flat_rows": tot_rows, "skips": skips}
(OUT / "build_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"corpus_files={len(files)} groups={len(groups)} BUILT={len(manifest)} "
      f"SKIPPED={len(skips)} RECOVERED={recovered} ASSEMBLED={assembled_count} total_rows={tot_rows}")
for s in skips[:12]: print("  SKIP:", s["law_code"], "|", s["reason"][:80])
