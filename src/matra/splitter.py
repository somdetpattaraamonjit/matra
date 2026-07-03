# Vendored from ~/.aice/legalrag/pipeline/normalize.py (engine lane, 2026-07-02) on 2026-07-03; behavior locked byte-level by tests/golden/normalize_63.golden.json
"""Stage 2 — split a raw record's flat section rows into per-document row groups.

Pure: every input is an argument, no globals, no I/O. This is pass 1 of the
engine normalizer: walk record["sections"] in order and start a new doc at
each doc_title (sectionTypeId == 1) boundary.
"""
import re

TYPE_MAP = {1: "doc_title", 2: "promulgation", 3: "recital", 4: "matra", 6: "phak",
            7: "laksana", 8: "muad", 9: "suan", 10: "kho", 13: "bot", 14: "countersign",
            15: "remark", 16: "source_toc"}


def clean(s):
    if s is None: return ""
    s = s.replace(" "," ").replace(" "," ")
    return re.sub(r"[ \t]+", " ", s).strip()


def doc_type_of(title):
    t = title
    if "ให้ใช้ประมวล" in t: return "enacting_act"
    if t.startswith("ประมวล") or (t.startswith("ประมวลกฎหมาย")): return "code"
    if "ประกาศของคณะปฏิวัติ" in t: return "announcement"
    if t.startswith("พระราชกำหนด"): return "emergency_decree"
    if t.startswith("พระราชกฤษฎีกา"): return "royal_decree"
    if t.startswith("กฎกระทรวง"): return "ministerial_regulation"
    return "act"


def split_record(record):
    """Split record["sections"] into per-doc row groups at doc_title boundaries.

    Returns a list of {"title", "doc_type", "rows"} dicts, each "rows" entry
    being {"i", "t", "no", "name", "c", "raw_type"}. Verbatim behavior of the
    engine's normalize() pass 1 (lines 39-51 of the vendored-from file).
    """
    rows = record["sections"]
    docs, cur = [], None
    for i, s in enumerate(rows):
        ttype = TYPE_MAP.get(s.get("sectionTypeId"))
        if ttype is None:  # unknown type — surface loudly, never guess
            ttype = f"unknown_{s.get('sectionTypeId')}"
        content = clean(s.get("content"))
        if ttype == "doc_title":
            cur = {"title": content, "doc_type": doc_type_of(content), "rows": []}
            docs.append(cur); continue
        if cur is None:  # content before first title
            cur = {"title": "(untitled)", "doc_type": "act", "rows": []}; docs.append(cur)
        cur["rows"].append({"i": i, "t": ttype, "no": s.get("sectionNo"),
                            "name": s.get("sectionName"), "c": content,
                            "raw_type": s.get("sectionTypeId")})
    return docs
