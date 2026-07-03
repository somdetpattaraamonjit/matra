# Matra Reference Architecture

**The reference pipeline as a publishable standard.** This document describes the stages that turn a raw `ocs-krisdika` record into a conservation-proven, section-level dataset, and fixes the invariants a conforming implementation must uphold. It is the standard's *how*; [`schemas/matra-0.2.json`](../schemas/matra-0.2.json) is its *what*.

Matra's premise: Thai statutory data is publicly available but not usable. Upstream records glue whole timelines into single rows, park amendment content at the end of the file instead of merging it into place, carry a broken `is_latest` flag, and corrupt their own tables of contents. The pipeline pays that cleaning cost once, in the open, and proves — byte for byte — that nothing was invented and nothing was silently dropped.

## Design principle: conservation over cleverness

Every stage is a **pure function** with explicit inputs (record in → structure + report out); the CLI is a thin wrapper, tests import the functions directly. Every transform proves **rows-in = rows-out and character Δ = 0**; a violation `hard_fail`s the build. Nothing is asserted without evidence — `status` / `effective_*` fall back to `"unknown"` rather than guess. Unknown section types are **quarantined and shipped**, never dropped and never crashed on. Re-running any stage on the same input is a no-op. These are not aspirations; they are enforced by the QA gate described in §Conservation gate.

## Pipeline stages

The stages run in order. Each row below states what enters, what leaves, and the conservation guarantee that must hold across it.

| # | Stage | Function | Input → Output | Conservation guarantee |
|---|---|---|---|---|
| 1 | Split | `splitter.split_record` | 1 raw record (flat section rows) → per-document groups + `doc_type` per group | Every source row lands in exactly one group; no row created or destroyed at the boundary. |
| 2 | Structure + Merge | `structure.build_docs_merged` | groups → ภาค/ลักษณะ/หมวด/ส่วน→มาตรา tree + `merge_report` | Text normalization and the Merge Engine re-home content **positionally**; char Δ = 0 across the whole merge. |
| 3 | Timeline | timeline stage | group → `is_latest_computed`, `timeline_seq` | Recency is *computed*, never trusted from source; no text touched. |
| 4 | Identity | `cid.assign_cids` / `assign_eids` | tree → `matra_cid` (primary key) + hierarchical `eId` | Identifiers are additive metadata; text and numbering unchanged. |
| 5 | Assemble | `assemble` stage (**new**) | a cross-record code family → one consolidated code | Every emitted row is verbatim from a source record; the union equals the expected มาตรา set or a gap is declared. |
| 6 | Flat / Wrap | `flat.to_flat` / `enrich_docs` / `work_expressions` | tree → flat rows + ELI Work/Expression wrapper | Flat is *generated* from the tree; the ancestor breadcrumb makes hierarchy survive flattening. |
| 7 | QA | `qa.qa_check` | outputs → `qa_report` | The gate: char round-trip Δ, section conservation, merge conservation. `hard_fail` blocks output. |

### 1. Split — `splitter.split_record`

The upstream record is a single flat list of section rows that glues an enacting instrument, the code body, its amendment acts, and editorial remarks together. `split_record` ungues them into per-document groups at **doc-title boundaries** (`sectionTypeId == 1`), and classifies each group's `doc_type` from the enumerated set: `code`, `enacting_act`, `amendment_act`, `royal_decree`, `emergency_decree`, `ministerial_regulation`, `announcement`, `act`. This is where "one record" stops being a lie: a Criminal Code record that arrives as one row becomes the code plus its enacting act plus each amendment act, each independently addressable.

### 2. Structure + Merge — `structure.build_docs_merged`

Builds the positional container tree ภาค → ลักษณะ → หมวด → ส่วน → มาตรา, then normalizes text: วรรค (paragraphs sharing a section number) are joined in order, en-space artifacts are stripped, spacing follows the OCS reference rendering. The TOC is **generated from the tree** — the source สารบาญ is discarded as corrupted.

The **Merge Engine** is the organ no upstream project ships. Thai amendment acts frequently insert whole structures — a new ลักษณะ, a new หมวด — with the inserted material parked at the *end* of the consolidated raw file, and often with no directive sentence at all: the heading declares its own position by number (ลักษณะ ๑/๑ slots itself between ลักษณะ ๑ and ๒). The engine re-homes these trailing amendment directives to their correct positions by anchor algebra (slash-number sequences, plain increments, scope fallbacks), and proves conservation on the way — the `merge_report` records every re-homing with a running char total, and the whole merge must close at Δ = 0. A pipeline that only parses directive sentences reconstructs a code with entire ลักษณะ missing and never knows.

### 3. Timeline

The source `is_latest` flag is broken and must not be trusted. This stage computes `is_latest_computed` per group as `max(timeline_seq)` within the `law_group_code` family, and derives `timeline_seq` from the trailing integer of `timeline_code`. Ordering for display comes from `timeline_seq` (newest first); exactly one Expression per Work may carry the "ฉบับล่าสุด" tag, and it comes from the computed flag only.

### 4. Identity — `cid.assign_cids` / `assign_eids`

Assigns the two identifier systems. `matra_cid` is the **primary key** (see §matra_cid). `eId` is the hierarchical container path (AKN-style ASCII structural id, e.g. `art_135_1`, `part_2__title_1_1`), recomputed per Expression; `wId` equals `eId` at first assignment under the v0 contract.

### 5. Assemble — cross-record code assembly (new stage)

Some codes are not stored as a single consolidated record. The **Civil & Commercial Code** is the canonical case: it lives across many timeline records, **one enacting instrument per บรรพ (Book)**, with no single row that holds the whole code. Naively picking the single fullest record — the strategy that works for the Criminal Code — drops **5 of the 6 Books**.

The assembly stage detects and repairs this:

1. **Detect.** A code family whose fullest *single* record covers far fewer มาตรา than the family *union* is flagged as a cross-record code. (A normal code's fullest record ≈ its union; a fragmented code's does not.)
2. **Select the body holder per Book.** For each บรรพ, consolidate from the clean code-body holder, preferring in order: a `code`-typed split-doc → the enacting `royal_decree` → the enacting `act`.
3. **Take the longest contiguous block.** From each holder, take its longest **contiguous** มาตรา block. This deliberately excludes each enacting act's own preamble มาตรา 1/2/3, which collide with the code's own numbering.
4. **Range-scope.** Scope each Book's contribution to its มาตรา range so Books do not overlap.

**Conservation guarantee:** every emitted row is verbatim from a source record — assembly *selects and orders*, it never synthesizes text. The union of assembled Books must equal the expected มาตรา set for the code; any shortfall is **declared as an explicit gap**, never silently dropped. This is the conservation law applied across records instead of within one.

### 6. Flat / Wrap — `flat.to_flat` / `enrich_docs` / `work_expressions`

Produces the two consumer views from the single tree store:

- **Flat export** — 1 row = 1 มาตรา, with the full ancestor breadcrumb walked from each node up through its containers, so hierarchy survives flattening. Column order is frozen by the schema (`flat_profile.columns`, a `const` so drift fails validation).
- **Work / Expression wrapper** (`work_expressions.json`) — the ELI-style `is_realized_by` graph connecting a law (Work) to its consolidated versions (Expressions), so "the version in force" is a query, not a guess.

### 7. QA — `qa.qa_check`

The conservation gate (see below). Runs last on every build and `hard_fail`s if any invariant is violated.

## matra_cid = the primary key

`matra_cid` is the join key the entire ecosystem depends on — the viewer, the version timeline, and the ฎีกา / case-law join all key on it.

- **Format:** `{law_group_code}:{matra_no_arabic}` — for example `ป0006-1D-0003:335/1`.
- **Verbatim number:** the section-number component keeps its Thai/slash/space forms as they appear in the number (the `335/1` above is the Arabic mirror; forms like `๙๐/๑` are preserved in `number`). The CID is not re-canonicalized.
- **Stability across versions:** because `law_group_code` and the section number both survive amendment, the CID is stable across consolidated versions. A section keeps its identity even as the code around it is amended. This stability is *proven*, by building a `-00`-style baseline version and a latest version of the same law and confirming the CIDs match (see [`docs/PUBLISHING.md`](PUBLISHING.md#matra_cid-as-an-open-standard)).

Because the CID is stable and public, third parties (case-law providers, viewers) can join on it without coordinating with Matra — this is what makes it a standard rather than an internal detail.

## FRBR / Akoma Ntoso mapping

Matra keeps JSON as its storage and processing format, and adopts the international semantic models where they fit. The mapping:

| FRBR level | Matra binding | Identifier |
|---|---|---|
| **Work** — the law as an abstract entity | the law group | `law_group_code` |
| **Expression** — a consolidated version | one timeline version | `timeline_code` / `timeline_seq` |
| **Manifestation** — a serialized rendering | the tree / flat views | — |
| container path within an Expression | structural node | `eId` (hierarchical) |

The `work_expressions.json` wrapper is ELI-style: `is_realized_by` links a Work to its Expressions.

This mapping is a **deliberate graft from Akoma Ntoso (OASIS) and its FRBR model, adapted** — not a full adoption. Akoma Ntoso's generic model does not natively express the Thai *positional* structure (ภาค/ลักษณะ/หมวด/ส่วน containers and slash-numbered positional amendments). An external standards assessment put Akoma Ntoso's confidence at expressing Thai positional amendment at ~10% without extension. Matra therefore keeps the Thai positional structure that the generic model omits, and extends rather than pretends where the two collide. The full adopt/hold ledger, with reasons per feature, lives in [`docs/akn_adoption_verdicts.md`](akn_adoption_verdicts.md).

## Conservation gate as contract

The QA gate is the contract that makes the whole standard trustworthy. Two levels operate:

1. **Per-build gate.** On *every* build, `qa.qa_check` runs a character round-trip and requires **Δ = 0** — the characters that entered the pipeline equal the characters that left it. Section conservation (rows in = rows out) and merge conservation (the Merge Engine's re-homed characters balance) are checked alongside. Any failure `hard_fail`s and blocks output. This is not a spot check; it is a gate every artifact passes before it exists.

2. **Corpus sampling gate.** The same unchanged pipeline is run across the whole corpus — a stratified, seed-pinned sample spanning decades **1870s–2020s** — and reports a **pass-rate plus a defect inventory**. The gate may never regress: a pipeline change that drops the pass-rate is rejected. Current baseline: **382 law groups, 100% pass, 0 exceptions**. Groups that once failed (worst case 74% character loss) are retained as permanent golden regression cases.

**Quarantine lane.** Unknown section types are never guessed. They route to a quarantine report that ships *with* the dataset — preserved, counted, visible. A pipeline that only logs its winners lies about what it dropped; the quarantine lane is how Matra refuses to.

## Schema versioning

[`schemas/matra-0.2.json`](../schemas/matra-0.2.json) (JSON Schema 2020-12) is the **frozen contract**.

- **Field names are frozen.** A conforming dataset uses the schema's field names exactly.
- **Changes are additive with a version bump.** New capability arrives as new optional fields under a new schema version (e.g. the v0.3 backlog item to promote `sectionTypeId 18` bodies to a displayable `content` node); existing fields do not change meaning.
- **`x_*` is out of scope.** The `x_*` namespace is reserved for implementation extensions and is **not part of the standard**. Consumers must not depend on `x_*` fields; producers must not put standard-level meaning in them.

The separation is the point: the *display* may pivot per document type (a code renders differently from an emergency decree), but *this standard never changes per law*.
