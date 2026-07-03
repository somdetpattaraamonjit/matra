# Publishing Matra as an Open Standard

**How to turn the Matra pipeline into a public, reproducible, credited open standard.** This document covers the build, the distribution channels, the honesty discipline that ships with every dataset, the `matra_cid` scheme as a joinable public contract, and the attribution chain. For the pipeline internals it references, see [`docs/ARCHITECTURE.md`](ARCHITECTURE.md); for the full credit ledger, [`docs/CREDITS.md`](CREDITS.md).

## 1. Reproducible build

One command takes the corpus to a dataset:

```bash
PYTHONPATH=src python3 demo/build_all_laws.py
```

Corpus directories are supplied via environment variables so the build is portable across machines:

| Variable | Points at |
|---|---|
| `MATRA_CORPUS_DL` | the downloaded / month-file corpus |
| `MATRA_CORPUS_RAW` | the raw record source |

The build is **deterministic** (same corpus in → same dataset out; re-running is a no-op) and **conservation-gated** (the per-build Δ = 0 character round-trip and the section/merge conservation checks `hard_fail` before any artifact is written — see [`docs/ARCHITECTURE.md`](ARCHITECTURE.md#conservation-gate-as-contract)).

It emits **`build_report.json`**: a full accounting of what was **built**, **skipped**, and **recovered**, with **every skip named and reasoned**. This is the "ไม่ทิ้งเงียบ" rule — nothing is dropped silently. A skipped record is not an absence; it is a line item with a cause (e.g. a known-empty source record, or a notification-class instrument whose body lives in a section type the flat profile v0 has no row for). A reader can reconcile the corpus against the dataset from the report alone.

## 2. Distribution channels

Matra publishes through four channels, in order of authority:

| # | Channel | What ships | License |
|---|---|---|---|
| a | **GitHub public repo** | the pipeline code and schema | code **MIT** |
| b | **Hugging Face datasets** (`matra-*`) | the built data in two profiles | data **CC-BY 4.0** |
| c | **Community registry showcase PR** | a showcase entry to the DGA-Thailand / Open-Law-Data-Thailand registry | — |
| d | **Courtesy discussion threads** | lineage-crediting notes to OLDT and harvard-lil/OLAW | — |

**(a) GitHub.** The repository carries the pipeline, schema, tests, and docs. Code is MIT.

**(b) Hugging Face datasets, named `matra-*`.** Two profiles ship:
- a **train / flat profile** — 1 row per มาตรา (the ML/RAG view, with the frozen column order and ancestor breadcrumb);
- an **index profile** — the lookup / navigation view.

Data outputs are CC-BY 4.0 under the attribution chain in §5.

**(c) Community registry showcase.** A showcase pull request to the **DGA-Thailand / Open-Law-Data-Thailand** community registry, so the dataset is discoverable from the Thai open-data community's own index rather than only from Matra's channels.

**(d) Courtesy threads.** Discussion threads to **OLDT** and **harvard-lil/OLAW** that credit the lineage Matra builds on. These are courtesy and provenance, not promotion: they close the loop back to the projects whose thinking Matra grafted.

## 3. Known-Defects discipline

**Every dataset card ships a Known Defects section.** Honesty is a feature of the standard, not an apology for it — a consumer who cannot see what is wrong or missing cannot trust what is right. The discipline is: state the defect, its cause, and Matra's handling (preserve-and-annotate, defer, or flag — never silently "fix" source text).

Representative entries:

- **Status detection deferred.** Repealed / pending status detection is deferred; per-section `status` falls back to `"unknown"` rather than guess.
- **Reference recall unknown.** The `refs_out` cross-reference extraction is regex-based; its recall against the full variety of citation phrasings is not yet measured.
- **Civil Code Book 1 reflects original enacted text.** The 2535 (re-examined) revision of บรรพ ๑ is stored in the source as a **non-separable amendment act**, not as a clean consolidated record. Matra **flags** this rather than auto-applying it — applying a non-separable amendment would require synthesizing text, which the conservation law forbids.
- **Tax / tariff tables are scanned images upstream.** Some tables in tax and tariff law exist in the source only as scanned images, not as machine-readable table structure; they cannot be emitted as `table` nodes until the upstream data carries them as text.

Each of these is a line in the card, visible to every consumer, updated as items are resolved.

## 4. `matra_cid` as an open standard

The point of publishing `matra_cid` is **joinability**: a third party — a case-law (ฎีกา) provider, a viewer, another dataset — can key their own data on the CID and join to Matra without coordinating with Matra at all.

- **The scheme is published**, not just the values: `{law_group_code}:{matra_no_arabic}`, with the section-number component kept verbatim (Thai / slash / space forms preserved). A third party can *construct* a CID for a section they hold and expect it to match Matra's.
- **The stability guarantee is proven, not asserted.** Because `law_group_code` and the section number survive amendment, a section's CID is stable across consolidated versions. This is demonstrated by building a `-00` (baseline) version and the latest version of the same law and confirming the CIDs match. The proof, not just the claim, is what lets a case-law provider trust that a citation keyed to a CID this year still resolves next year.

Joining on the CID (rather than regex over prose) is also what removes the text artifacts seen in existing products — run-together tokens like `มาตรา3` — because the join is on a structured key, not on scraped text.

## 5. Attribution / licence chain

Full detail lives in [`docs/CREDITS.md`](CREDITS.md); the summary chain:

**Data lineage** (each layer attributes the one below):

```
Matra
  ← Open Law Data Thailand
      ← ocs-krisdika (สำนักงานคณะกรรมการกฤษฎีกา)
```

Data outputs are **CC-BY 4.0** and must carry this chain: **Matra → Open Law Data Thailand → สำนักงานคณะกรรมการกฤษฎีกา**.

**Architecture lineage** (the thinking Matra grafted):

| Layer | Origin |
|---|---|
| Standard shape — per-section status, validity window, stable section IDs, flat ML export, MT provenance flag | **Harvard LIL COLD / OLAW** (Cargnelutti & Cushman 2024), adapted |
| Consolidated-law data model reference | **Légifrance / LEGI** (France's state-cleaned corpus) |
| Semantic model — FRBR Work/Expression, `eId` node identifiers | **Akoma Ntoso (OASIS)**, adapted with a Thai positional extension |

The cleaning engine itself — audit, unglue, Merge Engine, cross-record assembly, conservation QA, sampling gate — is **Matra original**: Thai source data is dirty in ways France's pre-cleaned corpus is not, and no upstream project ships this. The graft is the *shape and the citation contract*; the *cleaning* is the contribution.

**Source allowlist.** Allowed sources are pinned in code (`ocs-krisdika`, `soc-ratchakitcha`, and official `searchlaw.ocs.go.th` reference pages). Case-law aggregator sites are permanently out of scope. Publishing does not widen this allowlist.
