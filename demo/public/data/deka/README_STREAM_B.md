# deka/ — MATRA Stream B deliverable  (A: plug in · C: credit)

## Contract file: `index.json`  (schema `matra-deka/v1`)
Keyed by **matra_cid** = `{law_code}:{section}` **verbatim** (matches `src/matra/cid.py`), e.g. `ป0006-1D-0003:334`, `ป0006-1D-0003:336 ทวิ`.

> This **supersedes `l0088.json`**. Do NOT key deka by `lNNNN` — those indices are reassigned every rebuild → the ⚖️ button vanished (defect "DEKA-ORPHAN", 2026-07-02). matra_cid embeds the stable `law_code`, so it survives rebuilds. That orphan class is now fixed by construction.

Per entry:
```json
"ป0006-1D-0003:334": {
  "law_code":"ป0006-1D-0003","section":"334",
  "count":298,                       // distinct Supreme Court cases citing this มาตรา (TRUSTED, see below)
  "cases":[{"case_id":"3672/2568","case_year":"2568"}, ...up to 25, newest first],
  "n_cases_listed":25,
  "official_search":"https://deka.supremecourt.or.th"
}
```

## A — integration
- On a มาตรา view for `(law_code, section)` → look up `index[f"{law_code}:{section}"]`.
- If present → render ⚖️ `ฎีกาที่อ้างมาตรานี้ ({count})` → modal shows `cases[]` + official link.
- **Honesty label (required):** `count` is phoneee coverage (**87,525** distinct cases of ~133,119 official; snapshot **2026-03-10** + 99 post-snapshot delta). Show "จากชุดข้อมูล phoneee" — not exhaustive. When `count > 25`, show "แสดง 25 จาก {count}" + `official_search` for the rest.
- ~~No summary/ย่อ text in this dataset~~ **superseded 2026-07-03** — ย่อ + ฉบับเต็ม now ship per case (see "Case text" section below). Each case also ships its **co-cited มาตรา** (the other provisions the ruling cites): originally the sidecar `case_refs.json` (schema `matra-deka-refs/v1`, keyed by `case_id`), now inlined per entry in `bymatra/` — a "what is this case about" fingerprint instead of a bare number. Chips jump to the cited มาตรา (same-code in place, cross-code switches law).
- Covered law_codes = 5 featured codes + ~270 others. `coverage.json` audits mapped/unmapped (nothing dropped silently).

## C — credit (footer/README, REQUIRED by CC-BY-4.0)
> ข้อมูลคำพิพากษาศาลฎีกา (สาธารณสมบัติ, พ.ร.บ.ลิขสิทธิ์ พ.ศ.2537 ม.7(4)) จาก **deka.supremecourt.or.th**; citation metadata: **phoneee/thai-legal-corpus** (CC-BY-4.0).

New schema `schemas/matra-deka.json` is **additive** — `matra-0.2.json` untouched. Please wire this credit into the site footer/README before publish.

## Provenance / counts — why they're trustworthy
`count` comes from **inverting `deka_citations.jsonl`** (distinct `case_id` per มาตรา), verified **6/7 EXACT vs official** (l0088). `law_section_index.json` was **rejected** — its per-section counts are duplication-inflated (sections 1–17 repeated ~65×; ม.334/335 absent). Do not resurrect it for counts.

## Freshness / delta (live-verified 2026-07-03)
Cross-checked **15 official cases live** on deka.supremecourt.or.th: **14/14 law-blocks EXACT** on the 9 present in phoneee (precision 100%). Then **fully backfilled the post-snapshot period** (phoneee snapshot = 2026-03-10): **ปี 2569 0→11 (all official)**, **ปี 2568 135→218 distinct** — **94 delta cases** in `raw/delta_*.jsonl`, folded into `index.json` counts. (2568's remaining 48 of 266 cite only พ.ร.บ. → no MATRA มาตรา to index, omitted by design.) Method: pagination `/search/index/N` (GET, session-kept) + in-page JS `fetch`+extract → parser → `build_index.py` (auto-includes `delta_*.jsonl`, halt-on-seen). Official site is HTML+CAPTCHA (no JSON API); GET pagination isn't captcha-gated, no bypass. See `~/.aice/legalrag/deka/DELTA_FETCH_DESIGN.md`.

## Case text — ครบทุกคดี + ย่อ + ฉบับเต็ม + filter (2026-07-03, schema `matra-deka-text/v2`)
`~/.aice/legalrag/deka/build_case_text.py` (v3) inverts the SAME trusted citation graph as `build_index.py`
(mapping logic copied verbatim) → **ALL cases per มาตรา** (209,566 entries — ไม่ใช่ ≤25 เดิม; design
principle: แสดง 4 หรือ 400 ฎีกาต้องต่างกัน), joined to the phoneee full corpus.
**JOIN:** `doc_id = "deka-" + case_id.replace("/","")` (concat — the dashed form lives only in `deka_citations.jsonl`; never join on that).
**Anti-misjoin = 100% (not spot-check):** matched text must START with `คำพิพากษาศาลฎีกาที่ <case_id>`; mismatch → excluded + logged (45 excluded this build).
- `bymatra_map.json` — { matra_cid : "mNNNNN" } (~0.3MB, lazy once on first modal open)
- `bymatra/mNNNNN.json` — **FULL case list**, newest first: `{"list":[{"id","y","s"(ย่อ ≤700, absent if not in phoneee),"r"(co-cite tokens ≤12, INLINED — modal no longer fetches case_refs.json)}]}` → 1 fetch/modal; biggest = ม.55 ป.วิ.พ. 3,348 คดี < 8MB raw. Modal UI: ค้นในย่อ/เลขคดี + กรองปี + chunked render 60 + counter.
- `fulltext/s{digits(case_id)%512}.json` — ตัวคำพิพากษาเต็ม **ทุกคดีที่ phoneee มี (87,363)**; loaded ONLY on "อ่านฉบับเต็ม" click (~7MB raw/~1.7MB gz, session-cached). **512 must match `DK_NFULL` in index.html.** Every file <25MiB; public total ~4.1GB / ~9.7k files (limits: 25MiB/file + 20k files ✓).
- `case_text_report.json` — audit: **matched 87,363/87,525 (99.81%)**; missing 162 ≈ post-snapshot delta cases → UI แสดงตรงๆ "ไม่อยู่ในชุดข้อมูลเปิด" + ลิงก์ระบบทางการ (ไม่มั่ว)
- `case_refs.json` (v1) kept for compat; modal path no longer reads it (refs inlined in bymatra).
- Rebuild needs the 6GB phoneee download (`~/.aice/phoneee_dl/`; re-fetch via `~/.aice/phoneee_fetch.sh`).
- ⚠️ **Git:** `fulltext/` + `bymatra/` ≈ 3.9GB reproducible artifacts — decide .gitignore vs commit BEFORE Wed public flip (see publish pack).

## Files (scope B, this session)
`demo/public/data/deka/` → `index.json` (contract), `case_refs.json` (co-citation sidecar, `matra-deka-refs/v1`), `coverage.json` (audit), `README_STREAM_B.md`
`schemas/matra-deka.json`, `schemas/matra-deka-refs.json` · `~/.aice/legalrag/deka/` → `build_index.py`, `build_case_refs.py`, `verify_dod.py`, `fetch_metadata.sh`, `GATE_VERDICT.md/.json`, `DELTA_FETCH_DESIGN.md`
