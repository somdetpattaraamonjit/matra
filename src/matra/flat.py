# Task 5′ — flat export (1 row = 1 มาตรา) + ELI wrapper + enrich wiring.
"""Stage 5 (ENRICH, per docs/PIPELINE.md) continuation + Stage 7 (PUBLISH,
flat view) — turns a per-doc structure tree into the flat ML/RAG export the
standard promises: "flat rows carry the full ancestor breadcrumb so
hierarchy survives flattening" (PIPELINE.md design law #5).

Pure, stdlib + jsonschema-free (the schema file is read once at import time
only to load the column-order const — no jsonschema import here); no I/O
beyond that one read, no network.

HARD RULE (golden lock protection, docs/akn_adoption_verdicts.md +
brief task5-brief.md): `enrich_docs` is a SEPARATE stage applied AFTER
build_docs_merged returns. It is never wired inside build_docs /
build_docs_merged / normalize — those functions, merge.py, structure.py,
splitter.py, qa.py, cid.py are untouched by this module. Wiring into the
CLI output path happens in cli.py's __main__ flow only, additively.

Design decisions this module makes (brief §Column semantics + ambiguity
resolutions granted upfront):

  * phak/laksana/muad/suan ancestor headings are found by WALKING the
    parent_id chain node-by-node (never by parsing hierarchy_path, which is
    a precomputed human-readable string with no reliable machine-parseable
    grammar across Thai headings) and keying each ancestor found by its own
    node_type. A doc without a given ancestor level simply yields None for
    that column (e.g. a matra directly under a phak, no laksana/muad/suan
    in between).

  * status / effective_from / effective_until: the real pipeline's
    _build_trees (structure.py) does not set these fields on structure
    nodes at all today (only doc-level status is set; per-matra evidence
    fields are a future QA-phase-2 item per structure.py's own comment).
    Evidence-or-unknown law (PIPELINE.md law #3, schema
    status_evidence contract): a node that does not carry these fields
    gets status="unknown", effective_from=None, effective_until=None —
    never fabricated, never inferred from the doc envelope's own status.

  * record_ctx (ambiguity resolution b, brief): a plain dict the CALLER
    builds from a record + the doc's own timeline block — this module does
    not reach into raw record shape itself; it only reads the three keys it
    documents (law_group_code, reference_url, is_latest_computed) off
    whatever dict the caller hands it, keeping to_flat's own contract
    small and the record-shape-discovery responsibility with the caller
    (cli.py / the e2e runner), which already knows how to build one from a
    real record.

  * is_latest_computed inside work_expressions: no reusable "compute
    is_latest across a timeline group" function existed anywhere in the
    pipeline to import (grepped cli.py/qa.py/structure.py — confirmed;
    structure.py's _build_trees hardcodes is_latest_computed=True per doc
    because it only ever sees ONE record at a time, never a sibling group).
    The schema's own field description IS the spec: "Computed =
    max(timeline_seq) in group" — `compute_is_latest` (below) is now the
    ONE place that arithmetic is performed. work_expressions and every
    record_ctx assembly site (cli.py's --flat path,
    docs/run_e2e_criminal63.py) call it rather than duplicating inline
    max-seq comparisons or reading structure.py's per-record envelope
    hardcode (Task 5′ FIX cycle, task5-fix-brief.md FIX 1 — the hardcode
    at structure.py:170 stays untouched/out-of-scope; it goes in
    dataset-card Known Defects, not this module's job to correct upstream).
"""
import json
import pathlib

from .cid import assign_cids, assign_eids, extract_refs

_SCHEMA_PATH = pathlib.Path(__file__).parents[2] / "schemas" / "matra-0.2.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
FLAT_COLUMNS = list(_SCHEMA["properties"]["flat_profile"]["properties"]["columns"]["const"])

# Ancestor container levels flattened into their own columns (brief §Column
# semantics). Order here matches HIER_LEVELS in structure.py minus "bot"
# (บทเฉพาะกาล has no flat column of its own per the schema's frozen list —
# a matra parented directly to a bot node simply yields None for all four).
_ANCESTOR_LEVELS = {"phak", "laksana", "muad", "suan"}

# Thai-digit -> arabic translation table (Task 5′ FIX cycle FIX 2 — same
# local idiom already used identically in cid.py/merge.py/structure.py;
# no shared exported helper exists to import (checked: cid.py's and
# merge.py's _arab are both underscore-private module internals, not
# public API — duplicating this 2-line table locally is the same pattern
# those modules already independently repeat, not a new dependency).
_TH_DIGITS = "๐๑๒๓๔๕๖๗๘๙"
_TR = {c: str(i) for i, c in enumerate(_TH_DIGITS)}


def _translate_thai_digits(s):
    """Translate Thai digits to arabic; None-safe. Local to flat.py only —
    used exclusively to detect WHERE (in translated-text coordinates) a
    cid.extract_refs match starts, matching extract_refs' own internal
    Thai-to-arabic translation (cid.py translates before regex-matching,
    so raw_text/positions are relative to the translated text, not the
    original) — never used to mutate any row's stored `text` value."""
    if s is None:
        return None
    return "".join(_TR.get(c, c) for c in s)


def _drop_self_refs(text: str, refs: list[dict], own_number_arabic) -> list[dict]:
    """Task 5′ FIX cycle (task5-fix-brief.md FIX 2) — filter out refs_out
    self-citation pollution. Every มาตรา's text begins with its own
    heading ("มาตรา <n> …"), so cid.extract_refs (generic, untouchable)
    emits a self-reference for essentially every row; genuine
    cross-references get drowned out.

    Drops a ref iff BOTH:
      1. its regex match starts at position 0 of the text (translated to
         arabic digits, matching extract_refs' own internal translation —
         detected via startswith on the ref's own raw_text, which is the
         exact matched span with only outer whitespace stripped), AND
      2. its target_matra equals the row's own number_arabic (both sides
         already arabic: extract_refs always returns target_matra in
         arabic digits, and number_arabic is stored arabic by the
         pipeline upstream of this module — no translation needed for
         this half of the comparison).

    Every other ref is kept, including refs to the row's own number that
    occur mid-text (genuinely re-citing itself later, not just its own
    heading) and refs to other มาตรา anywhere in the text (position 0 or
    not) — only the specific position-0-AND-self-number combination is
    dropped. Never mutates `text` or any ref dict; returns a new list.
    """
    if not refs or own_number_arabic is None:
        return refs
    translated = _translate_thai_digits(text)
    filtered = []
    is_first_self_candidate = True
    for ref in refs:
        starts_at_zero = is_first_self_candidate and translated.startswith(ref["raw_text"])
        # only the ref(s) whose match literally begins the string can ever
        # be a position-0 match; once any ref has been inspected, no later
        # ref (by finditer's left-to-right, non-overlapping match order)
        # can also start at position 0 — so this only ever suppresses
        # (at most) the very first match in the list.
        is_first_self_candidate = False
        if starts_at_zero and ref["target_matra"] == own_number_arabic:
            continue
        filtered.append(ref)
    return filtered


def compute_is_latest(timeline_seq: int, group_seqs) -> bool:
    """Task 5′ FIX cycle (task5-fix-brief.md FIX 1) — the SINGLE reusable
    derivation of the rule `is_latest = (timeline_seq == max seq in
    group)`. Every place in this codebase that needs is_latest_computed
    (work_expressions below, plus callers assembling record_ctx: cli.py's
    --flat path, docs/run_e2e_criminal63.py) MUST go through this function
    rather than re-deriving the comparison inline or reading
    structure.py's per-record envelope hardcode (which is always True —
    it never sees a sibling group).

    `group_seqs` is any iterable of the group's timeline_seq values
    (including timeline_seq itself, i.e. pass the FULL group's seqs — the
    record whose own seq is being tested is a member of its own group).
    """
    return timeline_seq == max(group_seqs)


def enrich_docs(docs: list[dict], law_group_code: str) -> list[dict]:
    """Separate ENRICH stage: apply cid.assign_cids + cid.assign_eids to
    every doc's structure nodes, per doc, using that doc's OWN
    law_group_code when it carries one (falls back to the caller-supplied
    law_group_code otherwise — every real doc from build_docs_merged does
    carry timeline.law_group_code, so this is a defensive fallback, not the
    primary path).

    Applied AFTER build_docs / build_docs_merged returns (never inside
    those functions or normalize) — this is what keeps
    normalize_63.golden.json byte-identical: the golden is generated
    without ever calling this function.

    Mutates each doc's structure list in place (matches cid.py's own
    in-place-list-of-dicts convention) and returns the same list of docs.
    """
    for doc in docs:
        lg = doc.get("timeline", {}).get("law_group_code") or law_group_code
        nodes = doc["structure"]
        assign_cids(nodes, lg)
        assign_eids(nodes)
    return docs


def _ancestor_headings(doc: dict) -> dict:
    """For every node in `doc["structure"]`, walk its parent_id chain and
    return {node_id: {level: heading, ...}} — the ancestor heading found at
    each of phak/laksana/muad/suan, keyed by the ANCESTOR's own node_type
    (never by assuming a fixed depth — a matra nested directly under a phak,
    skipping laksana/muad/suan entirely, still resolves phak correctly and
    leaves the rest None).

    Walking parent_id (not parsing hierarchy_path) per the brief: hierarchy_
    path is a precomputed human breadcrumb string with no reliable Thai
    word-boundary grammar to split on (see tests/test_e2e_criminal63.py's
    own comment on why Thai headings can't be safely string-split); the
    parent_id chain is the actual machine-readable structural link.
    """
    by_id = {n["node_id"]: n for n in doc["structure"] if "node_id" in n}
    cache: dict = {}

    def ancestors_of(node_id):
        if node_id in cache:
            return cache[node_id]
        node = by_id.get(node_id)
        result = {lvl: None for lvl in _ANCESTOR_LEVELS}
        if node is not None:
            parent_id = node.get("parent_id")
            if parent_id is not None and parent_id in by_id:
                parent = by_id[parent_id]
                parent_result = dict(ancestors_of(parent_id))
                result.update(parent_result)
                if parent.get("node_type") in _ANCESTOR_LEVELS:
                    result[parent["node_type"]] = parent.get("heading")
        cache[node_id] = result
        return result

    return {n["node_id"]: ancestors_of(n["node_id"]) for n in doc["structure"] if "node_id" in n}


def to_flat(doc: dict, record_ctx: dict) -> list[dict]:
    """1 dict per node_type=="matra" node in `doc["structure"]`. Keys are
    EXACTLY set(FLAT_COLUMNS), values in FLAT_COLUMNS order.

    `record_ctx` supplies the 3 columns the brief scopes to record/envelope
    context rather than the node itself: law_group_code, reference_url,
    is_latest_computed (ambiguity resolution b — a plain dict the caller
    builds; shape documented at module top).

    Conservation law: matra_no / matra_no_arabic / text are byte-identical
    to the source node's number / number_arabic / joined paragraphs — ZERO
    text mutation anywhere in this function.
    """
    ancestors = _ancestor_headings(doc)
    title_th = doc.get("title", {}).get("th")
    rows = []
    for node in doc["structure"]:
        if node.get("node_type") != "matra":
            continue
        anc = ancestors.get(node["node_id"], {lvl: None for lvl in _ANCESTOR_LEVELS})
        text = "\n".join(p["text"] for p in node.get("paragraphs", []))
        row = {
            "matra_cid": node.get("matra_cid"),
            "law_group_code": record_ctx.get("law_group_code"),
            "doc_id": doc.get("doc_id"),
            "doc_type": doc.get("doc_type"),
            "law_title_th": title_th,
            "phak": anc.get("phak"),
            "laksana": anc.get("laksana"),
            "muad": anc.get("muad"),
            "suan": anc.get("suan"),
            "matra_no": node.get("number"),
            "matra_no_arabic": node.get("number_arabic"),
            # evidence-or-unknown law (PIPELINE.md #3): a node that does not
            # carry these fields (today's real pipeline output) yields the
            # unknown/None defaults — never fabricated from doc-level status.
            "status": node.get("status", "unknown"),
            "effective_from": node.get("effective_from"),
            "effective_until": node.get("effective_until"),
            "text": text,
            # Task 5′ FIX cycle FIX 2: drop the position-0 self-citation
            # every มาตรา's own heading otherwise generates (extract_refs
            # itself stays generic/untouched — the filter lives here only).
            "refs_out": _drop_self_refs(text, extract_refs(text), node.get("number_arabic")),
            "deka_refs": [],  # phase 2 — always empty in v0
            "reference_url": record_ctx.get("reference_url"),
            "is_latest_computed": record_ctx.get("is_latest_computed"),
        }
        rows.append({col: row[col] for col in FLAT_COLUMNS})
    return rows


def work_expressions(records: list[dict]) -> dict:
    """ELI wrapper (docs/akn_adoption_verdicts.md §6, HARDEN → Task 5′):
    {"work": <law_group_code>, "schema": "matra-work-expressions/v0",
     "expressions": [{"timeline_code", "timeline_seq", "is_latest_computed"},
     ...], "eli:is_realized_by": [<timeline_code>...]}

    `records` is a list of doc envelopes (the shape build_docs /
    build_docs_merged returns — each carries doc_id and timeline.
    {law_group_code, timeline_seq}). is_latest_computed is derived via
    compute_is_latest (Task 5′ FIX cycle FIX 1 — the ONE reusable
    max-seq-in-group derivation, no duplicated inline comparison here
    anymore) over timeline_seq — the field the pipeline already computes
    and stamps on every envelope (structure.py) — never re-derived from
    doc_id string-splitting or any other invented heuristic.

    timeline_code is recovered from doc_id by stripping the "#docN" suffix
    structure.py appends (doc_id = f"{tl}#doc{di}") — the doc_id IS the
    timeline_code, just qualified per-doc within one record's split; this
    is the same tl the record's own timeline_code carried in, not a new
    identifier invented here.
    """
    law_group_codes = {r["timeline"]["law_group_code"] for r in records}
    work = law_group_codes.pop() if len(law_group_codes) == 1 else None

    group_seqs = [r["timeline"]["timeline_seq"] for r in records]

    expressions = []
    for r in records:
        timeline_code = r["doc_id"].split("#doc")[0]
        seq = r["timeline"]["timeline_seq"]
        expressions.append({
            "timeline_code": timeline_code,
            "timeline_seq": seq,
            "is_latest_computed": compute_is_latest(seq, group_seqs) if group_seqs else False,
        })

    return {
        "work": work,
        "schema": "matra-work-expressions/v0",
        "expressions": expressions,
        "eli:is_realized_by": [e["timeline_code"] for e in expressions],
    }
