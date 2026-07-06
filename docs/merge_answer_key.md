# Merge Answer Key — 4 Golden Targets + Digit-Fidelity Probe

Task 4'.1 deliverables 2 and 3. Generated from `docs/survey_scan.py` output
(`/tmp/matra_survey_output.json`); locators given as
`(doc_idx, row_i, sectionNo/sectionId)` against the -63 record
(`ป0006-1D-0003-63`, 1,031 sections, 34 docs) unless stated otherwise.

## Deliverable 2 — the 4 golden merge targets

All 4 targets located, all 4 มาตรา ranges from the brief **match the raw
data exactly** — no discrepancy on the ranges themselves. What does NOT
match the brief's implicit assumption: **none of the 4 targets have a
directive sentence** (see verdict column). This is reported explicitly per
target below, not folded into a single caveat.

| Target | Source amendment act | Introducing act doc_idx | Directive sentence? | Anchor interpretation | Payload rows | Payload char-length | มาตรา range (matches brief) |
|---|---|---|---|---|---|---|---|
| ลักษณะ ๑/๑ ก่อการร้าย | พระราชบัญญัติแก้ไขเพิ่มเติมประมวลกฎหมายอาญา(ฉบับที่ ๑๖) พ.ศ. ๒๕๔๖ | 19 | **ABSENT.** No `ให้เพิ่ม.../ให้ยกเลิก...` sentence anywhere in this act's 16 rows. มาตรา ๓,๔ (the boilerplate range that would carry it) are missing from the raw section list — confirmed by both `split_record` row inspection and raw `rec["sections"]` grep. | POSITIONAL ONLY: heading row `ลักษณะ ๑/๑ ความผิดเกี่ยวกับการก่อการร้าย` (row_i 877, sectionNo "1/1") is a bare typeId-7 row with no anchor language; its own slash-number ("1/1") self-declares "insert between ลักษณะ ๑ and ลักษณะ ๒" in ภาค ๒ of the base code doc — confirmed by reading doc1's ลักษณะ sequence (ลักษณะ๑ มั่นคง @row266, ลักษณะ๒ การปกครอง @row311; 1/1 falls between them by number, not by any stated instruction) | 8 rows (typeId 4, มาตรา ๑๓๕/๑–๑๓๕/๔, some มาตรา span >1 raw row) | 1,924 chars | ๑๓๕/๑–๑๓๕/๔ — **matches brief exactly** |
| หมวดความผิดเกี่ยวกับบัตรอิเล็กทรอนิกส์ | พระราชกำหนดแก้ไขเพิ่มเติมประมวลกฎหมายอาญา พ.ศ. ๒๕๔๖ | 20 | **ABSENT.** No directive sentence in this act's 17 rows; zero directive-verb regex hits of any family. | POSITIONAL ONLY: heading row `หมวด ๔ ความผิดเกี่ยวกับบัตรอิเล็กทรอนิกส์` (row_i 894, sectionNo "4") is a bare typeId-8 row; extends the existing หมวด ๑-๓ sequence under ลักษณะ ๗ (การปลอมและการแปลง) in the base code doc (หมวด๑ เงินตรา @row468, หมวด๒ ดวงตรา @row483, หมวด๓ เอกสาร @row501) | 9 rows | 2,109 chars | ๒๖๙/๑–๒๖๙/๗ — **matches brief exactly** |
| หมวดความผิดเกี่ยวกับหนังสือเดินทาง | พระราชบัญญัติแก้ไขเพิ่มเติมประมวลกฎหมายอาญา (ฉบับที่ ๑๗) พ.ศ. ๒๕๔๗ | 21 | **ABSENT.** No directive sentence in this act's 15 rows; zero directive-verb regex hits. | POSITIONAL ONLY: heading row `หมวด ๕ ความผิดเกี่ยวกับหนังสือเดินทาง` (row_i 909, sectionNo "5") — continues the same หมวด ๑-๔ sequence under ลักษณะ ๗ to หมวด ๕ (สืบเนื่องจากหมวด ๔ บัตรอิเล็กทรอนิกส์ ที่เพิ่งเพิ่มโดยฉบับก่อนหน้า) | 10 rows | 2,409 chars | ๒๖๙/๘–๒๖๙/๑๕ — **matches brief exactly** |
| ลักษณะ ๑๓ ความผิดเกี่ยวกับศพ | พระราชบัญญัติแก้ไขเพิ่มเติมประมวลกฎหมายอาญา (ฉบับที่ ๒๑) พ.ศ. ๒๕๕๑ | 25 | **ABSENT.** No directive sentence in this act's 13 rows; zero directive-verb regex hits. | POSITIONAL ONLY: heading row `ลักษณะ ๑๓ ความผิดเกี่ยวกับศพ` (row_i 943, sectionNo "13") — extends ภาค ๒'s ลักษณะ sequence past the base code's own ลักษณะ ๑๑ (เสรีภาพและชื่อเสียง). **Note**: the base code's own structural rows never show a ลักษณะ ๑๒ (see digit-fidelity probe below — ทรัพย์ is mis-labeled "ลักษณะ ๑" in its typeId-7 heading row, though the record's own discarded source_toc calls it ลักษณะ ๑๒) — so ลักษณะ ๑๓ ศพ is numerically consistent with ทรัพย์ correctly being ๑๒, not with what the structural row literally displays. | 4 rows | 649 chars | ๓๖๖/๑–๓๖๖/๔ — **matches brief exactly** |

**Verdict on the brief's TOC-position questions ("verify from directive
text")**: since no target has directive text, all 4 anchor interpretations
above were derived from **row-position + self-declared number** (slash
suffix or plain increment) against the base code doc's own structure
sequence, not from any natural-language instruction. This is reported
plainly rather than reverse-engineering a directive sentence that does not
exist in the data.

## Total directive counts

**In -63's 32 amendment acts (docs idx 2..33): 0 genuine merge-directive
sentences of any family (ADD/REPLACE/REPEAL).** 7 raw regex hits were
produced by the broad-net verb patterns (`GIVEN_near_anchor` ×5,
`EDIT_เปลี่ยน` ×1, `REPLACE_taen_generic` ×1); every one was individually
read and confirmed to be ordinary legal cross-reference or substantive
prose (e.g. "ให้นำบทบัญญัติมาตรา ๓๐ มาใช้บังคับโดยอนุโลม" = "apply มาตรา
30 by analogy", not an insertion instruction). Breakdown by target level
is **not applicable** for -63 since there are zero genuine directives to
break down — the "targeting" that does happen is 100% structural/positional
(via heading rows) or purely payload-embedded (headless มาตรา with a
self-declared ทวิ/ตรี/slash number), never a natural-language directive
sentence at any level (ลักษณะ/หมวด/มาตรา/วรรค).

This absence was checked systematically across **all 32** -63 amendment
acts, not just the 4 golden targets — see `docs/merge_grammar.md`
§"Grammar absence in -63" for the full per-act มาตรา-sequence table. Every
act's sequence opens with the มาตรา ๒ boilerplate then jumps straight to
substantive payload, with the sole partial exception of doc29 (ฉบับที่
๒๕ พ.ศ. ๒๕๕๙), which has a genuinely unresolved missing-payload case
(see Ambiguity #4 in `merge_grammar.md`) unrelated to any of the 4 golden
targets.

**In the sampling_dl corpus (29 files, 680 non-code docs scanned): at
least 282 genuine directive sentences** — ADD: 55, REPLACE: 141, REPEAL:
86. Breakdown by target level, from manual reading of the classified hits
(not from regex family name):
- **มาตรา-level** (by far the dominant level): the large majority of ADD
  and REPLACE hits target a single มาตรา (with ทวิ/ตรี/slash suffix for
  ADD, plain มาตรา N for REPLACE). Exact counts:
  - ADD targeting a new มาตรา: 55/55 examples read all target มาตรา-level
    insertions (no ลักษณะ/หมวด-level ADD directive was found in either
    corpus — see Ambiguity #3).
  - REPLACE: 141/141 examples read all target a single existing มาตรา
    (`ให้ยกเลิกความในมาตรา X แห่ง...และให้ใช้ความต่อไปนี้แทน`); several
    target a specific sub-item within a มาตรา (e.g. `มาตรา ๒ (๑๗)`).
  - REPEAL: 86 hits split between มาตรา-level repeals (e.g.
    `ให้ยกเลิกความในมาตราดังกล่าว`) and whole-instrument-level repeals
    (an entire prior act/ประกาศ/บัญชี, e.g. `ให้ยกเลิกพระราชบัญญัติการ
    ทะเบียนคนต่างด้าว พุทธศักราช ๒๔๗๙`) — no ลักษณะ/หมวด-level repeal
    example found (see Ambiguity #2 in merge_grammar.md).
- **วรรค-level**: at least 1 confirmed example within the 55 ADD hits
  (`ให้เพิ่มความต่อไปนี้เป็นวรรคสามของมาตรา ๒๙ แห่งพระราชบัญญัติการปฏิรูป
  ที่ดินเพื่อเกษตรกรรม...` — `sampling_dl/1989-09.jsonl:1`).
- **ลักษณะ/หมวด (structure)-level**: **0 confirmed examples** of a
  directive SENTENCE targeting this level in either corpus. The only
  ลักษณะ/หมวด-level insertions observed anywhere (the -63 golden targets)
  arrive via bare heading rows with no directive language at all, not via
  a structure-level directive sentence — genuinely different mechanism
  from the มาตรา/วรรค-level ADD/REPLACE sentences.

## Deliverable 3 — Digit-fidelity probe

**Falsification target**: "ลักษณะ ๑ ที่ควรเป็น ๑๒" (claim: ลักษณะ ๑
appears somewhere it should say ลักษณะ ๑๒).

**Method**: enumerate ALL ลักษณะ heading rows (sectionTypeId 7) in the -63
record, in doc-then-row order, across BOTH the code doc (doc1) AND every
amendment act that injects a new ลักษณะ (per the finding that ก่อการร้าย
ลักษณะ ๑/๑ and ศพ ลักษณะ ๑๓ are both amendment-act-injected, not living in
the base code doc).

### Evidence rows — every ลักษณะ (typeId 7) heading row in the -63 record

| doc_idx | row_i | sectionNo | Verbatim heading | ภาค context |
|---|---|---|---|---|
| 1 (code) | 26 | ๑ | ลักษณะ ๑ บทบัญญัติที่ใช้แก่ความผิดทั่วไป | ภาค ๑ (บทบัญญัติทั่วไป, starts row 25) |
| 1 (code) | 259 | ๒ | ลักษณะ ๒ บทบัญญัติที่ใช้แก่ความผิดลหุโทษ | ภาค ๑ |
| 1 (code) | 266 | ๑ | ลักษณะ ๑ ความผิดเกี่ยวกับความมั่นคงแห่งราชอาณาจักร | ภาค ๒ (ความผิด, starts row 265 — restarts ลักษณะ numbering) |
| 1 (code) | 311 | ๒ | ลักษณะ ๒ ความผิดเกี่ยวกับการปกครอง | ภาค ๒ |
| 1 (code) | 361 | ๓ | ลักษณะ ๓ ความผิดเกี่ยวกับการยุติธรรม | ภาค ๒ |
| 1 (code) | 417 | ๔ | ลักษณะ ๔ ความผิดเกี่ยวกับศาสนา | ภาค ๒ |
| 1 (code) | 421 | ๕ | ลักษณะ ๕ ความผิดเกี่ยวกับความสงบสุขของประชาชน | ภาค ๒ |
| 1 (code) | 436 | ๖ | ลักษณะ ๖ ความผิดเกี่ยวกับการก่อให้เกิดภยันตรายต่อประชาชน | ภาค ๒ |
| 1 (code) | 467 | ๗ | ลักษณะ ๗ ความผิดเกี่ยวกับการปลอมและการแปลง | ภาค ๒ |
| 1 (code) | 512 | ๘ | ลักษณะ ๘ ความผิดเกี่ยวกับการค้า | ภาค ๒ |
| 1 (code) | 522 | ๙ | ลักษณะ ๙ ความผิดเกี่ยวกับเพศ | ภาค ๒ |
| 1 (code) | 568 | ๑๐ | ลักษณะ ๑๐ ความผิดเกี่ยวกับชีวิตและร่างกาย | ภาค ๒ |
| 1 (code) | 600 | ๑๑ | ลักษณะ ๑๑ ความผิดเกี่ยวกับเสรีภาพและชื่อเสียง | ภาค ๒ |
| 1 (code) | 645 | **๑ (⚠ see verdict)** | **ลักษณะ ๑ ความผิดเกี่ยวกับทรัพย์** | ภาค ๒ (still — ภาค ๓ ลหุโทษ does not start until row 713; this row is nested INSIDE ภาค ๒, immediately after ลักษณะ๑๑ at row 600, NOT after any ภาค boundary) |
| 19 (amendment act, ฉบับที่ ๑๖ พ.ศ. ๒๕๔๖) | 877 | ๑/๑ | ลักษณะ ๑/๑ ความผิดเกี่ยวกับการก่อการร้าย | injected between ลักษณะ๑ and ลักษณะ๒ of ภาค ๒ |
| 25 (amendment act, ฉบับที่ ๒๑ พ.ศ. ๒๕๕๑) | 943 | ๑๓ | ลักษณะ ๑๓ ความผิดเกี่ยวกับศพ | injected as the next ลักษณะ after the code's own ลักษณะ๑๑ sequence (and, per this probe's finding, after the correctly-numbered ๑๒ ทรัพย์) |

### Independent cross-check: the record's own (pipeline-discarded) table of contents

`sectionTypeId 16` (`source_toc`) rows are excluded from the tree-building
stage (`structure.py DISCARD = {"source_toc"}`) but are preserved in
`split_record`'s row-level output and in raw `rec["sections"]`. A raw grep
for the literal string `ลักษณะ ๑๒` across ALL 1,031 raw sections of the
-63 record (independent of `TYPE_MAP`, so it would catch the string even
under an unmapped sectionTypeId) returns **exactly 1 hit**:

> `sectionId 6465658`, `sectionTypeId 16` (`source_toc`), `sectionName`
> `"สารบาญประมวลกฎหมายอาญา"` (the code's own table of contents), full
> content (excerpt): `...หมวด ๓ ความผิดฐานหมิ่นประมาท๓๒๖-๓๓๓ **ลักษณะ ๑๒
> ความผิดเกี่ยวกับทรัพย์** หมวด ๑ ความผิดฐานลักทรัพย์และวิ่งราวทรัพย์
> ๓๓๔-๓๓๖...`

This is the SAME section (ทรัพย์, มาตรา ๓๓๔ onward) that the structural
heading row (`sectionId 6466038`, `sectionTypeId 7`, row_i 645) calls
`ลักษณะ ๑`. **The raw source's own table of contents independently and
correctly labels this section "ลักษณะ ๑๒"**, consistent with it being the
12th ลักษณะ of ภาค ๒ (following ลักษณะ ๑๑ เสรีภาพและชื่อเสียง,
immediately preceding it in row order) — while the structural heading row
for the SAME section says "๑" instead.

### Verdict

**DATA DEFECT — confirmed in the raw data itself, not a model/display-side
artifact.**

- The full ordered ลักษณะ sequence, IF the structural row for ทรัพย์ said
  "๑๒" (matching its own source_toc), would read cleanly:
  ภาค๑: ๑, ๒ (own sub-sequence) → ภาค๒: ๑ (มั่นคง), ๑/๑ (ก่อการร้าย,
  amendment-injected), ๒ (การปกครอง), ๓ (ยุติธรรม), ๔ (ศาสนา), ๕
  (ความสงบสุข), ๖ (ภยันตราย), ๗ (ปลอมและแปลง), ๘ (การค้า), ๙ (เพศ), ๑๐
  (ชีวิตและร่างกาย), ๑๑ (เสรีภาพและชื่อเสียง), **๑๒ (ทรัพย์)**, ๑๓ (ศพ,
  amendment-injected) — fully internally consistent, no duplicate, no gap.
- Instead, the structural (typeId 7) row for this section literally reads
  `เลข ๑` (`sectionId 6466038`) — a genuine within-record numbering
  mismatch: this row's own `sectionNo` field disagrees with (a) its own
  row-position (immediately following ลักษณะ๑๑, still inside ภาค๒, not
  after any ภาค boundary) and (b) the SAME record's own source_toc row
  (`sectionId 6465658`), which independently calls the identical section
  "ลักษณะ ๑๒".
- **Exact defect location**: `timeline_code = ป0006-1D-0003-63`,
  `sectionId = 6466038` (global raw index 645), `sectionTypeId = 7`,
  field `sectionNo = "1"` should read `"12"` to be internally consistent
  with the record's own table of contents and its own structural position.
  This is a KRISDIKA source-data numbering error carried through unedited
  by the pipeline (the pipeline does not currently cross-validate
  `sectionNo` against `source_toc` or against ภาค-relative row position —
  it has no reason to, since `source_toc` is intentionally discarded as
  "corrupted upstream" per `structure.py`'s own `DISCARD` comment, which
  turns out to be only PARTLY true: the source_toc content itself is
  internally correct here, even though the pipeline's own design rationale
  assumed it wasn't reliable enough to keep).
- This means the original falsification claim ("ลักษณะ ๑ ที่ควรเป็น ๑๒")
  is **CONFIRMED as a real data defect**, not a prior display/model
  hallucination — with a specific, reproducible row citation.

**Caveat on ภาค ๓ (ลหุโทษ)**: ภาค ๓ (starts row 713) has no ลักษณะ
sub-headings of its own in this record (confirmed: no typeId-7 row
appears between row 713 and the end of doc1 at row 751) — so ภาค ๓ is not
part of this numbering sequence and does not confuse the verdict above.
