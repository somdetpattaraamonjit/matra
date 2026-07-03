# Vendored from ~/.aice/legalrag/pipeline/normalize.py (engine lane, 2026-07-02) on 2026-07-03; behavior locked byte-level by tests/golden/normalize_63.golden.json
"""Thin CLI — replicates the engine's __main__ end-to-end. Only file I/O lives here.

Usage: python3 -m matra.cli <raw_record.json> <out_dir> [--merge]

Writes qa_report.json, docs_v02.json, toc_generated.json into out_dir, prints
the VERDICT line, and exits 2 on hard_fail (0 otherwise) — same contract as
the vendored-from engine's __main__ block. Without --merge the behavior is
byte-identical to before (golden safety); with --merge, Stage 3 runs and the
merge_report is folded into qa (checks["merge"] + merge_conservation_ok).
"""
import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

from .qa import qa_check, primary_doc
from .structure import build_docs, build_docs_merged, toc_of
from .flat import enrich_docs, to_flat, compute_is_latest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Matra normalizer CLI")
    parser.add_argument("raw_record", help="path to a raw record JSON file")
    parser.add_argument("out_dir", help="output directory for qa_report.json / docs_v02.json / toc_generated.json")
    parser.add_argument("--merge", action="store_true",
                        help="run Stage 3 (Merge Engine): re-home headless amendment structures into the code doc")
    parser.add_argument("--flat", action="store_true",
                        help="Task 5': run the ENRICH stage (cid.assign_cids/assign_eids, applied AFTER build — "
                             "never inside build_docs/build_docs_merged, golden-lock protection) over the built "
                             "docs, then write flat.jsonl (1 row = 1 matra) alongside docs_v02.json. Additive: "
                             "without --flat, output is byte-identical to before this flag existed.")
    args = parser.parse_args(argv)

    raw_path, out_dir = Path(args.raw_record), Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    record = json.loads(raw_path.read_text(encoding="utf-8"))

    # Task 4′.2 review Finding 3: a single merge execution. build_docs_merged
    # runs split_record + merge_amendments EXACTLY ONCE and hands back both the
    # built docs/flags AND the merge_report from that same run — previously
    # this called build_docs(record, merge=True) (which merges once internally
    # to build the tree) and THEN separately re-ran split_record +
    # merge_amendments a second time just to obtain the report for qa. Both
    # calls were pure and produced equal results, so the bug was never a
    # correctness divergence — but it computed the merge twice and meant the
    # on-disk qa_report and the tree the CLI wrote were, structurally, outputs
    # of two different executions of the same pure function rather than one
    # shared one. merge=False keeps calling build_docs directly (unchanged;
    # there is no merge_report on that path).
    if args.merge:
        docs, flags, merge_report = build_docs_merged(record)
    else:
        docs, flags = build_docs(record, merge=False)
        merge_report = None
    result = qa_check(record, docs, flags, merge_report=merge_report)
    checks, hard_fail, flags = result["checks"], result["hard_fail"], result["flags"]

    qa = {"generated": datetime.datetime.now().isoformat(timespec="seconds"),
          "input": str(raw_path), "sha256_in": hashlib.sha256(raw_path.read_bytes()).hexdigest()[:16],
          "hard_checks": checks, "hard_fail": hard_fail, "review_flags": flags, "n_flags": len(flags)}

    code = primary_doc(docs)  # None when docs == [] (Task 3.5 — record has sections: [])

    (out_dir / "qa_report.json").write_text(json.dumps(qa, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "docs_v02.json").write_text(json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "toc_generated.json").write_text(json.dumps(toc_of(code) if code else [], ensure_ascii=False, indent=1), encoding="utf-8")

    # Task 5' additive wiring: ONLY runs when --flat is passed. build -> enrich
    # -> (re-)write tree JSON (enriched docs now carry matra_cid/eId/wId, schema-
    # valid since 84d7369) -> to_flat -> JSONL. Applied AFTER docs/qa/toc are
    # already computed and written above (golden-lock protection: enrich_docs
    # is never called on the path that produces the byte-stable no-flag output).
    n_flat_rows = 0
    if args.flat:
        law_group_code = record.get("law_code")
        enriched_docs = enrich_docs(docs, law_group_code)
        # re-write docs_v02.json now that structure nodes carry matra_cid/eId/wId
        # (additive fields only; existing keys/values untouched — schema-valid
        # since 84d7369, see schemas/matra-0.2.json eId/wId deltas)
        (out_dir / "docs_v02.json").write_text(
            json.dumps(enriched_docs, ensure_ascii=False, indent=1), encoding="utf-8")

        # Task 5' FIX cycle (review findings, task5-fix-brief.md FIX 1):
        # is_latest_computed must be GROUP-derived via flat.compute_is_latest,
        # never read off d["timeline"]["is_latest_computed"] (structure.py's
        # per-record envelope hardcode — always True; _build_trees only ever
        # sees ONE record at a time and has no sibling-group context).
        #
        # Scope note: this CLI invocation processes exactly one raw_record
        # (argv[0]) — it has no month-file/corpus access to a record's
        # cross-record siblings (that discovery only happens in
        # docs/run_e2e_criminal63.py, which loads the whole month-file). So
        # the "group" compute_is_latest sees here is the set of timeline_seq
        # values actually visible within this single invocation's own
        # enriched_docs (every doc split from the SAME raw_record shares the
        # SAME timeline_seq, by construction of structure.py's _build_trees —
        # so this is honest given the CLI's true visibility, not a
        # fabrication: is_latest_computed reflects "latest among what this
        # invocation can see," which is correct scope for a single-record CLI
        # tool. A caller wanting cross-record group truth must supply it via
        # a multi-record entry point, as run_e2e_criminal63.py does.)
        group_seqs = [d.get("timeline", {}).get("timeline_seq") for d in enriched_docs]
        flat_rows = []
        for d in enriched_docs:
            seq = d.get("timeline", {}).get("timeline_seq")
            record_ctx = {
                "law_group_code": d.get("timeline", {}).get("law_group_code") or law_group_code,
                "reference_url": record.get("reference_url"),
                "is_latest_computed": compute_is_latest(seq, group_seqs) if group_seqs else False,
            }
            flat_rows.extend(to_flat(d, record_ctx))
        n_flat_rows = len(flat_rows)
        with (out_dir / "flat.jsonl").open("w", encoding="utf-8") as fh:
            for row in flat_rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    flat_note = f" | flat_rows={n_flat_rows}" if args.flat else ""
    print(f"VERDICT: {'FAIL' if hard_fail else 'PASS'} | docs={len(docs)} | rows {checks['rows_in_vs_out'][0]}->{checks['rows_in_vs_out'][1]} | "
          f"charΔ={checks['char_roundtrip_delta_pct']}% | tree={checks['code_tree']} | matra={checks['matra_nodes_code']} | flags={len(flags)}"
          f"{flat_note}")
    sys.exit(2 if hard_fail else 0)


if __name__ == "__main__":
    main()
