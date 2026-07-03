# Vendored from ~/.aice/legalrag/pipeline/normalize.py (engine lane, 2026-07-02) on 2026-07-03; behavior locked byte-level by tests/golden/normalize_63.golden.json
"""Hard QA math — vendored from the engine's __main__ block.

Pure: caller passes everything (record, docs, flags produced by build_docs).
No I/O, no filesystem, no timestamps. Returns exactly the engine's `checks` +
`hard_fail` + the updated flags list (DEFECT#8 unmerged-structure detector
appended), so callers (the CLI and later gate/regression tasks) can build the
full qa_report.json envelope around it.

Task 3′.3 (2026-07-03) adds a quarantine ledger: typeId 13 (บทเฉพาะกาล) joins
BODY_TYPES (real, counted, displayed structural row — symmetric in/out like
หมวด); everything else outside BODY_TYPES ∪ {1, 16} (18, 20, any future
unknown typeId) is a separate counted lane — kept, hidden, never dropped
(Berkson rule: log the invisible). Body and quarantine conservation are
checked separately; char roundtrip stays one combined number across both
lanes, name/shape unchanged.
"""
from .structure import HIER_LEVELS
from .splitter import clean

BODY_TYPES = {2, 3, 4, 6, 7, 8, 9, 10, 13, 14, 15}  # type 1 → doc.title (metadata), counted separately; 13=บทเฉพาะกาล real container


def primary_doc(docs):
    """The code if present, else the doc holding the most มาตรา (generic across doc types).

    Single helper — was duplicated (qa.py + cli.py) before Task 3′.3 review; cli.py imports this.
    Returns None for empty docs (Task 3.5 — records with sections: [] exist in the real
    corpus; normalize_record returns ([], []) for them, so there is no primary doc — never
    crash with max() arg is an empty sequence, return None and let callers handle it).
    """
    if not docs:
        return None
    return max(docs, key=lambda d: (d["doc_type"] == "code",
                                    sum(1 for n in d["structure"] if n["node_type"] == "matra")))


def qa_check(record, docs, flags, merge_report=None):
    """Run the engine's hard QA checks against (record, docs, flags).

    Returns {"checks": dict, "hard_fail": bool, "flags": list} — `flags` is a
    new list (input `flags` plus any DEFECT#8 entries appended), never
    mutated in place.

    Task 4′.2: `merge_report` is optional. When None (the default — every
    pre-merge caller, incl. the sampling gate and golden/regression tests),
    behavior is byte-for-byte identical to before. When a merge_report dict is
    passed (merge=True path), qa additionally exposes ``checks["merge"]`` (the
    report itself) and ``checks["merge_conservation_ok"]``, and hard_fail
    becomes True if that conservation check is False. The rows_total_* keys are
    read with ``.get`` (default equal, i.e. vacuously OK) so a merge_report from
    an older caller that predates Finding 2 does not spuriously fail this check.

    What merge_conservation_ok actually guarantees (and what it does NOT):
      * chars_moved_in == chars_moved_out — the donor-side chars removed equal
        the code-doc char growth. These are measured INDEPENDENTLY (Task 4′.2
        review Finding 4: donor pre-removal count vs. code-doc after−before
        growth), so this is a real quantity check, not a tautology.
      * per-segment payload rows sum to the reported rows_moved.
      * (Finding 2) rows_total_before == rows_total_after — the total row count
        summed across every doc (code + all donors) is unchanged.
    Together these prove the merge neither lost nor duplicated any content in
    the physical move. They do NOT prove each segment landed at the correct
    POSITION in the code tree — positional correctness is asserted by the
    tests/goldens (TOC-order assertions in tests/test_merge*.py), not by this
    ledger. A green merge_conservation_ok therefore means "nothing was lost or
    duplicated," not "every placement is correct."
    """
    n_in = sum(1 for s in record["sections"] if s.get("sectionTypeId") in BODY_TYPES)
    n_titles_in = sum(1 for s in record["sections"] if s.get("sectionTypeId") == 1)
    n_out_rows = sum(len(n.get("paragraphs", [])) or 1 for d in docs for n in d["structure"]
                      if not n["node_type"].startswith("unknown_"))
    in_chars = sum(len(clean(s.get("content"))) for s in record["sections"] if s.get("sectionTypeId") in BODY_TYPES | {1})
    out_chars = sum(len(d["title"]["th"]) for d in docs) + \
                sum(len(p["text"]) for d in docs for n in d["structure"] for p in n.get("paragraphs", [])
                    if not n["node_type"].startswith("unknown_")) + \
                sum(len(n["heading"] or "") for d in docs for n in d["structure"]
                    if not n["node_type"].startswith("unknown_"))

    # quarantine lane: input sections whose typeId is outside BODY_TYPES ∪ {1, 16}
    # (16 = source_toc, discarded upstream as corrupted, not a data-loss lane);
    # output side = every emitted unknown_* node (by_type breakdown is input-side,
    # keyed by raw sectionTypeId, e.g. "18": 2).
    quarantined_in_sections = [s for s in record["sections"] if s.get("sectionTypeId") not in BODY_TYPES | {1, 16}]
    quarantined_out_nodes = [n for d in docs for n in d["structure"] if n["node_type"].startswith("unknown_")]
    q_rows_in = len(quarantined_in_sections)
    q_rows_out = sum(len(n.get("paragraphs", [])) or 1 for n in quarantined_out_nodes)
    q_chars_in = sum(len(clean(s.get("content"))) for s in quarantined_in_sections)
    q_chars_out = sum(len(p["text"]) for n in quarantined_out_nodes for p in n.get("paragraphs", []))
    q_by_type = {}
    for s in quarantined_in_sections:
        key = str(s.get("sectionTypeId"))
        q_by_type[key] = q_by_type.get(key, 0) + 1

    # char roundtrip stays ONE combined number across body + quarantine lanes
    combined_in_chars = in_chars + q_chars_in
    combined_out_chars = out_chars + q_chars_out
    if combined_in_chars == 0:
        # Task 3.5: records with sections: [] exist in the real corpus — both lanes
        # are 0 in and 0 out, so the delta is genuinely 0.0 (nothing lost); guard
        # the division instead of crashing. If somehow chars came out of nothing,
        # that is itself the defect — surface it as a full 100% delta, not NaN/crash.
        char_delta_pct = 0.0 if combined_out_chars == 0 else 100.0
    else:
        char_delta_pct = round(abs(combined_in_chars - combined_out_chars) / combined_in_chars * 100, 3)

    code = primary_doc(docs)  # None when docs == [] (Task 3.5 — no primary doc to report)
    counts = {lv: sum(1 for n in code["structure"] if n["node_type"] == lv) for lv in HIER_LEVELS} if code else {}
    # DEFECT #8 detector: structural headings living inside amendment docs = NOT merged into code body
    unmerged = [{"doc": di, "title": d["title"]["th"][:60], "level": n["node_type"], "heading": n["heading"]}
                for di, d in enumerate(docs) if d["doc_type"] != "code"
                for n in d["structure"] if n["node_type"] in HIER_LEVELS]
    checks = {
        "rows_in_vs_out": (n_in, n_out_rows, n_in == n_out_rows),
        "titles_in_vs_docs": (n_titles_in, len(docs), n_titles_in <= len(docs)),
        "char_roundtrip_delta_pct": char_delta_pct,
        "code_tree": counts,
        "docs_split": len(docs),
        "matra_nodes_code": sum(1 for n in code["structure"] if n["node_type"] == "matra") if code else 0,
        "unmerged_amendment_structures": len(unmerged),
        "quarantine": {"rows_in": q_rows_in, "rows_out": q_rows_out, "by_type": q_by_type,
                        "chars_in": q_chars_in, "chars_out": q_chars_out},
    }
    out_flags = list(flags)
    for u in unmerged:
        out_flags.append({"doc": u["doc"], "node": None,
                          "reason": f"DEFECT#8 unmerged {u['level']} in amendment: {u['heading'][:50]} — merge engine (phase 2) must insert into code tree",
                          "sample": u["title"]})
    if code is None:
        # Berkson rule: visible, never silent, never crash — the old engine gate
        # scored these vacuous PASS (0==0) silently; count it instead so it's
        # never lost in aggregate stats.
        out_flags.append({"doc": None, "node": None, "reason": "empty_record",
                          "sample": f"record has sections: [] (timeline_code={record.get('timeline_code')})"})
    body_rows_ok = checks["rows_in_vs_out"][2]
    quarantine_rows_ok = q_rows_in == q_rows_out
    hard_fail = (not body_rows_ok) or (not quarantine_rows_ok) or checks["char_roundtrip_delta_pct"] > 0.5

    # Task 4′.2: merge lane (only when a merge_report was supplied — merge=True path).
    # merge_conservation_ok = char round-trip balances AND per-segment payload rows
    # sum to the reported rows_moved AND (Finding 2) the total row count across
    # every doc (code + all donors) is unchanged before vs after. hard_fail if
    # the merge did not conserve on any of these axes.
    if merge_report is not None:
        per_seg_rows = sum(seg["rows"] for seg in merge_report.get("per_segment", []))
        rows_total_before = merge_report.get("rows_total_before")
        rows_total_after = merge_report.get("rows_total_after")
        rows_total_ok = rows_total_before == rows_total_after  # .get default (None==None) is vacuously OK for legacy reports
        merge_conservation_ok = (
            merge_report["chars_moved_in"] == merge_report["chars_moved_out"]
            and per_seg_rows == merge_report["rows_moved"]
            and rows_total_ok
        )
        checks["merge"] = merge_report
        checks["merge_conservation_ok"] = merge_conservation_ok
        hard_fail = hard_fail or (not merge_conservation_ok)

    return {"checks": checks, "hard_fail": hard_fail, "flags": out_flags}
