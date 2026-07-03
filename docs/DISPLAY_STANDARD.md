# Matra Display Standard v1 (2026-07-02)

Binding requirements for ANY consumer/viewer of Matra data. Born from field feedback (real code-book reference: drthawip.com criminal code; market voice: customer requirement PDF; competitor deka UX benchmark).

## 1. Dual-numeral rendering (REQUIRED)
Data ships Thai numerals verbatim (`number`, headings, text) + Arabic mirrors (`number_arabic`). A conforming viewer MUST offer a **real-time Thai ↔ Arabic toggle** implemented as display-only string transform at render time (`[๐-๙]` ↔ `[0-9]`), never mutating stored data. Reference implementation: `demo/public/index.html` `fmt()`.

## 2. Print-faithful "book" profile (light) + reading profile (dark)
Light mode MUST resemble the printed code volume: paper background, dark serif body, **centered section headings with rule lines** (ภาค/ลักษณะ/หมวด/ส่วน), bold "มาตรา N" inline with first วรรค, subsequent วรรค as indented paragraphs, **editorial footnotes centered under headings** (e.g. "เพิ่มโดยพระราชบัญญัติ… (ฉบับที่ ๑๖) พ.ศ. ๒๕๔๖"). Dark mode = card-per-มาตรา reading app. Toggle is real-time, display-only.

## 3. Product voice (REQUIRED for end-user surfaces)
End-user pages speak law, not vendor: no first-person, no engine self-praise, no pipeline meta-talk. Structural provenance appears as **book-style footnotes** (facts a lawyer wants), data-honesty notes as **editorial remarks** ("หมายเหตุบรรณาธิการ: …"). All engineering proof lives on a **separate internal report page** (`report.html`) that is deleted before customer delivery (one file + one footer line).

## 4. Version timeline (REQUIRED)
Viewer shows all Expressions of the Work sorted by computed `timeline_seq` desc with exactly one "ฉบับล่าสุด" tag from `is_latest_computed` (never the broken source flag).

## 5. Universality (REQUIRED)
A conforming viewer takes ANY Matra flat export + work_expressions wrapper via manifest (`laws.json`) — no per-law code. Main document = doc_id with the most มาตรา rows within declared `main_doc_type`. Proven live with two instrument types: ประมวลกฎหมายอาญา (code, 3-level containers) and พ.ร.ก.พิกัดอัตราศุลกากร 2530 (emergency_decree, containerless, 15 expressions) — same schema, same pipeline, same viewer, zero code change.

## 6. Whole-corpus coverage finding (2026-07-02 full local run — the "see the whole picture first" pass)
Running EVERY group in the local corpus (166 groups, 34 month-files) through the unchanged pipeline: **101 built (3,965 มาตรา), 65 skipped — every skip named + reasoned in `build_report.json` (shipped with the demo)**. Skip anatomy: 3 known-empty source records + 62 **notification-class instruments** (กฎกระทรวงประกาศเขต/เหรียญที่ระลึก/ทางน้ำชลประทาน…) whose body lives in sectionTypeId 18 blocks with NO มาตรา/ข้อ markup at source — data fully conserved in the quarantine lane, but flat-profile v0 has no row type for them. **Standard consequence (v0.3 backlog, schema-additive):** promote typeId-18 bodies to a displayable `content` node so notification instruments render; until then they are listed transparently, never silently dropped. Conservation law held for 101/101 built (hard_fail gate inside the batch script).

## 7. Deka benchmark (phase-2 contract — official source surveyed live 2026-07-02)
`deka.supremecourt.or.th` (ระบบสืบค้นคำพิพากษาศาลฎีกา, Beta 1.0.0) confirmed reachable and sufficient: search by คำค้น/ชื่อกฎหมาย/เลขคำพิพากษา/ช่วงปี with และ-หรือ-ยกเว้น operators, result fields include **ย่อสั้น and ย่อยาว and ฉบับเต็ม** natively — the market-benchmark tiers exist at the official source. Contract: per-มาตรา case links join via `matra_cid`; tiers ย่อสั้น/ย่อยาว/ฉบับเต็ม per case; source = this official system ONLY (deka.in.th / lawlink permanently banned); zero text artifacts (market shows run-together tokens like "มาตรา3").
Per-มาตรา case links MUST offer tiers ย่อสั้น / ย่อยาว / ฉบับเต็ม per case (market bar set by existing deka products), sourced from **official deka.supremecourt.or.th only**, joined via `matra_cid` (not regex over prose), with zero text artifacts (observed in market: run-together tokens like "มาตรา3").
