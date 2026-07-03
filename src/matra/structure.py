# Vendored from ~/.aice/legalrag/pipeline/normalize.py (engine lane, 2026-07-02) on 2026-07-03; behavior locked byte-level by tests/golden/normalize_63.golden.json
"""Stage 4 — per-doc tree building + doc envelope + TOC generation.

Pure: every input is an argument, no globals, no I/O.

This is pass 2 of the engine normalizer: build the hierarchy tree per doc
(matra วรรค merge, unknown_N flagging, hierarchy_path breadcrumb) and wrap
each doc's tree in its schema envelope (provenance, timeline, status).

Behavior-identical to the vendored-from engine with ONE deliberate change:
the engine's status line was a dead conditional — "in_force" if <condition>
else "in_force" — both branches literally "in_force". The condition compared
against a bare, accidental module-level global (Finding #0, see
docs/PIPELINE.md design law #4) that was only ever assigned inside the
engine's __main__ block, which made the engine's normalize() raise
NameError when called standalone (exactly what tests/canon.py had to work
around before this vendoring). The dead conditional is removed here; status
is hardcoded to "in_force" with the identical status_evidence string. This
is the only behavior-affecting edit in this vendoring — everything else is
verbatim.
Task 3′.3 (2026-07-03) extends this with typeIds discovered by the 2026-07-02
sampling gate (60 groups; 4 failed conservation): 13 = บทเฉพาะกาล
(transitional-provisions chapter) is a real structural container — TYPE_MAP
gains 13 -> "bot", it pops the entire hierarchy stack (sits directly under
doc root, like starting a new top-level chapter) and subsequent มาตรา parent
to it. Everything else outside TYPE_MAP (18, 20, and any future unknown
typeId) is quarantined: the node is still emitted as unknown_{N} with content
preserved verbatim (never crash, never silently reclassify — Berkson rule:
log the invisible), but display is False. Quarantine accounting lives in
qa.py only; no new fields invented on structure nodes here.
"""
import datetime
import re

from .splitter import clean, split_record

HIER_LEVELS = ["phak", "laksana", "muad", "suan"]         # ภาค > ลักษณะ > หมวด > ส่วน
HIDE_TYPES  = {"countersign", "remark"}                    # per customer spec: keep in DB, display=false
DISCARD     = {"source_toc"}                                # corrupted upstream → regenerate
CONTAINER_TYPES = {"bot"}                                   # typeId 13 บทเฉพาะกาล: pops whole stack, real container


def build_docs(record, merge: bool = False):
    """Split + build the per-doc structure trees, wrapped in schema envelopes.

    Returns (docs, flags) — verbatim behavior of the engine's normalize(),
    composing the splitter pass (split_record) with the tree-building pass.

    Task 4′.2 adds an optional Stage 3 (MERGE) between split and tree:
    ``merge=False`` (default) → EXACTLY today's behavior (golden safety; the
    ``merge`` module is never even imported on this path); ``merge=True`` →
    delegates to ``build_docs_merged`` (a single merge execution) and
    discards the merge_report, keeping this function's original ``(docs,
    flags)`` contract so all existing callers (gate, golden, regressions)
    are untouched.

    Task 4′.2 review Finding 3: callers that DO need the merge_report (the
    CLI's ``--merge`` path) must call ``build_docs_merged`` directly instead
    of calling this function and then separately re-running
    ``split_record`` + ``merge_amendments`` themselves — that was the
    double-merge bug this refactor removes. ``merge_amendments`` is pure and
    idempotent-on-already-merged-input, so the old double-merge was not
    silently wrong, but it did real work (and real I/O-free compute) twice
    and made the CLI's on-disk report and the report qa saw two DIFFERENT
    executions of a pure function instead of one shared one.
    """
    if merge:
        out_docs, flags, _merge_report = build_docs_merged(record)
        return out_docs, flags
    docs = split_record(record)
    return _build_trees(record, docs)


def build_docs_merged(record):
    """Split + MERGE (once) + build the per-doc structure trees.

    Returns (docs, flags, merge_report) — the single-execution counterpart of
    ``build_docs(record, merge=True)`` that ALSO hands back the merge_report
    produced by that one ``merge.merge_amendments`` call, so a caller that
    needs both the built docs AND the report (the CLI, qa) never has to run
    the merge twice to get both halves (Task 4′.2 review Finding 3).
    """
    from .merge import merge_amendments
    docs = split_record(record)
    docs, merge_report = merge_amendments(docs)
    out_docs, flags = _build_trees(record, docs)
    return out_docs, flags, merge_report


def _build_trees(record, docs):
    """Tree-building pass (pass 2): turn split (and optionally already-merged)
    per-doc row groups into the schema-v0.2 doc envelopes + hierarchy trees.

    Pure, UNCHANGED logic from the original build_docs body — factored out so
    both the merge=False path (build_docs, calling this directly on split-only
    rows) and the merge=True path (build_docs_merged, calling this on
    split-then-merged rows) share exactly one implementation. `docs` is
    whatever split_record (optionally then merge_amendments) produced; this
    function does not know or care whether a merge happened upstream — it
    just sees row lists.
    """
    lg  = record["law_code"]; tl = record["timeline_code"]
    seq = int(tl.rsplit("-", 1)[1])
    out_docs, flags = [], []
    for di, d in enumerate(docs):
        nodes, stack, last_matra, order, container = [], {}, None, 0, None
        nid = lambda: f"{tl}_{di}_{len(nodes)}"
        for r in d["rows"]:
            t = r["t"]
            if t in DISCARD: continue
            order += 1
            if t in HIER_LEVELS:
                lvl = HIER_LEVELS.index(t)
                for deeper in HIER_LEVELS[lvl:]: stack.pop(deeper, None)
                node = {"node_id": nid(), "node_type": t, "krisdika_type_id": r["raw_type"],
                        "heading": r["c"], "number": None, "number_arabic": r["no"],
                        "parent_id": stack.get(HIER_LEVELS[lvl-1]) if lvl>0 else None,
                        "order": order, "display": True}
                stack[t] = node["node_id"]; nodes.append(node); last_matra=None; continue
            if t in CONTAINER_TYPES:
                # typeId 13 บทเฉพาะกาล: pops the ENTIRE hierarchy stack (sits
                # directly under doc root); subsequent มาตรา parent to it.
                stack.clear()
                node = {"node_id": nid(), "node_type": t, "krisdika_type_id": r["raw_type"],
                        "heading": r["c"], "number": None, "number_arabic": r["no"],
                        "parent_id": None, "order": order, "display": True}
                container = node["node_id"]; nodes.append(node); last_matra=None; continue
            if t == "matra":
                head = re.match(r"^มาตรา\s+(\S+(?:\s+(?:ทวิ|ตรี|จัตวา|เบญจ|ฉ|สัตต|อัฏฐ|นว|ทศ))?)", r["c"])
                if last_matra and nodes and nodes[-1]["node_id"]==last_matra and \
                   r["no"]==nodes[-1]["number_arabic"] and not head:
                    nodes[-1]["paragraphs"].append({"text": r["c"]}); continue
                parent = None
                for lv in reversed(HIER_LEVELS):
                    if lv in stack: parent = stack[lv]; break
                if parent is None: parent = container
                node = {"node_id": nid(), "node_type": "matra", "krisdika_type_id": 4,
                        "number": head.group(1) if head else None, "number_arabic": r["no"],
                        "heading": None, "parent_id": parent, "order": order, "display": True,
                        "paragraphs": [{"text": r["c"]}]}
                if not head:
                    flags.append({"doc": di, "node": node["node_id"], "reason": "matra row without 'มาตรา' head", "sample": r["c"][:60]})
                nodes.append(node); last_matra = node["node_id"]; continue
            # everything else: promulgation/recital/kho/countersign/remark/unknown
            # (typeIds outside TYPE_MAP surface as unknown_{N} in split_record;
            # those, plus any explicitly-quarantined mapped type, are hidden —
            # keep + hide + count, never crash, never silently reclassify)
            node = {"node_id": nid(), "node_type": t, "krisdika_type_id": r["raw_type"],
                    "heading": None, "number": None, "number_arabic": r["no"],
                    "parent_id": None, "order": order,
                    "display": t not in HIDE_TYPES and not t.startswith("unknown_"),
                    "paragraphs": [{"text": r["c"]}]}
            if t.startswith("unknown_"):
                flags.append({"doc": di, "node": node["node_id"], "reason": t, "sample": r["c"][:60]})
            nodes.append(node); last_matra=None
        # hierarchy_path per node (breadcrumb)
        by_id = {n["node_id"]: n for n in nodes}
        for n in nodes:
            parts, p = [], n.get("parent_id")
            while p:
                parts.append(by_id[p]["heading"]); p = by_id[p].get("parent_id")
            n["hierarchy_path"] = " > ".join([d["title"]] + list(reversed(parts))) if parts else d["title"]
        out_docs.append({
            "schema_version": "0.2",
            "doc_id": f"{tl}#doc{di}",
            "doc_type": d["doc_type"],
            "title": {"th": d["title"], "en": None},
            "status": "in_force",  # per-doc status refined in QA phase 2 (dead conditional on a bare global removed — Finding #0, see module docstring)
            "status_evidence": f"latest consolidation {tl} (max timeline seq in group at ingest)",
            "timeline": {"law_group_code": lg, "timeline_seq": seq, "is_latest_computed": True,
                          "amended_by": [], "consolidates": []},
            "structure": nodes,
            "provenance": {"source": "ocs-krisdika", "reference_url": record.get("reference_url"),
                            "source_trust_rank": 1,
                            "ingested_at": datetime.datetime.now().isoformat(timespec="seconds"),
                            "pipeline_version": "normalize.py v0.2"},
            "lang": "th", "en_pair_doc": None})
    return out_docs, flags


TOC_LEVELS = HIER_LEVELS + ["bot"]                          # existing levels, then bot (typeId 13 บทเฉพาะกาล container)


def toc_of(code_doc):
    toc, path = [], {}
    for n in code_doc["structure"]:
        if n["node_type"] in TOC_LEVELS:
            toc.append({"level": n["node_type"], "heading": n["heading"], "node_id": n["node_id"], "matra": []})
            path[n["node_id"]] = toc[-1]
        elif n["node_type"] == "matra" and n.get("parent_id") in path and n.get("number"):
            path[n["parent_id"]]["matra"].append(n["number"])
    for t in toc:
        t["matra_range"] = f"{t['matra'][0]}–{t['matra'][-1]}" if t["matra"] else None
        del t["matra"]
    return toc
