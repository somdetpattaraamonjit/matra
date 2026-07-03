"""Task 6′ — stable identifiers: matra_cid + eId/wId + extract_refs (v0).

Pure functions, stdlib only, no I/O, no network, no imports outside this
package. Design decisions binding this module (docs/akn_adoption_verdicts.md
§Design decisions 1-5, Lindy Gate run 2026-07-02):

  1. matra_cid = f"{law_group_code}:{number_arabic}" VERBATIM, set on
     node_type=="matra" nodes only. number_arabic real forms ("334",
     "135/1", "335 ทวิ") are NEVER normalized inside cid — stability is
     group+number surviving amendment, not a canonical string shape.

  2. eId = ASCII structural id using AKN element names: matra->art,
     phak->part, laksana->title, muad->chapter, suan->subchapter,
     kho->clause, bot->transitional. Containers are hierarchically
     qualified via the parent chain (part_2__title_1_1) because ลักษณะ
     numbering restarts per ภาค — unqualified ids would collide across
     ภาค. มาตรา ids are left unqualified (art_135_1) because มาตรา numbers
     are continuous within one doc; uniqueness scope is the whole doc
     envelope for both container and matra eIds.

  3. eId collisions (real case: digit-defect sectionId 6466038 puts a
     second title_1 under part_2 in the -63 corpus) get a deterministic
     __d2, __d3, ... suffix assigned in `order` order, with an
     eid_collision flag set on the later node(s). number/number_arabic are
     never mutated — the defect stays annotated, not corrected.

  4. wId = eId at first assignment (v0 contract: wId == eId, always a
     separate field so a later divergence — wId frozen across renumbering
     while eId is recomputed — is a pure additive change, not a breaking
     one).

  5. Nodes whose number_arabic is None or empty (promulgation, recital,
     bare paragraph rows, ...) get eId = None and are skipped silently:
     no eid_sanitized, no eid_collision flag on them.

extract_refs is the v0 regex baseline from the plan (Task 7 baseline +
suffix tuning): Thai-digit translate, then regex on
"มาตรา <num>[ ทวิ|ตรี|จัตวา]" with an optional "แห่ง<law>" suffix.
"""
import re

# ---- AKN element name map (verdicts doc §2) ----
_AKN_ELEMENT = {
    "matra": "art",
    "phak": "part",
    "laksana": "title",
    "muad": "chapter",
    "suan": "subchapter",
    "kho": "clause",
    "bot": "transitional",
}

# ---- Thai-digit -> arabic (same convention as merge.py's _arab) ----
_TH_DIGITS = "๐๑๒๓๔๕๖๗๘๙"
_TR = {c: str(i) for i, c in enumerate(_TH_DIGITS)}


def _arab(s):
    """Translate any Thai digits in a string to arabic; None-safe."""
    if s is None:
        return None
    return "".join(_TR.get(c, c) for c in s)


# ---- eId number normalization (verdicts doc §2) ----
# suffix WORD (space-separated, at the end of the number) -> ASCII suffix.
# Full Latin legal-ordinal set matching the suffix words structure.py:129
# already recognizes in the wild (review 6′ Minor #2: mapping only the 3
# originally-profiled suffixes would silently sanitize e.g. "335 เบญจ").
_SUFFIX_WORD = {
    "ทวิ": "bis", "ตรี": "ter", "จัตวา": "quater", "เบญจ": "quinquies",
    "ฉ": "sexies", "สัตต": "septies", "อัฏฐ": "octies", "นว": "novies",
    "ทศ": "decies",
}

_RESIDUAL_NON_ASCII_ID = re.compile(r"[^A-Za-z0-9_]")


def _norm_number(number_arabic):
    """Normalize a real number_arabic string into the ASCII fragment used
    inside an eId. Returns (normalized_str, was_sanitized_bool).

    Steps (verdicts doc §2, literal order):
      1. '/' -> '_'
      2. trailing suffix WORD (ทวิ/ตรี/จัตวา), space-separated -> ASCII
         suffix (bis/ter/quater), e.g. "335 ทวิ" -> "335_bis"
      3. remaining spaces -> '_'
      4. residual non-[A-Za-z0-9_] characters are DROPPED (not replaced)
         and the sanitized flag is set True.
    """
    s = number_arabic.replace("/", "_")
    parts = s.split(" ")
    if len(parts) > 1 and parts[-1] in _SUFFIX_WORD:
        s = "_".join(parts[:-1]) + "_" + _SUFFIX_WORD[parts[-1]]
    else:
        s = "_".join(parts)
    sanitized = bool(_RESIDUAL_NON_ASCII_ID.search(s))
    s = _RESIDUAL_NON_ASCII_ID.sub("", s)
    return s, sanitized


def assign_cids(nodes: list[dict], law_group_code: str) -> list[dict]:
    """Set matra_cid = f"{law_group_code}:{number_arabic}" VERBATIM on every
    node_type=="matra" node. Non-matra nodes get NO matra_cid key at all
    (not even None) — absence, not null, marks "not applicable".

    Mutates and returns the same node dicts (matches the existing pipeline's
    convention of in-place-list-of-dicts passing, e.g. structure.py); never
    touches number/number_arabic (conservation law).
    """
    for n in nodes:
        if n.get("node_type") == "matra":
            n["matra_cid"] = f"{law_group_code}:{n['number_arabic']}"
    return nodes


def assign_eids(nodes: list[dict]) -> list[dict]:
    """Set eId + wId on every displayable structural node (matra + the AKN
    container types). Skips nodes with a None/empty number_arabic (eId=None,
    no flag). Handles collisions (two siblings whose computed eId would be
    identical) with a deterministic __d2/__d3... suffix in `order` order,
    flagging every node after the first with eid_collision=True.

    Containers are hierarchically qualified via the parent chain (each
    container's eId is prefixed with its own parent container's eId,
    joined by '__') because ลักษณะ (and similar) numbering restarts per
    ภาค. มาตรา eIds are left unqualified — uniqueness scope is the whole
    doc (one call to this function = one doc envelope's node list).
    """
    by_id = {n["node_id"]: n for n in nodes if "node_id" in n}

    def parent_eid(node):
        pid = node.get("parent_id")
        if pid is None or pid not in by_id:
            return None
        return by_id[pid].get("eId")

    # Assign in a stable order so hierarchical qualification always sees an
    # already-resolved parent eId; `nodes` is already emitted in build order
    # (parents always precede children in structure.py's node list), and we
    # additionally sort by `order` (falling back to list position) for
    # deterministic collision-suffix assignment per the verdicts doc.
    ordered = sorted(range(len(nodes)), key=lambda i: nodes[i].get("order", i))

    seen_base = {}  # base eId (pre-collision-suffix) -> count of prior nodes with it
    for i in ordered:
        n = nodes[i]
        number_arabic = n.get("number_arabic")
        if not number_arabic:  # None or "" — skip silently, no flag
            n["eId"] = None
            n["wId"] = None
            continue

        norm, sanitized = _norm_number(number_arabic)
        element = _AKN_ELEMENT.get(n.get("node_type"))
        if element is None:
            # Unknown/non-AKN node_type (e.g. paragraph, promulgation) that
            # nonetheless carries a number_arabic — no id scheme applies.
            n["eId"] = None
            n["wId"] = None
            continue

        base = f"{element}_{norm}"
        if element != "art":  # containers: hierarchically qualify via parent
            pe = parent_eid(n)
            if pe:
                base = f"{pe}__{base}"

        count = seen_base.get(base, 0)
        if count == 0:
            eid = base
        else:
            eid = f"{base}__d{count + 1}"
            n["eid_collision"] = True
        seen_base[base] = count + 1

        if sanitized:
            n["eid_sanitized"] = True
        n["eId"] = eid
        n["wId"] = eid  # v0 contract: wId == eId at first assignment

    return nodes


# ---- extract_refs v0 (plan Task 7 baseline + suffix tuning) ----
# มาตรา <num>[ ทวิ|ตรี|จัตวา] with optional แห่ง<law-name>, tuned from the
# plan's starting regex to require a plausible มาตรา-number token (so plain
# prose without any มาตรา reference never over-matches) and to stop the law
# name at sentence-ish punctuation/whitespace boundaries.
_REF_RE = re.compile(
    r"มาตรา\s*([0-9/]+(?:\s*(?:ทวิ|ตรี|จัตวา))?)"
    r"(?:\s*แห่ง\s*([ก-๙A-Za-z.\s]+?))?"
    r"(?=[\s,]|$)"
)


def extract_refs(text: str) -> list[dict]:
    """Extract มาตรา cross-references from free text.

    Returns a list of {"target_doc": str|None, "target_matra": str,
    "raw_text": str} per match, in a v0 regex baseline: Thai digits are
    translated to arabic first, then the pattern above is applied.
    target_matra is returned Arabic (never Thai digits). target_doc is the
    law name (trimmed) when a แห่ง<law> suffix is present, else None.
    Never mutates the input text; text without any มาตรา reference returns
    [] (no over-matching).
    """
    translated = _arab(text)
    refs = []
    for m in _REF_RE.finditer(translated):
        raw_num, raw_doc = m.group(1), m.group(2)
        target_matra = re.sub(r"\s+", " ", raw_num).strip()
        target_doc = raw_doc.strip() if raw_doc else None
        refs.append({
            "target_doc": target_doc,
            "target_matra": target_matra,
            "raw_text": m.group(0).strip(),
        })
    return refs
