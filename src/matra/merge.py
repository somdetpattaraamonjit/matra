# Task 4′.2 — Stage 3 (MERGE), the missing organ of PIPELINE.md.
# Design basis (evidence, not guesses): docs/merge_answer_key.md + docs/merge_grammar.md
# (Task 4′.1, derived from the raw -63 data). All numbers in those docs were
# re-verified against the raw row before this was written.
"""Stage 3 — Merge Engine (defect #8): positional re-homing + directive recognizer.

Pure: `merge_amendments(docs_rows)` is a pure function over the docs-rows
structure produced by `splitter.split_record`. No I/O, no globals, no network.
Nothing is ever deleted or rewritten — structural + payload rows are MOVED
verbatim (same dicts) from a donor amendment doc into the base code doc at the
resolved insertion point; the donor keeps its own boilerplate.

Two regimes exist in the corpus (merge_grammar §4):
  1. KRISDIKA-consolidated records like -63: headless structural fragments
     (a bare `ลักษณะ ๑/๑` / `หมวด ๔` heading row followed by payload มาตรา
     rows). Anchor is POSITIONAL — recovered from the heading's own number
     (slash or plain N) + row-order against the base code's structure. This
     is what v0 APPLIES.
  2. Records that preserve natural-language directive SENTENCES
     (`ให้เพิ่มความ…`, `ให้ยกเลิกความใน…และให้ใช้ความต่อไปนี้แทน`, `ให้ยกเลิก…`).
     v0 RECOGNIZES + COUNTS these but does NOT apply them (Known Defect lane) —
     so nothing is silently ignored.

A THIRD, headless-มาตรา-only regime also occurs: an amendment doc carries bare
payload มาตรา rows with NO structural heading (7/8/9) of their own to anchor on
— e.g. -63 doc17's มาตรา ๓๐/๑–๓๐/๓. These rows have no segment (`_find_segments`
starts a segment only at a heading row), so v0 does NOT apply them and they are
NOT yet counted in the merge report (no rows_moved / chars_moved entry, no
per_segment row); they simply stay in their donor doc, conserved by the overall
rows_total invariant. This is a Known Defect / v1 item — flagged here so report
consumers know such fragments exist and are neither merged nor separately
tallied yet.

merge_report shape (feeds qa.qa_check via its optional merge_report arg):
    {segments_found, segments_applied, segments_quarantined, rows_moved,
     chars_moved_in, chars_moved_out, rows_total_before, rows_total_after,
     per_segment: [{donor_doc, heading, anchor_rule, rows, chars}],
     directives_recognized: {ADD, REPLACE, REPEAL},
     directives_applied: 0, unresolved: [...]}

Conservation law (asserted internally + reflected in qa hard_fail when merge
was requested): chars_moved_in == chars_moved_out over the FULL physical move,
per-segment payload rows/chars equal the donor payload rows removed, AND
rows_total_before == rows_total_after (Task 4′.2 review Finding 2) — the sum
of len(rows) across every doc (code + all donors) is invariant under a merge,
since rows only ever relocate between docs here, never dropped or duplicated.
This catches defects the char-only check can miss: a row silently dropped (or
duplicated) elsewhere in the doc set with an unrelated, coincidentally-
compensating char delta.

The two char totals are measured INDEPENDENTLY (Task 4′.2 review Finding 4):
chars_moved_in is the donor segment's own content chars read BEFORE removal;
chars_moved_out is the code doc's content-char GROWTH across the insertion
(total after − before). They coincide for a correct move but are no longer the
same number counted twice, so the equality is a real check, not a tautology.
NOTE what this ledger does and does NOT prove: it proves nothing is lost or
duplicated in the physical move (a quantity invariant); it does NOT prove each
segment landed at the correct POSITION — placement correctness is verified by
the tests/goldens (TOC-order assertions), not by these numbers.
"""
import re

# Structural-heading raw typeIds (splitter TYPE_MAP: 7 ลักษณะ, 8 หมวด, 9 ส่วน) and matra (4).
HEADING_TYPES = (7, 8, 9)
MATRA_TYPE = 4
SEGMENT_TYPES = HEADING_TYPES + (MATRA_TYPE,)

# ---- Thai-digit → arabic (work in arabic after translate, per the brief) ----
_TH_DIGITS = "๐๑๒๓๔๕๖๗๘๙"
_TR = {c: str(i) for i, c in enumerate(_TH_DIGITS)}


def _arab(s):
    """Translate any Thai digits in a string to arabic; None-safe."""
    if s is None:
        return None
    return "".join(_TR.get(c, c) for c in s)


def _parse_number(no):
    """Parse a heading/matra sectionNo into (base:int, slash:int|None).

    '๑' → (1, None); '1/1' → (1, 1); '๒๖๙/๘' → (269, 8); '๓๓๕ ทวิ' → (335, None)
    (the Thai ordinal suffix is not a slash-number here). Returns (None, None)
    if no leading integer is found.
    """
    a = _arab(no)
    if a is None:
        return None, None
    a = a.strip()
    m = re.match(r"(\d+)\s*(?:/\s*(\d+))?", a)
    if not m:
        return None, None
    base = int(m.group(1))
    slash = int(m.group(2)) if m.group(2) else None
    return base, slash


def _matra_base(no):
    """Base integer of a matra number ('269/1' → 269, '335 ทวิ' → 335)."""
    base, _ = _parse_number(no)
    return base


def _content_chars(rows):
    """Total content-char count over a row list (sum of len(row['c'])).

    The independent measuring stick for the merge char-conservation ledger
    (Task 4'.2 review Finding 4): chars_moved_out is the code doc's own growth
    across an insertion (after − before), measured with this over the code
    rows, so it is a genuinely separate number from chars_moved_in (the donor-
    side pre-removal count) rather than the same value counted twice.
    """
    return sum(len(r["c"]) for r in rows)


# ======================================================================
# Directive-sentence recognizer (recognize-only v0). Families + false-positive
# guard from docs/merge_grammar.md. Order matters: exclude false positives
# first, then REPLACE (has both ยกเลิก and แทน) before REPEAL (ยกเลิก, no แทน).
# ======================================================================
# False positives the survey documented — NOT directives (e.g. cross-reference
# "apply มาตรา 30 by analogy"). Checked BEFORE any directive family.
# KNOWN DEFECT (v0): this guard is greedy — it matches ANYWHERE in the row
# text and, on a hit, short-circuits recognize_directives back to None for
# the WHOLE row. A genuine REPEAL (or ADD/REPLACE) directive that happens to
# co-occur in the same row alongside a ให้นำ…มาใช้บังคับ cross-reference phrase
# elsewhere in that row is swallowed along with the false positive instead of
# being recognized. Deferred to sentence-parse v1 (recognize per-sentence,
# not per-row) — v0 recognizes/counts at row granularity only.
_FALSE_POSITIVE = re.compile(r"ให้นำ.{0,40}?มาใช้บังคับ")

# ADD: insert new มาตรา/วรรค — "ให้เพิ่มความต่อไปนี้เป็น…"
_ADD = re.compile(r"ให้เพิ่มความต่อไปนี้เป็น")
# REPLACE: repeal-and-substitute — "ให้ยกเลิกความใน… และให้ใช้ความต่อไปนี้แทน"
_REPLACE = re.compile(r"ให้ยกเลิกความใน.*?และให้ใช้ความต่อไปนี้แทน", re.DOTALL)
# REPEAL: remove, no replacement — "ให้ยกเลิก…" WITHOUT a following …ต่อไปนี้แทน
_REPEAL = re.compile(r"ให้ยกเลิก")
_TAEN = re.compile(r"ต่อไปนี้แทน")


def recognize_directives(text):
    """Classify a single row's text into a directive family, or None.

    Returns one of "ADD" / "REPLACE" / "REPEAL", or None (not a directive,
    incl. the documented false-positive family). Recognize-only: never applies.
    """
    if not text:
        return None
    if _FALSE_POSITIVE.search(text):
        return None
    if _ADD.search(text):
        return "ADD"
    if _REPLACE.search(text):
        return "REPLACE"
    if _REPEAL.search(text):
        # REPEAL only if it is not actually a REPLACE we failed to span (guard):
        # a bare ยกเลิก with no ต่อไปนี้แทน anywhere in the row.
        if not _TAEN.search(text):
            return "REPEAL"
        return "REPLACE"
    return None


# ======================================================================
# Segment detection
# ======================================================================
def _find_segments(donor_rows):
    """Return list of (start_idx, end_idx) row-index spans for structural segments
    in one donor doc's row list.

    A segment starts at the FIRST structural-heading row (7/8/9) and extends over
    the contiguous run of heading+matra (7/8/9/4) rows that follows; it ends before
    any row of another type (countersign/remark/recital/unknown/etc.). A doc may
    contain 0 or more segments.
    """
    segments = []
    i = 0
    n = len(donor_rows)
    while i < n:
        if donor_rows[i]["raw_type"] in HEADING_TYPES:
            start = i
            j = i
            while j < n and donor_rows[j]["raw_type"] in SEGMENT_TYPES:
                j += 1
            segments.append((start, j))
            i = j
        else:
            i += 1
    return segments


# ======================================================================
# Anchor resolution — returns (insertion_index_in_code, anchor_rule:str) or
# (None, reason:str) when unresolvable (→ quarantine).
# ======================================================================
def _code_heading_index(code_rows):
    """Precompute, for the code doc, the row indices of every structural heading
    (7/8/9) and every ภาค (6), each with parsed number — used by anchor rules."""
    heads = []
    for idx, r in enumerate(code_rows):
        if r["raw_type"] in (6,) + HEADING_TYPES:
            base, slash = _parse_number(r["no"])
            heads.append({"idx": idx, "type": r["raw_type"], "base": base,
                          "slash": slash, "row": r})
    return heads


def _end_of_container_index(code_rows, anchor_idx, anchor_rank):
    """Row index immediately AFTER the anchor container's whole subtree = the
    next heading row of rank <= anchor_rank following anchor_idx (or end of doc).

    Rank: 6=ภาค(0) < 7=ลักษณะ(1) < 8=หมวด(2) < 9=ส่วน(3). Lower rank = higher level.
    """
    rank = {6: 0, 7: 1, 8: 2, 9: 3}
    for idx in range(anchor_idx + 1, len(code_rows)):
        rt = code_rows[idx]["raw_type"]
        if rt in rank and rank[rt] <= anchor_rank:
            return idx
    return len(code_rows)


def _resolve_anchor(seg_head, seg_first_matra_base, code_rows):
    """Resolve where a segment (identified by its FIRST heading row) inserts into
    the code doc. Returns (insertion_index, anchor_rule) or (None, reason).
    """
    htype = seg_head["raw_type"]
    base, slash = _parse_number(seg_head["no"])
    rank = {7: 1, 8: 2, 9: 3}[htype]
    heads = _code_heading_index(code_rows)

    if slash is not None:
        # Slash number N/M → insert after container of same type numbered N and
        # before its sibling N+1, IN THE SAME PARENT SCOPE. The scope is pinned by
        # the segment's own payload base number (same mechanism as the หมวด rule):
        #   ลักษณะ slash → parent scope = the ภาค whose มาตรา span contains the base
        #   หมวด  slash → parent scope = the ลักษณะ whose มาตรา span contains the base
        # This is what excludes the ภาค ๑ "ลักษณะ ๑" from a ภาค ๒ insertion, and
        # what leaves the mislabeled ทรัพย์ "ลักษณะ ๑" out (it is not the sequence-
        # consistent one within ภาค ๒). Candidates + sequence-consistency are then
        # evaluated ONLY among the same-type headings inside that scope.
        scope = _slash_scope(code_rows, htype, seg_first_matra_base)
        if scope is None:
            return None, f"slash_no_parent_scope_for_base_{seg_first_matra_base}"
        lo, hi = scope
        # same-type headings inside the scope, in row order
        scoped = [h for h in heads if h["type"] == htype and lo <= h["idx"] < hi]
        candidates = []
        for k, h in enumerate(scoped):
            if h["base"] == base and h["slash"] is None:
                nxt = scoped[k + 1] if k + 1 < len(scoped) else None
                seq_ok = nxt is not None and nxt["base"] == base + 1 and nxt["slash"] is None
                candidates.append((h, nxt, seq_ok))
        seq_consistent = [c for c in candidates if c[2]]
        if len(seq_consistent) == 1:
            h, nxt, _ = seq_consistent[0]
            return nxt["idx"], "slash:sequence_consistent"
        if len(candidates) == 1:
            # unambiguous even if next sibling isn't literally N+1
            h, nxt, _ = candidates[0]
            insert_at = nxt["idx"] if nxt else min(_end_of_container_index(code_rows, h["idx"], rank), hi)
            return insert_at, "slash:unique_in_scope"
        # 0 or >1 sequence-consistent candidates within scope → ambiguous, quarantine
        return None, f"slash_ambiguous: {len(candidates)} containers numbered {base} in scope, {len(seq_consistent)} sequence-consistent"

    # Plain number N → continuation anchor = same-type container numbered N-1.
    if htype == 8:
        # หมวด: scope = the ลักษณะ whose มาตรา span contains the segment's first
        # payload base number. Pin หมวด (N-1) inside THAT ลักษณะ, then insert at
        # end of that ลักษณะ's span.
        if seg_first_matra_base is None:
            return None, "muad_no_payload_base"
        target_lak = _laksana_span_containing(code_rows, seg_first_matra_base)
        if target_lak is None:
            return None, f"muad_no_laksana_span_for_base_{seg_first_matra_base}"
        lak_idx, lak_end = target_lak
        # find หมวด numbered N-1 within [lak_idx, lak_end)
        prev = None
        for idx in range(lak_idx, lak_end):
            r = code_rows[idx]
            if r["raw_type"] == 8:
                b, s = _parse_number(r["no"])
                if b == base - 1 and s is None:
                    prev = idx
        if prev is None:
            return None, f"muad_prev_{base - 1}_not_found_in_laksana"
        insert_at = _end_of_container_index(code_rows, prev, rank)
        # clamp inside the ลักษณะ span (never spill past ลักษณะ end)
        insert_at = min(insert_at, lak_end)
        return insert_at, "plain:continuation_muad"

    if htype == 7:
        # ลักษณะ N: scope = the ภาค containing the highest-numbered existing ลักษณะ.
        phak_span = _phak_with_highest_laksana(code_rows)
        if phak_span is None:
            return None, "laksana_no_phak_found"
        phak_idx, phak_end = phak_span
        # find ลักษณะ numbered N-1 within the ภาค
        prev = None
        for idx in range(phak_idx, phak_end):
            r = code_rows[idx]
            if r["raw_type"] == 7:
                b, s = _parse_number(r["no"])
                if b == base - 1 and s is None:
                    prev = idx
        if prev is not None:
            insert_at = _end_of_container_index(code_rows, prev, rank)
            insert_at = min(insert_at, phak_end)
            return insert_at, "plain:continuation_laksana"
        # N-1 not literally present (the ๑๒-mislabeled-as-๑ defect) → fall back to
        # END of that ภาค's ลักษณะ sequence (before the next ภาค heading / end of doc).
        return phak_end, "plain:end_of_phak_fallback"

    if htype == 9:
        # ส่วน N (not needed by -63, but handle generically inside current parent):
        same = [h for h in heads if h["type"] == 9 and h["base"] == base - 1 and h["slash"] is None]
        if same:
            insert_at = _end_of_container_index(code_rows, same[-1]["idx"], rank)
            return insert_at, "plain:continuation_suan"
        return None, f"suan_prev_{base - 1}_not_found"

    return None, "unknown_heading_type"


def _slash_scope(code_rows, htype, matra_base):
    """Parent-container [lo, hi) row-span that scopes a SLASH insertion, pinned by
    the segment's payload base number. ลักษณะ(7) → its ภาค span; หมวด(8)/ส่วน(9) →
    its ลักษณะ span. Returns None if the base cannot be located."""
    if matra_base is None:
        return None
    if htype == 7:
        return _phak_span_containing(code_rows, matra_base)
    # หมวด / ส่วน slash-insert scopes to the enclosing ลักษณะ
    return _laksana_span_containing(code_rows, matra_base)


def _phak_span_containing(code_rows, matra_base):
    """(phak_row_idx, span_end_idx) for the ภาค whose มาตรา base span contains
    matra_base, or None. Span end = next ภาค heading or end of doc."""
    phaks = []  # {idx, bases}
    cur = None
    for idx, r in enumerate(code_rows):
        if r["raw_type"] == 6:
            cur = {"idx": idx, "bases": []}
            phaks.append(cur)
        elif r["raw_type"] == 4 and cur is not None:
            b = _matra_base(r["no"])
            if b is not None:
                cur["bases"].append(b)
    for k, ph in enumerate(phaks):
        if ph["bases"] and min(ph["bases"]) <= matra_base <= max(ph["bases"]):
            end = phaks[k + 1]["idx"] if k + 1 < len(phaks) else len(code_rows)
            return ph["idx"], end
    return None


def _laksana_span_containing(code_rows, matra_base):
    """Return (laksana_row_idx, span_end_idx) for the ลักษณะ whose มาตรา base span
    contains matra_base, or None. Span walk tracks the current ลักษณะ and the
    max/min matra base seen under it; end = start of next ลักษณะ/ภาค or end of doc.
    """
    laks = []  # (idx, [matra bases])
    cur = None
    for idx, r in enumerate(code_rows):
        if r["raw_type"] in (7, 6):  # a new ลักษณะ or ภาค closes the current ลักษณะ scope
            if r["raw_type"] == 7:
                cur = {"idx": idx, "bases": []}
                laks.append(cur)
            else:
                cur = None
        elif r["raw_type"] == 4 and cur is not None:
            b = _matra_base(r["no"])
            if b is not None:
                cur["bases"].append(b)
    for k, lk in enumerate(laks):
        if lk["bases"] and min(lk["bases"]) <= matra_base <= max(lk["bases"]):
            # span end = next ลักษณะ or ภาค heading after this one, else end of doc
            end = len(code_rows)
            for idx in range(lk["idx"] + 1, len(code_rows)):
                if code_rows[idx]["raw_type"] in (6, 7):
                    end = idx
                    break
            return lk["idx"], end
    return None


def _phak_with_highest_laksana(code_rows):
    """Return (phak_idx, phak_end_idx) for the ภาค containing the highest-numbered
    existing ลักษณะ, or None if no ภาค. Ties → the later ภาค (higher row order),
    which is where the amendment-injected top ลักษณะ belongs."""
    phaks = []  # (idx, end, max_lak)
    cur = None
    for idx, r in enumerate(code_rows):
        if r["raw_type"] == 6:
            if cur is not None:
                cur["end"] = idx
            cur = {"idx": idx, "end": len(code_rows), "max_lak": -1}
            phaks.append(cur)
        elif r["raw_type"] == 7 and cur is not None:
            b, s = _parse_number(r["no"])
            if b is not None and s is None and b > cur["max_lak"]:
                cur["max_lak"] = b
    if not phaks:
        return None
    best = max(phaks, key=lambda p: (p["max_lak"], p["idx"]))
    return best["idx"], best["end"]


# ======================================================================
# Public entry point
# ======================================================================
def merge_amendments(docs_rows):
    """Pure. Given split_record output, MOVE headless amendment structures into the
    base code doc at their positionally-resolved anchors, and RECOGNIZE (not apply)
    any directive sentences. Returns (docs_rows', merge_report).

    Input is never mutated: we build fresh doc dicts (shallow-copied) with new row
    lists; the moved row dicts themselves are carried verbatim (same objects), so
    downstream tree-building sees identical row content.
    """
    # --- fresh copy of the docs list + row lists (row dicts kept identical objects) ---
    out_docs = [{**d, "rows": list(d["rows"])} for d in docs_rows]

    # Task 4'.2 review Finding 2: total-row-count invariant, summed across ALL
    # docs (code + every donor), BEFORE any move happens. This is the coarse,
    # doc-agnostic conservation check qa.py's merge_conservation_ok needs on
    # top of the existing chars/per-segment-rows checks — a move that drops or
    # duplicates a row anywhere (not just inside a counted segment) still
    # breaks this even if chars_moved_in == chars_moved_out happens to hold
    # (e.g. a row silently deleted instead of moved, or duplicated instead of
    # moved, with a compensating but unrelated char miscount elsewhere).
    rows_total_before = sum(len(d["rows"]) for d in docs_rows)

    report = {
        "segments_found": 0, "segments_applied": 0, "segments_quarantined": 0,
        "rows_moved": 0, "chars_moved_in": 0, "chars_moved_out": 0,
        "rows_total_before": rows_total_before, "rows_total_after": rows_total_before,
        "per_segment": [],
        "directives_recognized": {"ADD": 0, "REPLACE": 0, "REPEAL": 0},
        "directives_applied": 0,
        "unresolved": [],
    }

    # --- doc classification: code doc = the code, else the doc with most มาตรา ---
    code_idx = _primary_code_index(out_docs)
    if code_idx is None:
        return out_docs, report  # nothing to merge into (rows_total_after == rows_total_before, trivially conserved)

    # Candidate donor docs = every doc AFTER the code doc (amendment acts). The
    # enacting act BEFORE the code is never a donor.
    donor_indices = [i for i in range(code_idx + 1, len(out_docs))]

    # --- pass 1: directive recognizer over ALL donor matra/recital content ---
    for di in donor_indices:
        for r in out_docs[di]["rows"]:
            if r["raw_type"] in (4, 3):  # matra / recital
                fam = recognize_directives(r["c"])
                if fam is not None:
                    report["directives_recognized"][fam] += 1
                    report["unresolved"].append({
                        "kind": "directive_unapplied", "family": fam, "donor_doc": di,
                        "sample": (r["c"] or "")[:60],
                    })

    # --- pass 2: positional segment re-homing, in ascending donor doc index
    # (chronological ฉบับ order — so หมวด ๔ exists before หมวด ๕ anchors to it) ---
    for di in donor_indices:
        donor = out_docs[di]
        # Task 4'.2 review Finding 1: resolve-and-apply ONE segment at a time
        # against the CURRENT code rows. A donor can carry >1 structural segment
        # (multiple ลักษณะ/หมวด in one amendment act). The OLD code resolved every
        # segment's insertion index against ONE pre-insert snapshot of the code
        # doc, then applied them back-to-front by DONOR start index — correct
        # only when donor segment order happened to match ascending anchor order.
        # A donor whose segments are in anchor-DESCENDING order (e.g. ลักษณะ ๒/๑
        # listed before ลักษณะ ๑/๑) landed them in the wrong TOC positions (and
        # a shifted stale index could even mis-scope a later segment's anchor).
        # Fix: each pass, re-resolve every remaining (un-applied, non-quarantined)
        # segment against the code rows AS THEY STAND NOW, then apply the one with
        # the HIGHEST insertion index first. Inserting at the highest index never
        # shifts any lower, already-resolved index, so the remaining segments'
        # anchors stay valid; re-resolving each pass also lets a segment anchor
        # against a sibling segment of the SAME donor applied earlier this loop.
        # Single-segment donors (the entire -63 corpus) take exactly one pass —
        # one resolve, one apply — byte-for-byte the prior behavior.
        segments = _find_segments(donor["rows"])  # (start, end) spans, ascending
        report["segments_found"] += len(segments)
        # remaining spans still to place, as mutable list; each entry is the raw
        # (s, e) span into the donor's CURRENT row list (kept correct after each
        # removal by re-finding spans from the donor rows below).
        remaining = list(segments)
        while remaining:
            # resolve every remaining segment against the CURRENT code rows
            code_rows = out_docs[code_idx]["rows"]
            resolved = []      # (insert_at, s, e, seg_rows, matra_rows, head_row, rule, heading_text, payload_chars, full_chars)
            quarantine = []    # segments that cannot be placed at all this donor
            for (s, e) in remaining:
                seg_rows = donor["rows"][s:e]
                head_row = seg_rows[0]
                matra_rows = [r for r in seg_rows if r["raw_type"] == MATRA_TYPE]
                first_matra_base = _matra_base(matra_rows[0]["no"]) if matra_rows else None
                insert_at, rule = _resolve_anchor(head_row, first_matra_base, code_rows)
                heading_text = head_row["c"]
                payload_chars = sum(len(r["c"]) for r in matra_rows)
                full_chars = sum(len(r["c"]) for r in seg_rows)
                if insert_at is None:
                    quarantine.append((s, e, head_row, heading_text, rule))
                else:
                    resolved.append((insert_at, s, e, seg_rows, matra_rows, head_row,
                                     rule, heading_text, payload_chars, full_chars))

            if not resolved:
                # nothing placeable remains → quarantine all remaining, done with donor
                for (s, e, head_row, heading_text, rule) in quarantine:
                    report["segments_quarantined"] += 1
                    report["unresolved"].append({
                        "kind": "segment_quarantined", "donor_doc": di,
                        "heading": heading_text, "reason": rule,
                    })
                    report["per_segment"].append({
                        "donor_doc": di, "heading": heading_text,
                        "anchor_rule": f"QUARANTINED:{rule}", "rows": 0, "chars": 0,
                    })
                break

            # apply the single placeable segment with the HIGHEST insertion index —
            # a higher-index insert never invalidates a lower, still-unplaced index.
            (insert_at, s, e, seg_rows, matra_rows, head_row, rule,
             heading_text, payload_chars, full_chars) = max(resolved, key=lambda p: p[0])
            # Task 4'.2 review Finding 4: chars_moved_in and chars_moved_out must be
            # INDEPENDENT measurements, not the same number counted twice (the old
            # code added `full_chars` to both, so chars_moved_in == chars_moved_out
            # held by construction and the conservation check could never fail —
            # an unfireable assert). Measure each side of the physical move on its
            # own doc:
            #   chars_moved_in  = the donor segment's content chars, read from the
            #                     donor rows BEFORE removal (== full_chars).
            #   chars_moved_out = the code doc's own content-char GROWTH across the
            #                     insertion (total code chars after − before).
            # For a correct move these are equal (the same rows land whole in the
            # code doc), but now via two separate measurements, so a defective move
            # that drops/mangles chars on one side breaks the equality for real.
            code_chars_before = _content_chars(out_docs[code_idx]["rows"])
            # MOVE: insert the same row objects into the code doc, remove from donor
            out_docs[code_idx]["rows"][insert_at:insert_at] = seg_rows
            del donor["rows"][s:e]
            code_chars_after = _content_chars(out_docs[code_idx]["rows"])
            report["segments_applied"] += 1
            report["rows_moved"] += len(matra_rows)
            report["chars_moved_in"] += full_chars                          # donor-side, pre-removal
            report["chars_moved_out"] += code_chars_after - code_chars_before  # code-doc growth
            report["per_segment"].append({
                "donor_doc": di, "heading": heading_text, "anchor_rule": rule,
                "rows": len(matra_rows), "chars": payload_chars,
            })
            # re-find the donor's remaining segment spans against its NOW-shorter
            # row list (the removal shifted indices), and loop.
            remaining = _find_segments(donor["rows"])

    # sort per_segment by donor_doc for stable, human-auditable output
    report["per_segment"].sort(key=lambda x: (x["donor_doc"], x["heading"]))

    # Finding 2: total-row-count AFTER, summed across all docs post-move (rows
    # only ever relocate between docs here — never dropped, never duplicated —
    # so this must equal rows_total_before exactly).
    report["rows_total_after"] = sum(len(d["rows"]) for d in out_docs)

    # --- conservation law (internal assertion; qa reflects it as merge_conservation_ok) ---
    # These asserts are now REAL (Task 4'.2 review Finding 4): chars_moved_in is
    # the donor-side pre-removal count and chars_moved_out is the code doc's own
    # growth, two independent measurements — so a defective move that loses or
    # mangles chars on one side genuinely trips the first assert (the old code
    # added the same full_chars to both, making it unfireable). Both are pure
    # char/row totals: they prove nothing is lost or duplicated in the physical
    # move, NOT that each segment landed at the right position — placement
    # correctness is verified by the tests/goldens (TOC-order assertions), not
    # by this ledger.
    assert report["chars_moved_in"] == report["chars_moved_out"], \
        f"merge char conservation broken: in={report['chars_moved_in']} out={report['chars_moved_out']}"
    assert report["rows_total_before"] == report["rows_total_after"], \
        f"merge row conservation broken: before={report['rows_total_before']} after={report['rows_total_after']}"

    return out_docs, report


def _primary_code_index(docs):
    """Index of the code doc (doc_type == 'code'); else the doc with the most matra
    rows; None if no docs. Mirrors qa.primary_doc's selection at the row level."""
    if not docs:
        return None
    best_i, best_key = None, None
    for i, d in enumerate(docs):
        key = (d["doc_type"] == "code", sum(1 for r in d["rows"] if r["raw_type"] == MATRA_TYPE))
        if best_key is None or key > best_key:
            best_key, best_i = key, i
    return best_i
