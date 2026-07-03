"""Stage — cross-record code assembly (consolidate a fragmented code family).

Most laws arrive as ONE record per timeline version, and the pipeline builds
the newest non-empty record. But a few codes are stored *across many records* —
one enacting instrument per structural Book (บรรพ) — with NO single consolidated
record holding the whole code. The Civil & Commercial Code (ป0003-1D-0002) is
the clear case: 73 records, whose union is all 1,755 มาตรา across 6 บรรพ, yet the
fullest *single* record holds only บรรพ 3 (มาตรา 453–1297, 845 มาตรา). Picking the
fullest single record silently drops 5 of 6 Books.

This module detects that condition and assembles the code from the clean
code-body holder per Book:

  * candidates = split-docs whose title enacts a code ("ให้ใช้บทบัญญัติ" or
    starts "ประมวลกฎหมาย"), never an amendment/re-enactment act ("แก้ไขเพิ่มเติม",
    "ฉบับที่", …);
  * each candidate contributes ITS Book's มาตรา numbers — for act-form enacting
    instruments a small, far-separated leading run (the act's own preamble
    มาตรา 1/2/3, which collide with code numbering) is dropped;
  * cover priority: a `code`-typed doc beats an enacting `royal_decree`, which
    beats a bare enacting `act`; then newer seq, larger block, stable id. Each
    winner claims its Book's มาตรา that are still unclaimed. Emission is by the
    CLAIMED number set (never a raw range span), so two Books can never
    double-emit the same มาตรา — the assembly asserts zero duplicates.

Conservation: every emitted section is a *verbatim* raw section from a source
record (assembly moves rows by reference, never rewrites text). The only
injected rows are derived Book (บรรพ) container headings — navigation
scaffolding, declared, counted symmetrically in QA (typeId 6, in BODY_TYPES).

Pure: every input is an argument, no globals, no I/O.
"""
import re
import unicodedata

from .splitter import split_record

_TH = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
_AR = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")
HIER = {"phak", "laksana", "muad", "suan"}
CODE_TIER = {"code": 2, "royal_decree": 1, "enacting_act": 1}   # act / others → 0
MIN_BLOCK = 40                 # a real Book is hundreds of มาตรา; amendment runs are tiny/scattered
PREAMBLE_MAX = 20              # an enacting act's own preamble is a handful of มาตรา…
PREAMBLE_GAP = 50              # …separated by a large jump from the Book body
ASSEMBLY_THRESHOLD = 0.95      # fullest single record must cover >=95% of the union, else assemble
_AMEND_TOKENS = ("แก้ไขเพิ่มเติม", "ฉบับที่", "แก้ไข")   # title markers of an amendment/re-enactment

# Civil & Commercial Code — the one known fragmented family. Canonical Book names
# are legal facts (บรรพ 3 IS เอกเทศสัญญา); used only as derived container labels.
CIVIL_CODE = "ป0003-1D-0002"
CIVIL_BOOK_RANGES = [(1, 193, "บรรพ ๑ บทเบ็ดเสร็จทั่วไป"), (194, 452, "บรรพ ๒ หนี้"),
                     (453, 1297, "บรรพ ๓ เอกเทศสัญญา"), (1298, 1434, "บรรพ ๔ ทรัพย์สิน"),
                     (1435, 1598, "บรรพ ๕ ครอบครัว"), (1599, 1755, "บรรพ ๖ มรดก")]


def to_int(x):
    """Base มาตรา number as int — handles arabic/Thai digits and every sub-number
    form (`335/1`, `๓๓๕/๑`, `335 ทวิ`, `๓๓๕ ทวิ`). Leading integer wins; None if none."""
    if x is None:
        return None
    m = re.match(r"\s*(\d+)", str(x).translate(_TH))
    return int(m.group(1)) if m else None


def seq_of(timeline_code):
    try:
        return int(timeline_code.rsplit("-", 1)[1])
    except (AttributeError, ValueError, IndexError):
        return -1


def matra_numbers(record):
    """Distinct base มาตรา numbers (typeId 4) in a raw record, as ints."""
    return sorted({n for n in (to_int(s.get("sectionNo"))
                               for s in (record.get("sections") or [])
                               if s.get("sectionTypeId") == 4) if n is not None})


def family_union(records):
    """Distinct base มาตรา numbers across every record of a family."""
    u = set()
    for r in records.values():
        u.update(matra_numbers(r))
    return sorted(u)


def needs_assembly(records, threshold=ASSEMBLY_THRESHOLD):
    """True when NO single record holds (nearly) the whole family — i.e. the
    code is fragmented across records and must be consolidated."""
    union = family_union(records)
    if not union:
        return False
    best = max((len(matra_numbers(r)) for r in records.values()), default=0)
    return best < threshold * len(union)


def completeness_of(nums, expected_max=None):
    """Describe coverage of a มาตรา list: present count, range, contiguity, and
    interior gaps (missing runs within [min,max])."""
    nums = sorted(set(nums))
    if not nums:
        return {"present": 0, "min": None, "max": None, "contiguous": True, "gaps": []}
    lo, hi = nums[0], nums[-1]
    have = set(nums)
    gaps, run_start = [], None
    for n in range(lo, hi + 1):
        if n not in have and run_start is None:
            run_start = n
        elif n in have and run_start is not None:
            gaps.append([run_start, n - 1]); run_start = None
    if run_start is not None:
        gaps.append([run_start, hi])
    out = {"present": len(nums), "min": lo, "max": hi, "contiguous": not gaps, "gaps": gaps}
    if expected_max is not None:
        out["expected_max"] = expected_max
    return out


def _runs(nums):
    """Maximal contiguous runs of a sorted distinct int list → [(lo,hi), …]."""
    if not nums:
        return []
    runs, lo, prev = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
        else:
            runs.append((lo, prev)); lo = prev = n
    runs.append((lo, prev))
    return runs


def _book_nums(doc):
    """The Book's base มาตรา numbers contributed by a candidate doc. For an
    act-form enacting instrument, a small far-separated LEADING run (the act's
    own preamble มาตรา 1/2/3) is dropped so it can never contaminate the code's
    own numbering. code/royal_decree holders start at their Book's first มาตรา
    (their มาตรา 1 IS the code's), so nothing is dropped from them."""
    nums = sorted({to_int(r["no"]) for r in doc["rows"]
                   if r["t"] == "matra" and to_int(r["no"]) is not None})
    if not nums:
        return set()
    runs = _runs(nums)
    if CODE_TIER.get(doc["doc_type"], 0) == 0:      # act-typed → strip leading preamble run(s)
        while len(runs) > 1 and (runs[0][1] - runs[0][0] + 1) <= PREAMBLE_MAX \
                and (runs[1][0] - runs[0][1]) > PREAMBLE_GAP:
            runs.pop(0)
    return {n for lo, hi in runs for n in range(lo, hi + 1)}


def _candidates(records):
    """Code-body candidate docs across a family: (tc, seq, tier, doc, book_nums)."""
    cands = []
    for tc, rec in records.items():
        for doc in split_record(rec):
            title = doc["title"]
            if any(tok in title for tok in _AMEND_TOKENS):
                continue
            if not ("ให้ใช้บทบัญญัติ" in title or title.startswith("ประมวลกฎหมาย")):
                continue
            book = _book_nums(doc)
            if len(book) < MIN_BLOCK:
                continue
            cands.append({"tc": tc, "seq": seq_of(tc), "tier": CODE_TIER.get(doc["doc_type"], 0),
                          "doc": doc, "rec": rec, "book": book})
    return cands


def _emit_sections(doc, rec, claimed):
    """Verbatim raw sections of a doc for exactly the CLAIMED base numbers:
    the claimed มาตรา (their วรรค), plus structural headings within their span
    (leading ancestor headings included). A มาตรา claimed by another winner is
    skipped — emission can never double-count."""
    rows = doc["rows"]
    positions = [ri for ri, r in enumerate(rows)
                 if r["t"] == "matra" and to_int(r["no"]) in claimed]
    if not positions:
        return []
    start, last = positions[0], positions[-1]
    while start > 0 and rows[start - 1]["t"] in HIER:      # keep the Book's opening ลักษณะ/หมวด
        start -= 1
    out = []
    for ri in range(start, last + 1):
        r = rows[ri]
        if r["t"] == "matra":
            if to_int(r["no"]) in claimed:
                out.append(rec["sections"][r["i"]])
        else:
            out.append(rec["sections"][r["i"]])
    return out


def complete_code_record(record):
    """Fill a code body's number-gaps from มาตรา parked in the SAME record's
    trailing amendment documents (the "amendment parked at the end instead of
    merged into place" pattern). For each missing base number in the code doc's
    [min,max] range, if a non-code doc holds that มาตรา as a substantive section
    (content begins "มาตรา"), its section(s) are RELOCATED — verbatim, by
    reference — to just after the code's preceding มาตรา, so the consolidated
    code is navigable-complete. Sections are moved, never rewritten or dropped,
    so character/row conservation holds. Returns (record', filled_numbers).

    Only fills GAPS (never touches a number the code body already has), so an
    amendment act's own preamble มาตรา 1/2/3 can never overwrite the code — they
    are not gaps."""
    docs = split_record(record)
    if len(docs) < 2:
        return record, []

    def nmat(d):
        return len({to_int(r["no"]) for r in d["rows"]
                    if r["t"] == "matra" and to_int(r["no"]) is not None})
    code_di = max(range(len(docs)), key=lambda i: nmat(docs[i]))
    code_last_i = {}                       # code base number -> index of its last วรรค section
    for r in docs[code_di]["rows"]:
        if r["t"] == "matra":
            b = to_int(r["no"])
            if b is not None:
                code_last_i[b] = r["i"]
    if not code_last_i:
        return record, []
    lo = min(code_last_i)

    # donor code-มาตรา from every OTHER doc: a มาตรา that belongs to that doc's
    # code BODY (its own preamble มาตรา 1/2/3 excluded via _book_nums), is NOT
    # already in the code body, sits at/above the code's first number, and reads
    # as a substantive section. Fills interior gaps AND trailing มาตรา; the later
    # (newer) holding doc wins. Never touches a number the code already has, so an
    # amendment act's own preamble can never overwrite the code.
    donors = {}
    for di, d in enumerate(docs):
        if di == code_di:
            continue
        body = _book_nums(d)
        by_base = {}
        for r in d["rows"]:
            if r["t"] == "matra":
                b = to_int(r["no"])
                if b is not None and b in body:
                    by_base.setdefault(b, []).append(record["sections"][r["i"]])
        for b, secs in by_base.items():
            if b not in code_last_i and b >= lo and (secs[0].get("content") or "").lstrip().startswith("มาตรา"):
                donors[b] = secs
    if not donors:
        return record, []

    donor_ids = {id(s) for secs in donors.values() for s in secs}
    after = {}                             # section index -> [gap numbers to insert after it]
    for b in donors:
        preds = [x for x in code_last_i if x < b]
        if preds:
            after.setdefault(code_last_i[max(preds)], []).append(b)
    out = []
    for idx, s in enumerate(record["sections"]):
        if id(s) in donor_ids:             # relocated below — skip at original position
            continue
        out.append(s)
        for b in sorted(after.get(idx, [])):
            out.extend(donors[b])
    new_rec = dict(record)
    new_rec["sections"] = out
    return new_rec, sorted(b for b in donors if [x for x in code_last_i if x < b])


def assemble_code(records, law_code, title=None, book_labels=None):
    """Consolidate a fragmented code family into ONE synthetic record.

    Returns (synthetic_record, report). The synthetic record is pipeline-shaped
    (law_code, timeline_code, title, reference_url, sections) with a single
    typeId-1 code title so the splitter classifies it `code`. Sections are the
    verbatim raw sections of each winning Book, in มาตรา order, each Book
    preceded by a derived typeId-6 container heading.
    """
    cands = _candidates(records)
    # cover: strongest source first — code > royal_decree > act, then newest seq,
    # then larger Book, then stable id (fully deterministic; no arbitrary ties).
    claimed = {}          # base number -> winning candidate
    winners = []
    for c in sorted(cands, key=lambda c: (c["tier"], c["seq"], len(c["book"]), c["tc"]), reverse=True):
        gained = c["book"] - claimed.keys()
        if not gained:
            continue
        for n in gained:
            claimed[n] = c
        c["claimed"] = gained
        winners.append(c)
    winners.sort(key=lambda c: min(c["claimed"]))          # Books in มาตรา order

    if title is None:
        newest = max(records.values(), key=lambda r: seq_of(r.get("timeline_code", "")))
        title = unicodedata.normalize("NFC", (newest.get("title") or "").strip()) or law_code

    win_secs, provenance, emitted = [], [], []
    for c in winners:
        secs = _emit_sections(c["doc"], c["rec"], c["claimed"])
        win_secs.append(secs)
        nums = sorted({to_int(s.get("sectionNo")) for s in secs
                       if s.get("sectionTypeId") == 4 and to_int(s.get("sectionNo")) is not None})
        emitted += nums
        provenance.append({"source_timeline_code": c["tc"], "source_doc_type": c["doc"]["doc_type"],
                           "matra_lo": min(c["claimed"]), "matra_hi": max(c["claimed"]), "matra_count": len(nums)})
    all_secs = [s for secs in win_secs for s in secs]

    sections = [{"sectionTypeId": 1, "sectionNo": None, "content": title, "_derived": True}]
    if book_labels is None and law_code == CIVIL_CODE:
        # Inject บรรพ headings at the 6 KNOWN Book boundaries (legal facts) — one
        # enacting record (-00) physically carries บรรพ 1 AND 2, so a per-winner
        # heading would mislabel มาตรา 194–452. Each section is tagged with the
        # Book of the NEXT มาตรา (so a Book's opening ลักษณะ heading sits under the
        # right บรรพ), and a heading is emitted at each Book transition.
        def _book_of(n):
            for idx, (lo, hi, _) in enumerate(CIVIL_BOOK_RANGES):
                if lo <= n <= hi:
                    return idx
            return None
        nb, bk = None, [None] * len(all_secs)
        for i in range(len(all_secs) - 1, -1, -1):
            if all_secs[i].get("sectionTypeId") == 4:
                n = to_int(all_secs[i].get("sectionNo"))
                if n is not None:
                    nb = _book_of(n)
            bk[i] = nb
        cur = None
        for s, b in zip(all_secs, bk):
            if b is not None and b != cur:
                sections.append({"sectionTypeId": 6, "sectionNo": str(b + 1),
                                 "content": CIVIL_BOOK_RANGES[b][2], "_derived": True})
                cur = b
            sections.append(s)
    else:
        labels = book_labels or [f"บรรพ {str(i + 1).translate(_AR)}" for i in range(len(winners))]
        for i, secs in enumerate(win_secs):
            sections.append({"sectionTypeId": 6, "sectionNo": str(i + 1),
                             "content": labels[i] if i < len(labels) else f"บรรพ {i + 1}", "_derived": True})
            sections.extend(secs)

    dup = len(emitted) - len(set(emitted))
    assert dup == 0, f"assembly emitted {dup} duplicate มาตรา for {law_code} — cover overlap bug"
    union = family_union(records)
    max_seq = max((seq_of(tc) for tc in records), default=0)
    synthetic = {
        "law_code": law_code,
        "timeline_code": f"{law_code}-{max_seq}",
        "title": title,
        "reference_url": winners[0]["rec"].get("reference_url", "") if winners else "",
        "sections": sections,
        "_assembled": True,
    }
    report = {
        "assembled": True,
        "law_code": law_code,
        "books": provenance,
        "matra_present": len(set(emitted)),
        "family_union": len(union),
        "duplicate_matra": dup,
        "covers_union": set(emitted) == set(union),
        "completeness": completeness_of(emitted),
        "source_records_used": [c["tc"] for c in winners],
    }
    return synthetic, report
