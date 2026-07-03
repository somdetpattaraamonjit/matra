#!/usr/bin/env python3
"""build_law_alias.py — name→law_code alias map for in-text law linking (whole corpus).

Reads demo/public/data/laws.json (the live manifest) and emits
demo/public/data/deka/law_alias.json:

    { "schema": "matra-law-alias/v1",
      "byname": { "<norm_title_no_year>": { "<year>": "<law_code>", ... } } }

Normalization mirrors what the web matcher does: NFC + ํ+า→ำ + strip spaces +
strip "(ยกเลิก)" + strip the trailing enactment-year phrase (พ.ศ./พุทธศักราช NNNN).
Linking policy is YEAR-STRICT: the web only links a citation whose year exists
here — a cited version we don't hold must stay plain text (never link the wrong
version of a law).
"""
import json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "public", "data")
OUT  = os.path.join(DATA, "deka", "law_alias.json")

YEAR_RE = re.compile(r"(พ\.ศ\.|พุทธศักราช)\s*([0-9]{4})")

def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").replace("ํา", "ำ")
    return re.sub(r"\s+", "", s)

def main():
    m = json.load(open(os.path.join(DATA, "laws.json"), encoding="utf-8"))
    laws = m["laws"] if isinstance(m, dict) and "laws" in m else m
    byname, dup = {}, []
    for l in laws:
        title = unicodedata.normalize("NFC", l.get("title", "")).replace("ํา", "ำ")
        title = re.sub(r"\(ยกเลิก\)", "", title)
        years = YEAR_RE.findall(title)
        year = years[-1][1] if years else ""
        # name = title minus the LAST year phrase (inner years, e.g. ให้ใช้ฯ, stay in the name)
        name = title
        if years:
            i = title.rfind(years[-1][0])
            name = title[:i]
        key = norm(name)
        if not key:
            continue
        slot = byname.setdefault(key, {})
        if year in slot and slot[year] != l["law_code"]:
            dup.append((key, year, slot[year], l["law_code"]))
            continue  # keep first
        slot[year] = l["law_code"]
    out = {"schema": "matra-law-alias/v1", "n_laws": len(laws),
           "n_names": len(byname), "byname": byname}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"))
    print(f"law_alias.json: {len(byname):,} names / {len(laws):,} laws · "
          f"dups kept-first: {len(dup)} · {os.path.getsize(OUT):,} bytes")
    for d in dup[:5]: print("  dup:", d)
    # self-check: the case ICE reported must resolve
    k = norm("พระราชบัญญัติการเลือกตั้งสมาชิกสภาผู้แทนราษฎร")
    assert byname.get(k, {}).get("2522"), "election act 2522 missing from alias"
    print("self-check ก0051 (เลือกตั้ง สส. 2522):", byname[k]["2522"])

if __name__ == "__main__":
    main()
