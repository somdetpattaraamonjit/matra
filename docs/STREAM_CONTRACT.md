# Stream Contract — data changes for Stream A (viewer) & Stream B (case-law / ฎีกา)

Stream C (STANDARD / data producer) owns `src/matra/**`, `schemas/**`, `demo/build_all_laws.py`,
`docs/**`, `README.md`, and the rebuilt outputs `demo/public/data/laws.json` + `demo/public/data/laws/**`.
It does **not** touch `demo/public/index.html` (A) or `demo/public/data/deka/**` (B). This note announces
the schema/data deltas A and B will see after the latest rebuild.

## 1. Join key (the whole ecosystem depends on this) — for Stream B

```
matra_cid = "{law_code}:{matra_no_arabic}"
```

* Stable across rebuilds and across versions — `law_code` + section number survive amendment.
  Proven this session: assembled Civil Code vs single source record → **845 common มาตรา, 0 cid mismatches**.
* To join case law (ฎีกา) to a มาตรา: map the citation's law name/abbreviation → `law_code` via
  **`docs/alias_law_codes.json`**, then join on `matra_cid`.
* Sub-numbered forms (ทวิ/ตรี) keep their own `matra_no_arabic` (e.g. `1598/1`), so
  `matra_cid = "ป0003-1D-0002:1598/1"`. Match on the emitted `matra_cid` string, never a regex over prose.

### Alias table (`docs/alias_law_codes.json`) — code name → law_code

| law_code | code | aliases |
|---|---|---|
| ป0003-1D-0002 | ประมวลกฎหมายแพ่งและพาณิชย์ | ป.พ.พ., ปพพ |
| ป0006-1D-0003 | ประมวลกฎหมายอาญา | ป.อ., ปอ |
| ป0004-1D-0001 | ประมวลกฎหมายวิธีพิจารณาความแพ่ง | ป.วิ.พ., ป.วิ.แพ่ง |
| ป0005-1D-0001 | ประมวลกฎหมายวิธีพิจารณาความอาญา | ป.วิ.อ., ป.วิ.อาญา |
| ป0008-1D-0001 | ประมวลรัษฎากร | ป.รัษฎากร |
| ป0002-1D-0001 | ประมวลกฎหมายที่ดิน | — |
| ป0007-1D-0008 | ประมวลกฎหมายอาญาทหาร | — |
| ป0060-1D-0001 | ประมวลกฎหมายยาเสพติด | ป.ยาเสพติด |

## 2. New fields in `laws.json` manifest entries — for Stream A

Every entry now carries **`completeness`** (also documented in `schemas/matra-0.2.json`):

```jsonc
"completeness": {
  "present": 1755,            // base มาตรา in the navigable CODE BODY (main doc); ทวิ/ตรี share a base
  "min": 1, "max": 1755,
  "contiguous": true,
  "gaps": [],                 // interior gaps in the code body, as [lo,hi] runs
  "present_in_corpus": 1755,  // base มาตรา anywhere in the law's records
  "gaps_unmerged": [],        // gap numbers present in corpus but not yet merged into the code body
  "gaps_absent": []           // gap numbers TRULY missing from the corpus (a real, declared gap)
}
```

Assembled codes also carry `"assembled": true`, `"assembly_sources": [timeline_codes…]`, and
(in `completeness`) `"covers_union"` + `"family_union"` so any shortfall is auditable.

**All 8 -1D- code families are now navigable-complete** (`present == present_in_corpus`, `contiguous: true`,
`gaps_absent: []`, `gaps_unmerged: []`): มาตรา that the source parked in trailing amendment documents
have been relocated into the code body at their sorted position (verbatim, conservation Δ=0). Counts:
civil 1,755 · อาญา 398 · วิ.แพ่ง 323 · วิ.อาญา 267 · รัษฎากร 262 · ที่ดิน 113 · อาญาทหาร 52 · ยาเสพติด 186.
`build_report.json` carries `gap_filled_matra` and `assembly_scope`. Civil ships 6 correctly-labeled บรรพ
headings (the flat `phak` column: ม.1–193 → "บรรพ ๑ …", ม.194–452 → "บรรพ ๒ หนี้", … ม.1599–1755 → "บรรพ ๖ มรดก").

Suggested A display: show `present` มาตรา; if `gaps_absent` is non-empty, surface a real coverage gap;
if only `gaps_unmerged` is non-empty, label it "N มาตรา pending merge into the code body" (data is present).

## 3. Behavior changes A will notice

* **`main_doc_type` now resolves to `code` for every `-1D-` code family** (previously some showed
  `enacting_act` / `royal_decree` — the enacting instrument that heads the code body). Affects the
  8 codes above; the "main document = most มาตรา within declared `main_doc_type`" rule still holds.
* **Civil & Commercial Code (`ป0003-1D-0002`) is now complete**: 1,796 matra nodes / **1,755 base มาตรา,
  all 6 บรรพ** (was 845 = บรรพ 3 only), `main_doc_type: "code"`, assembled from
  `-00, -01, -03, -31, -15`. `n_matra_main` and `n_rows` change accordingly.
* No index/deka schema touched. `laws.json` / `laws/*.jsonl` regenerate deterministically via
  `PYTHONPATH=src MATRA_CORPUS_DL=… MATRA_CORPUS_RAW=… python3 demo/build_all_laws.py`.

## 4. Footer attribution (A) — `docs/attribution.json`

Machine-readable credits/licence block for the site footer (MIT code / CC-BY 4.0 data; full chain in
`docs/CREDITS.md`). Renders directly; every source has `url_verify` where a URL still needs confirming.
