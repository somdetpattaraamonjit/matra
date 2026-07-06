# Matra (มาตรา)

**An open data standard and cleaning pipeline for Thai law, at the section (มาตรา) level.**

Thai statutory data is publicly available — the hard part is making it *usable*. As bulk-published legal data, the upstream records concatenate whole timelines into single records, place amendment content at the end of the file rather than merged into position, and carry source artifacts (a legacy `is_latest` flag, table-of-contents inconsistencies, an occasional heading mis-number). These are normal characteristics of open legal-data publishing — not a fault of the publishers, whose openness makes this project possible — but they make the data hard to use directly. Every Thai legal-tech project pays this cleaning cost privately. Matra pays it once, in the open, with proofs, and reports issues back upstream.

## What you get
<!--DEKA_FRESH-->
**🆕 Deka freshness:** case-law index last topped-up from the official Supreme Court search on **2026-07-03** (+94 post-snapshot cases, human-in-loop weekly). Live list: `demo/public/latest.html` · feed: `demo/public/data/deka/latest.json`
<!--/DEKA_FRESH-->

One truth, two views, every claim checkable:

- **Tree JSON** (`docs_v02.json`) — full document hierarchy ภาค → ลักษณะ → หมวด → ส่วน → มาตรา with generated TOC, per-node identifiers, and provenance.
- **Flat JSONL** (1 row = 1 มาตรา) — the ML/RAG view: 19 fixed columns including the full ancestor breadcrumb, so hierarchy survives flattening; `matra_cid` stable identifiers; extracted cross-references; computed timeline facts.
- **Work→Expressions wrapper** (`work_expressions.json`) — ELI-style `is_realized_by` graph connecting a law (Work) to its consolidated versions (Expressions), so "the version in force" is a query, not a guess.
- **QA report beside every output** — conservation counts, TOC audit, quarantine ledger, known defects. Failures are loud; nothing is silently dropped.

## The missing organ: the Merge Engine

Thai amendment acts frequently insert whole structures (a new ลักษณะ, a new หมวด) **with no directive sentence at all** — the inserted heading simply declares its own position by number (ลักษณะ ๑/๑ inserts itself between ลักษณะ ๑ and ๒). In the consolidated Criminal Code record, all four amendment-inserted structures (terrorism, electronic cards, passports, offences relating to corpses) arrive this way, parked at the end of the raw file. A pipeline that only parses directive sentences reconstructs a code with entire ลักษณะ missing — and never knows.

International standards do not model this. **Akoma Ntoso cannot natively represent Thai positional amendments (an external standards assessment put its confidence at 10% without extension) — Matra's Merge Engine plus the `akn:th:positional_insertion` extension is the missing piece.** The engine re-homes inserted structures by anchor algebra (slash-number sequences, plain increments, scope fallbacks), proves conservation (rows and characters in = out, Δ = 0), and writes an auditable merge ledger into the QA report.

## Whole codes scattered across records: the Assembly stage

Some codes are not stored as one record but as **one enacting instrument per Book (บรรพ)**. The Civil & Commercial Code arrives as 73 timeline records whose union is all **1,755 มาตรา across 6 บรรพ** — yet no single record holds more than บรรพ 3 (845 มาตรา). Picking the fullest single record silently drops five of six Books (the exact failure this project exists to kill). The Assembly stage detects a fragmented code family and consolidates it from the clean code-body holder per Book — preferring a `code`-typed document, then the enacting decree; each contributes its **longest contiguous มาตรา block**, so an enacting act's own preamble มาตรา ๑–๓ never contaminate the code's numbering. Every emitted section is verbatim from source (conservation Δ = 0). Each built code then carries a **`completeness`** descriptor that separates *truly absent from the corpus* (`gaps_absent`) from *present but not yet merged into the code body* (`gaps_unmerged`): nothing is claimed complete that isn't, and nothing real is hidden. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Data QA discipline

Every design law here is traceable to a defect found in the wild:

| Law | Practice |
|---|---|
| Conservation | Every transform proves rows-in = rows-out and char Δ = 0; violations hard-fail. |
| Quarantine, don't crash | Unknown section types are preserved, counted, and shipped in the QA ledger — never dropped, never guessed. |
| Evidence or "unknown" | `status` / `effective_*` are never asserted without evidence; the #1 legal-RAG failure mode (temporal/material scope confusion) is fixed at the data layer. |
| Verbatim source | Source text and numbering are never mutated. Upstream errors (yes, they exist — see Known Defects) are annotated, not corrected. |
| Regression gate | A stratified sampling gate across the corpus (2,000 law groups, decades 1870s–2020s, seed-pinned) runs on every pipeline change: currently **100% pass, 0 exceptions**. |

Current test suite: **106 tests, 0 skipped**, including byte-identical golden locks on the normalizer, 4/4 golden merge targets (7,237 chars re-homed, 0 loss), cross-version `matra_cid` stability, cross-record code assembly (Civil & Commercial Code → all 1,755 มาตรา, anti-contamination + conservation proven), and an end-to-end run of the full Criminal Code (1,031 sections → 34 documents, TOC audit-matched).

## Quickstart

```bash
git clone <this-repo> && cd matra && pip install -e .
python3 -m matra.cli path/to/raw_record.json out/ --merge --flat
# out/: docs_v02.json · toc_generated.json · qa_report.json · flat.jsonl · work_expressions.json
```

## API surface

```python
from matra import (normalize_record,      # record -> (docs, flags)
                   build_docs_merged,     # record -> (docs, flags, merge_report)
                   enrich_docs,           # + matra_cid / eId / wId  (separate stage)
                   to_flat, FLAT_COLUMNS, # doc -> flat rows (19 schema-frozen columns)
                   work_expressions,      # records -> ELI Work->Expressions wrapper
                   qa_check, toc_of)
```

Schema: [`schemas/matra-0.2.json`](schemas/matra-0.2.json) (JSON Schema 2020-12). The `x_*` namespace is reserved for implementation extensions and is not part of the standard.

## Standards interop

Matra keeps JSON as the storage/processing format and adopts the international semantic models where they fit: FRBR mapping (Work = law group, Expression = consolidated version, Manifestation = tree/flat), AKN-style `eId`/`wId` node identifiers (structural vs semantic, with Latin ordinal suffixes for ทวิ/ตรี/จัตวา…), and an ELI `is_realized_by` graph. Where the standards break on Thai reality (positional amendment), Matra extends rather than pretends: see [`docs/akn_adoption_verdicts.md`](docs/akn_adoption_verdicts.md) for the full adopt/hold ledger with reasons.

## Lineage & credits

Full attribution chain, with what each source contributed and its licence, lives in [`docs/CREDITS.md`](docs/CREDITS.md) (machine-readable footer block: [`docs/attribution.json`](docs/attribution.json)). Summary:

| Layer | Origin |
|---|---|
| Standard shape (per-section status, validity window, stable IDs, flat ML export) | [COLD French Law](https://huggingface.co/datasets/harvard-lil/cold-french-law) (Harvard LIL; Cargnelutti & Cushman 2024), adapted |
| RAG citation pattern + Known-Defects discipline | [OLAW](https://github.com/harvard-lil/olaw) (Harvard LIL, MIT) |
| Consolidated-versions + code-first navigation | Légifrance / LEGI (DILA, France) |
| FRBR Work/Expression mapping + hierarchical `eId` | Akoma Ntoso (OASIS LegalDocML) |
| Source statute data | [Open Law Data Thailand](https://huggingface.co/open-law-data-thailand) (ocs-krisdika, CC-BY 4.0) ← สำนักงานคณะกรรมการกฤษฎีกา |
| Thai legal NLP tooling/reference | [PyThaiNLP — thailaw](https://huggingface.co/datasets/pythainlp/thailaw-v1.0) (CC0-1.0) |
| Case-law (ฎีกา) layer, joined via `matra_cid` | [phoneee/thai-legal-corpus](https://huggingface.co/datasets/phoneee/thai-legal-corpus) (CC-BY 4.0) |
| Audit · unglue · **Merge Engine** · **cross-record Assembly** · conservation QA · sampling gate | **Matra original** — Thai open data arrives in a rawer shape than France's state-consolidated LEGI (timelines glued, amendments parked at end-of-file), so this layer is needed here; no upstream project ships it yet. Issues we find are reported back upstream, not just patched locally. |

## Licenses

| Artifact | License |
|---|---|
| Code (this repo) | MIT |
| Data outputs | CC-BY 4.0 — attribution chain: Matra → Open Law Data Thailand → สำนักงานคณะกรรมการกฤษฎีกา |

Allowed sources are pinned in code (`ocs-krisdika`, `soc-ratchakitcha` + official searchlaw.ocs.go.th reference pages). Case-law aggregator sites are permanently out of scope.

## Known Defects

Honesty is a feature: the full inventory (source-data defects we preserve-and-annotate, v0 limitations, deferred detection) ships with the dataset — see [`docs/dataset_card_matra-criminal-code.md`](docs/dataset_card_matra-criminal-code.md#known-defects). Highlight: the Criminal Code source data itself mis-numbers ลักษณะ ๑๒ (ทรัพย์) as "๑" in its structural heading row — proven by the same record's own table of contents; Matra ships it verbatim with a defect annotation rather than silently "fixing" source text.

Whole-corpus & case-law honesty (the demo surfaces the same discipline):

- **Notification-class instruments** (≈1,428 กฎกระทรวง/ประกาศ whose body lives in typeId-18 blocks with no มาตรา/ข้อ markup at source) are **listed with a reason, never silently dropped** — conserved in the quarantine lane; a displayable `content` node is a v0.3 schema-additive backlog. Every skip is named in `demo/public/data/build_report.json`, shipped with the demo.
- **Domain taxonomy**: 7 of 1,619 laws (ประกาศคณะปฏิวัติ/รสช. with number-only titles) are shown as an explicit **"ยังไม่จัดหมวด"** bucket — not force-fit into a domain.
- **Case-law (ฎีกา) coverage**: the ⚖️ links join the open **phoneee/thai-legal-corpus** citation graph — **87,525 distinct rulings of ~133,119** in the official system (snapshot 2026-03-10 + 99 post-snapshot delta), across 236 laws. Counts are the trusted citation-inversion (14/14 exact vs official on a live cross-check), **not exhaustive**; the official system is CAPTCHA-gated so bulk completion is out of scope by policy. Each displayed case ships its **co-cited มาตรา** (`case_refs.json`) as a "what is this case about" fingerprint; full headnote (ย่อ/ฉบับเต็ม) text is official-only and linked out, never fabricated.

## Contributing

`tests/golden/make_golden.py` regenerates golden files **unconditionally** — `git diff` is the guard; never commit a golden change without understanding the byte-level diff. PRs must keep the sampling gate at 100% and the suite at 0 skips.
