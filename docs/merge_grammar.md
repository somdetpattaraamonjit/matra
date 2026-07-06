# Merge Grammar Survey — Thai Amendment-Directive Language

Task 4'.1 deliverable 1. Generated from `docs/survey_scan.py` output
(`/tmp/matra_survey_output.json`, reproducible by re-running the script).
Every row cited below is locatable by `(source, doc_idx, row_i, sectionNo)`
in that JSON. Thai legal text quoted verbatim, untranslated; structural
commentary in English.

Scope scanned:
- **-63 record** (`ป0006-1D-0003-63`, 1,031 sections, 34 docs): all 32
  amendment-act docs (doc_idx 2..33), the full row set (not the tree-built
  `normalize_record` output — recital/remark rows the tree stage demotes
  are exactly where directive language would live, so the row-level
  `matra.splitter.split_record` API was used instead).
- **sampling_dl corpus**: 29 files on disk (the brief's "220 groups" does
  not match what is on disk — logged as Ambiguity #1 below; every file was
  scanned, one JSON record per line, 680 non-code docs total across all
  records).

## 1. Pattern inventory table

Verb-pattern regexes were deliberately loose (see `DIRECTIVE_VERB_PATTERNS`
in `survey_scan.py`) so every candidate hit could be manually classified
against its row context, rather than trusting a narrow regex to already
know the true formula. Classification below is done by READING the hits,
not by regex family name alone — several regex families turned out to be
false-positive magnets on ordinary legal prose and are marked NOISE.

| # | Formula family | Regex-able skeleton | Freq in -63 (docs idx≥2) | Freq in sampling_dl | Verbatim example (locator) |
|---|---|---|---|---|---|
| 1 | **ADD** (insert new มาตรา/วรรค) | `ให้เพิ่มความต่อไปนี้เป็น (มาตรา X [ทวิ/ตรี/...] \| วรรค N ของมาตรา X) แห่ง<law>` | **0** | **55** (`ADD_khwaam` family; `ADD_generic` mostly overlaps, 67 raw hits before de-dup) | `มาตรา ๓ ให้เพิ่มความต่อไปนี้เป็นมาตรา ๙ ทวิ ของพระราชบัญญัติว่าด้วยวินัยตำรวจ พุทธศักราช ๒๔๗๗` — `sampling_dl/1950-11.jsonl:3`, matra row no=3 |
| 2 | **REPLACE** (repeal-and-substitute one มาตรา) | `ให้ยกเลิกความใน (มาตรา X \| มาตรา X (N)) แห่ง<law> [ซึ่งได้แก้ไขเพิ่มเติมโดย...] และให้ใช้ความต่อไปนี้แทน "<new text>"` | **0** | **141** (`REPLACE_yoklerk_khwaam_taen`) | `มาตรา ๕ ให้ยกเลิกความในมาตรา ๑๖ แห่งพระราชบัญญัติว่าด้วยวินัยตำรวจ พุทธศักราช ๒๔๗๗ ... และให้ใช้ความต่อไปนี้แทน "มาตรา ๑๖ ถ้าเป็นความผิด..."` — `sampling_dl/1950-11.jsonl:3`, matra row no=5 |
| 3 | **REPEAL** (remove, no replacement) | `ให้ยกเลิก (มาตรา X \| พระราชบัญญัติ<name> \| ประกาศ...\| บัญชี...)` — target can be a whole prior act, a มาตรา, or a schedule, not only structural containers | **0** | **86** (`REPEAL_yoklerk`) | `มาตรา ๓ ให้ยกเลิกพระราชบัญญัติการทะเบียนคนต่างด้าว พุทธศักราช ๒๔๗๙ ...` — `sampling_dl/1950-11.jsonl:0`, matra row no=3. Structural-level repeal example not found in the scanned corpus (see edge list). |
| 4 | AMEND (generic "แก้ไขเพิ่มเติม") | `ให้แก้ไขเพิ่มเติม...` | 0 (title boilerplate excluded by regex) | present but **NOISE**: nearly always the enacting-act's own TITLE verb ("พระราชบัญญัติแก้ไขเพิ่มเติมประมวลกฎหมาย...") re-quoted inside a remark, not a fresh directive. Not counted as a distinct family. | — |
| 5 | EDIT_ตัด / EDIT_แทรก / EDIT_เปลี่ยน / EDIT_ปรับ (candidate families per task instructions to expand beyond the seed verb list) | `ให้ตัด...` / `ให้แทรก...` / `ให้เปลี่ยน...` / `ให้ปรับ...` | 0 | ตัด: 12, แทรก: 0, เปลี่ยน: 147, ปรับ: 25 — **ALL NOISE on manual read**: every hit is substantive legal-content prose (e.g. "ให้ตัดรานกิ่งหรือโค่นต้นไม้" = a tree-trimming duty in a railway act; "ให้ปรับ" = "shall be fined") that happens to start with ให้ + one of these verbs, not a merge-engine directive. Zero genuine insert/replace/repeal hits found under these verbs in either corpus. | — |
| 6 | `GIVEN_near_anchor` (broad-net probe: "ให้..." within 20 chars of มาตรา/ลักษณะ/หมวด/วรรค) | `ให้[ก-ู]{0,20}(?:มาตรา\|ลักษณะ\|หมวด\|วรรค)` | 7 (all -63 hits — see §"Absence" below, all cross-reference prose, zero are merge directives) | 103 | -63 example (NOISE): `ให้นำบทบัญญัติมาตรา ๓๐ มาใช้บังคับโดยอนุโลม` — rec63 doc_idx 17, row_i 856 (a cross-reference clause "apply มาตรา 30 by analogy", not an insertion). |
| 7 | `REPLACE_taen_generic` (naive "แทน" substring probe) | `แทน` anywhere in row | n/a, excluded from -63 headline count (matched only as part of hit #2 above and prose like "ให้ส่งข้าวแทนเงิน") | 601 raw hits, **overwhelming NOISE** — "แทน" is common Thai for "instead/in place of/representative" in ordinary prose (ผู้แทน = representative, ใช้...แทน = use X instead) unrelated to the merge grammar | `ปนั้นให้ส่งข้าวแทนเงินแต่คิดราคาต่ำกว่า...` — `sampling_dl/1877-05.jsonl:0`, recital row (a 19th-century usury statute, "give rice instead of money") |

**Headline counts (genuine merge-directive sentences only, after manual
declassification of noise families):**
- **-63 amendment acts (docs idx 2..33): 0 genuine directive sentences of ANY family.** The 7 raw regex hits in -63 (families `GIVEN_near_anchor`×5, `EDIT_เปลี่ยน`×1, `REPLACE_taen_generic`×1) were individually read; all 7 are ordinary legal cross-reference or substantive prose, none is an insert/replace/repeal directive. See §"Grammar absence in -63" below.
- **sampling_dl corpus: at least 196 genuine directive sentences** (55 ADD + 141 REPLACE; REPEAL's 86 hits include both มาตรา-level and whole-instrument-level targets, all genuine repeal directives even though they don't match the ADD/REPLACE anchor-payload shape — so total genuine directives across all three real families = 55 + 141 + 86 = **282**). This supersedes the prior seed-scan's "16 hits / 9 files" — the expanded, manually-verified count is far higher once the full corpus and full verb list are scanned.

## 2. Payload anatomy

Evidence rows (sampling_dl, since -63 has none to inspect):

- **Same-row payload (REPLACE family)**: the new text is embedded in the
  SAME row as the directive verb, opening with a Thai quotation mark `"`
  immediately after `...ต่อไปนี้แทน`, e.g. row `sampling_dl/1950-11.jsonl:3`
  matra no=5: `...และให้ใช้ความต่อไปนี้แทน "มาตรา ๑๖ ถ้าเป็นความผิด..."` —
  the quoted payload re-states the full มาตรา number and text inline, in
  one `sectionTypeId 4` (matra) row.
- **Same-row payload (ADD family)**: also single-row; the directive clause
  (`ให้เพิ่มความต่อไปนี้เป็นมาตรา X ทวิ แห่ง<law>`) and the new text are
  one continuous `matra`-typed row, e.g.
  `sampling_dl/1973-06.jsonl:2` matra no=5: `มาตรา ๕ ให้เพิ่มความต่อไปนี้เป็นมาตรา ๑๒ ทวิ แห่งพระราชบัญญัติรับราชการทหาร พ.ศ. ๒๔๙๗ "มาตรา ...`.
  A single ADD directive can target more than one new มาตรา at once —
  `sampling_dl/1973-06.jsonl:4` matra no=3: `ให้เพิ่มความต่อไปนี้เป็นมาตรา ๖ ทวิ และมาตรา ๖ ตรี แห่ง...` (two new มาตรา,
  one directive sentence).
- **No separate "payload row" type exists** — `sectionTypeId` for both the
  directive clause and its quoted new text is always 4 (`matra`), same as
  ordinary substantive มาตรา rows. There is no dedicated payload/quote
  sectionTypeId in this schema; the payload is textually embedded, not
  structurally separated.
- **-63's actual payload anatomy (no directive present)**: in every one of
  the 32 -63 amendment acts, the "payload" (new มาตรา text, e.g.
  `มาตรา ๓๓๕ ทวิ ผู้ใดลักทรัพย์...`) appears as an ordinary standalone
  `matra` row with NO preceding directive-verb row at all — see §"Grammar
  absence in -63".

## 3. Target-anchor anatomy

The addressing scheme the merge engine must resolve, with row evidence:

| Anchor level | Expression pattern | Evidence |
|---|---|---|
| มาตรา (section), simple insert | `เป็นมาตรา ๙ ทวิ ของ/แห่ง<law>` — Thai suffix (ทวิ/ตรี/จัตวา/เบญจ/ฉ/สัตต/อัฏฐ/นว/ทศ) marks "inserted after existing มาตรา N, Kth insertion" | `sampling_dl/1950-11.jsonl:3` |
| มาตรา, slash-numbered insert (observed only in -63's headless payloads, never with an explicit directive sentence in the scanned data) | `มาตรา ๑๓๕/๑` etc. — slash suffix marks "inserted after มาตรา 135, 1st of a new block" | rec63 doc19, row_i 878 |
| วรรค (paragraph) within an existing มาตรา | `เป็นวรรคสามของมาตรา ๒๙ แห่ง<law>` | `sampling_dl/1989-09.jsonl:1` matra no=9: `ให้เพิ่มความต่อไปนี้เป็นวรรคสามของมาตรา ๒๙ แห่งพระราชบัญญัติการปฏิรูปที่ดินเพื่อเกษตรกรรม...` |
| ลักษณะ (title-level container), slash-numbered insert | `ลักษณะ ๑/๑ <heading>` — bare heading row, no directive sentence anchoring it in -63; anchor is purely POSITIONAL (row order: sits between the existing ลักษณะ ๑ heading row and the existing ลักษณะ ๒ heading row in the base code doc) | rec63 doc19, row_i 877, heading-only; base-code anchor confirmed by reading doc1's ลักษณะ sequence: ...ลักษณะ๑(row266)‑ลักษณะ๒(row311)... — ๑/๑ falls between them by number |
| หมวด (chapter-level container), plain sequential insert | `หมวด ๔ <heading>` / `หมวด ๕ <heading>` — again bare heading rows, anchor is POSITIONAL: extends the existing หมวด ๑-๓ sequence under ลักษณะ ๗ (การปลอมและการแปลง) in the base code doc | rec63 doc20 row_i 894 (หมวด ๔), doc21 row_i 909 (หมวด ๕); base code's ลักษณะ๗ already has หมวด๑(row468)/๒(row483)/๓(row501) |
| ลักษณะ, plain sequential insert | `ลักษณะ ๑๓ <heading>` — bare heading row, anchor is POSITIONAL: extends ภาค ๒'s existing ลักษณะ sequence (which the base code doc runs ๑..๑๑) to ๑๓ — see digit-fidelity section for why it's ๑๓ not ๑๒ | rec63 doc25 row_i 943 |

**Key finding**: sampling_dl's genuine directive sentences ALWAYS state
their anchor explicitly in natural language (`เป็นมาตรา X แห่ง<law>`).
-63's amendment acts NEVER state an anchor in natural language for any of
the 4 golden targets (or, per the systematic scan below, for ANY of its 32
acts) — the anchor is recoverable ONLY by: (a) the new heading/มาตรา's own
number (ทวิ/ตรี suffix or slash-numbering self-declares its insertion
point), and (b) row-adjacency to the corresponding position in the base
code doc's own structure sequence. **This means the merge engine needs TWO
anchor-resolution strategies**: parse-the-sentence (sampling_dl-style) and
infer-from-number-and-position (all of -63's golden-target style) — this
is reported as evidence, not prescribed as a design.

## 4. Grammar absence in -63 (systematic, all 32 amendment acts checked)

**Finding (verified programmatically for all 32 acts, not just the golden
targets): every single one of -63's 32 amendment-act docs lacks a natural-
language merge-directive sentence.** The universal shape is: มาตรา ๒
(boilerplate effective-date clause) → optional มาตรา ๕/๑๐/๑๑-ish
(boilerplate "รัฐมนตรีรักษาการ" / transitional clause, present in only a
few acts) → remark rows (หมายเหตุ, the legislative-intent explanation,
NOT a directive) → **directly** the new/replacement มาตรา payload row(s)
or a heading row (ลักษณะ/หมวด typeId 7/8) immediately followed by payload
มาตรา rows. There is no "ให้เพิ่มความ.../ให้ยกเลิกความ...และให้ใช้ความ
ต่อไปนี้แทน" sentence anywhere in this record's 32 amendment acts.

Systematic evidence — มาตรา-number sequence per act (full list in
`docs/merge_answer_key.md` §Total directive counts; every act's sequence
starts `['2', ...]` then jumps straight to its actual target มาตรา,
skipping the boilerplate 3-9 directive-carrying range entirely or almost
entirely):

- **32/32 acts** open `มาตรา ๒` (effective date) then jump directly to
  their substantive target(s) with **zero** intervening directive-bearing
  มาตรา rows in the 3-9 boilerplate range, EXCEPT:
  - **doc17** (ฉบับที่ ๑๔ พ.ศ. ๒๕๔๐): sequence is `['2','30/1','30/2','30/3',...]` —
    no directive gap in the classic sense since ๓๐/๑ etc. are themselves
    the payload (slash-numbered insertions right after ๒).
  - **doc29** (ฉบับที่ ๒๕ พ.ศ. ๒๕๕๙): sequence `['2','10','11']` — a TRUE
    gap, มาตรา ๓-๙ missing (7 integers), yet the remark text explicitly
    discusses amending มาตรา ๓๐ of the code — that amendment's actual
    payload row is missing from this record entirely (not even present as
    a headless payload row). **This is the single unresolved case in this
    survey — flagged as Ambiguity #4 below.**
  - **doc31** (ฉบับที่ ๒๗ พ.ศ. ๒๕๖๒): sequence `['2','305']` — this is NOT
    a boilerplate-range gap (there was never a มาตรา ๓..๓๐๔ intended here);
    the act's one substantive target is simply a high-numbered มาตรา
    (๓๐๕), so the large "missing" range my gap-detector reports is a
    **false-positive artifact of the detector's own heuristic** (it flags
    any integer jump, not specifically the 3-9 boilerplate range) — logged
    as Ambiguity #5, not a real finding.
- **Golden-target acts specifically** (doc19 ก่อการร้าย, doc20
  บัตรอิเล็กทรอนิกส์, doc21 หนังสือเดินทาง, doc25 ศพ): doc19 has the
  clean textbook gap (มาตรา ๓,๔ missing, verified above); doc20/21/25 have
  NO gap at all in the 2..N sense — they simply never had a มาตรา ๓-N in
  the first place (their sequence goes straight `['2', <first payload>...]`
  with nothing in between, not even a stub).
- This was checked to be a genuine raw-source characteristic, not a
  `clean()`/pipeline artifact, by both `split_record` row inspection (which
  bypasses the tree-building stage entirely) AND a direct raw
  `rec["sections"]` grep independent of `TYPE_MAP` (see
  `raw_grep_all_sections` in `survey_scan.py`) — no hidden unmapped
  sectionTypeId is smuggling a directive sentence past the type map either.

**Interpretation** (reported as evidence per the brief's tension framing,
not as an engine design choice): the -63 record is a KRISDIKA-style
*consolidated code with headless amendment fragments* — it retains only the
`มาตรา ๒` procedural boilerplate and the final payload text of each
amendment, not the amending act's own directive/instruction language. The
sampling_dl corpus (which includes non-code standalone acts) DOES retain
full directive sentences. This suggests the merge engine's real workload
divides into two regimes: (1) acts/records that preserve directive
sentences → sentence-parse strategy; (2) KRISDIKA-consolidated records
with headless payloads (like -63) → positional/numeric-adjacency strategy
using the payload's own self-declared number (ทวิ/ตรี suffix or slash) plus
its row-order position relative to the base code's existing structure.

## 5. Edge / ambiguity list

1. **sampling_dl file count mismatch**: brief says "220 groups"; disk has
   **29 files**. Not re-derived or forced to match — logged as a ground-
   truth discrepancy per the environment brief's own instruction to trust
   what's on disk.
2. **REPEAL family, structural-level target**: the brief's expected REPEAL
   skeleton includes `ให้ยกเลิก (มาตรา X / หมวด X / ลักษณะ X ...) แห่ง<law>`
   (structural-level repeal). All 86 REPEAL hits found in sampling_dl target
   either a specific มาตรา or an entire prior act/ประกาศ/บัญชี — **no
   example of a หมวด- or ลักษณะ-level repeal was found** in either corpus.
   Cannot confirm or deny this sub-family exists in the wild from this
   survey; flagged as unverified rather than assumed absent.
3. **"Renumber" / "insert-before" formulas** (brief asks to record these if
   found, even rare): none found in either corpus under any scanned verb.
   No evidence either way beyond "not observed in this sample."
4. **doc29 (ฉบับที่ ๒๕ พ.ศ. ๒๕๕๙) missing มาตรา ๓-๙**: remark text
   explicitly references amending มาตรา ๓๐ of the code
   ("บทบัญญัติมาตรา ๓๐ แห่งประมวลกฎหมายอาญา ซึ่งแก้ไขเพิ่มเติมโดย
   พระราชบัญญัตินี้..." — rec63 doc29 row_i 982), meaning this act DID
   amend มาตรา ๓๐, but no row anywhere in this act (checked all 10 rows)
   carries that amendment's directive OR payload text. This is a genuine
   unresolved data gap distinct from the golden-targets' pattern (those
   never claim to carry a directive at all; this one's own remark implies
   one should exist and it's simply absent from the raw record). Flagged,
   not guessed at.
5. **Gap-detector false positive on doc31**: the mechanical "missing
   integers between prev and cur matra number" heuristic in
   `find_matra_gaps()` flags doc31's `['2','305']` sequence as "271 missing
   มาตรา," which is a detector artifact (there was never an intent to have
   มาตรา 3-304 in this act) rather than a real finding. Documented so a
   future reader of the raw JSON output doesn't mistake it for a genuine
   gap; the correct read is in §4 above ("boilerplate-range gap" ≠ "any
   large numeric jump").
6. **`GIVEN_near_anchor` and verb-adjacent regex families are structurally
   noisy** on Thai legal prose generally (ให้ is one of the most common
   words in the language, meaning "let/shall/give/for"). All positive
   hits under EDIT_ตัด/แทรก/เปลี่ยน/ปรับ, `GIVEN_near_anchor`, and
   `REPLACE_taen_generic` were manually read (not just counted) precisely
   because of this; every single one turned out to be substantive-content
   prose, not merge directives. This is reported as a finding in itself —
   these five families contribute **zero** genuine directives across both
   corpora — rather than silently dropped from the pattern table.
