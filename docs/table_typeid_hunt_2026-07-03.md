# Table sectionTypeId Hunt (5, 11, 12) — 2026-07-03

Bounded probe (~20 min). Goal: find sectionTypeId 5/11/12 ("TABLE") in the
ocs-krisdika corpus — unseen across 220 prior sampled law groups. Customer
promised a check on tax/tariff laws ("บางอันมีตาราง").

## Candidates checked

Picked from `tree_main.json` (confirmed paths before download, no guessing),
downloaded host-side via osascript into the shared cache, verified byte-exact
against tree_main.json sizes:

| File | Size | Target law |
|---|---|---|
| `data/1939/1939-04.jsonl` | 5,654,128 B | ประมวลรัษฎากร (Revenue Code) — พ.ร.บ.ให้ใช้ฯ 2481 |
| `data/1987/1987-12.jsonl` | 2,490,443 B | พระราชกำหนดพิกัดอัตราศุลกากร พ.ศ. 2530 (Customs Tariff) |
| `data/2017/2017-03.jsonl` | 1,447,001 B | พระราชบัญญัติภาษีสรรพสามิต พ.ศ. 2560 (Excise Tax) |

Total downloaded: ~9.6MB (well under the 60MB cap).

All three candidate laws were confirmed present with real (non-empty)
`sections[]` content:
- **ประมวลรัษฎากร** — 9 non-empty timeline versions (up to 644 sections each; many other `is_latest=true` timeline rows have `sections: []`, i.e. stub/pointer rows for that law_code).
- **พระราชกำหนดพิกัดอัตราศุลกากร พ.ศ. 2530** — 15 timeline versions, up to 146 sections.
- **พระราชบัญญัติภาษีสรรพสามิต พ.ศ. 2560** — 2 timeline versions, up to 516 sections.

## Census

Note: `sectionTypeId` lives at `record.sections[i].sectionTypeId`, not
top-level (an initial top-level read returned all-`None`; corrected before
census).

**Grand total across all 3 files: 162 records, 14,087 sections scanned.**

| sectionTypeId | count | in KNOWN_IDS? |
|---:|---:|:---|
| 1 | 346 | yes |
| 2 | 82 | yes |
| 3 | 86 | yes |
| 4 | 10,931 | yes |
| 7 | 55 | yes |
| 8 | 307 | yes |
| 9 | 164 | yes |
| 10 | 232 | yes |
| 13 | 10 | yes |
| 14 | 83 | yes |
| 15 | 836 | yes |
| 16 | 931 | yes |
| 17 | 7 | yes |
| 18 | 10 | yes |
| 19 | 6 | yes |
| 20 | 1 | yes |
| **5, 11, 12** | **0** | — TARGET, not found |
| any id outside {1-4,6-10,13-20} | **0** | — none found |

Focused re-check isolating just the three named tax/tariff law_codes
(ป0008-1D-0001, พ0007-1C-0003, ภ0007-1B-0001) across all their timeline
versions: **same result, zero hits for 5/11/12 or any out-of-range id.**

## Hits: none — but a decisive adjacent finding

No occurrence of sectionTypeId 5, 11, or 12 anywhere in the 14,087 sections
scanned. However, the hunt surfaced *why* a dedicated TABLE type may not
exist at all in this corpus:

In **พระราชกำหนดพิกัดอัตราศุลกากร พ.ศ. 2530** (the law that literally *is*
a customs tariff schedule by HS code — the strongest possible table
candidate in the whole corpus), the attachment sections
(`sectionTypeId=16`, "เอกสารแนบท้าย") contain:

> `[เอกสารแนบท้าย] ๑. ภาค ๑ หลักเกณฑ์การตีความพิกัดอัตราศุลกากร ๒. ภาค ๒ พิกัดอัตราอากรขาเข้า ๓. ภาค ๓ พิกัดอัตราอากรขาออก ๔. ภาค ๔ ของที่ได้รับยกเว้นอากร ... (ดูข้อมูลจากภาพกฎหมาย)`

Translation: "[Attached document] ... Import tariff schedule ... Export
tariff schedule ... **(see data from the law image)**."

This "ดูข้อมูลจากภาพกฎหมาย" / "ดูภาพ" (see the law's image) punt appears **16
times**, all confined to this one law (`1987-12.jsonl`), all under
`sectionTypeId=16`. It means the OCS/Krisdika source itself never
transcribed the tariff tables into extractable text — it points readers to a
scanned image of the law instead. The corpus's `content` field is text-only;
there is no evidence anywhere in the schema of a table-structured
(rows/cols) content type being populated. The word "ตาราง" (table) itself
appears 105 times across the local corpus (32 files total, prior + new), but
as prose references to "the table below" / statutory cross-references, not
as a distinct machine-parseable table block.

**Interpretation:** sectionTypeId 5/11/12 may simply never have been used by
the source system for this document class, or — if they exist — they live
in law categories/eras not yet sampled (this corpus spans multiple
digitization eras; older or differently-sourced laws could use different
type ranges). This hunt covers 3 files / 162 records / 14,087 sections out
of a corpus of 994 file entries — a real but partial slice. **Absence here
is not proof of absence corpus-wide** (Berkson) — logged as "not found,"
not "does not exist."

## Pipeline verdict on the closest table-adjacent record

Ran `normalize_record` (`build_docs`) + `qa_check` from the repo's
`src/matra` (with the raw corpus under `~/.aice/legalrag/`; no src/ or
tests/ modified) against the largest Customs Tariff record
(timeline `พ0007-1C-0003-28`, 146 sections, containing the image-punt
`sectionTypeId=16` attachment refs — the closest thing to a "table hit" in
this hunt):

```
normalize_record: OK, no crash — 15 docs, 0 flags
qa_check: hard_fail = False
  rows_in_vs_out        = (123, 123, True)   # balanced
  titles_in_vs_docs      = (15, 15, True)
  char_roundtrip_delta_pct = 0.0
  quarantine              = {rows_in: 0, rows_out: 0, by_type: {}, ...}
```

`sectionTypeId=16` is treated as expected (alongside type 1) per the
pipeline's own `qa.py` docstring — `BODY_TYPES ∪ {1, 16}` — so it correctly
does **not** land in quarantine. Ledger balanced, no hard fail.

**Sanity check that quarantine actually fires when it should:** found a
different record (`ล0002-1B-0001-01`, พ.ร.บ.ล้อเลื่อน ฉะบับที่ 2, 1939-04)
containing `sectionTypeId=18` (outside `BODY_TYPES ∪ {1,16}`). Ran the same
pipeline:

```
hard_fail = False
quarantine = {rows_in: 6, rows_out: 6, by_type: {'18': 6}, chars_in: 1637, chars_out: 1637}
rows_in_vs_out = (14, 14, True)
```

Quarantine correctly captured all 6 rows of the anomalous type, ledger
balanced (`rows_in == rows_out`, `chars_in == chars_out`), no crash, no hard
fail. This confirms the quarantine lane is live and correctly non-destructive
for out-of-range typeIds in general — giving confidence that **if**
5/11/12 are encountered elsewhere in the corpus, the pipeline will quarantine
them safely rather than crash or silently drop data.

## Next-hunt suggestions

1. **Widen the law sample**, not just tax/tariff — 5/11/12 may belong to a
   different document class entirely (e.g. royal decrees with schedules,
   ministerial regulations with fee tables, or a different digitization
   batch/era). Grep `tree_main.json` for other "บัญชี"/"อัตรา" law titles
   beyond the 3 checked here.
2. **Check pre-1932 or post-2020 eras** — different digitization vintages
   sometimes used different typeId schemes; this hunt only touched
   1939/1987/2017.
3. **If a genuine table-bearing record is ever found**, verify whether its
   `content` field actually contains delimited/tabular text or is another
   "ดูภาพ" image-punt — the corpus may render *no* law's tables as structured
   text, making 5/11/12 permanently vacant by design rather than by sampling
   luck.
4. Grep the *entire* local `tree_main.json` index (994 entries) for
   candidate paths whose Thai title metadata (if any is embedded) suggests
   fee schedules, rate tables, or "บัญชีท้าย" — 220 + 162 = 382 records
   sampled so far, corpus likely has tens of thousands of individual law
   records total across 994 files.
