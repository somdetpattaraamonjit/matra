# Credits & Attribution — Matra (มาตรา)

Matra stands on other people's best thinking. This file is the complete, honest
attribution chain: every architecture or idea we grafted, every step of the data
source chain, and the licence that binds them. Our stance throughout: **we study
and adapt the best thinking in open legal data — we do not copy it.** Where an
upstream model broke on Thai reality, we extended it and said so; where it fit,
we adopted it and credited it here.

If you find an attribution that is thin, wrong, or missing, that is a defect —
open an issue. Honesty is a feature of this project, and attribution is part of
the honesty.

---

## Architecture & ideas grafted

**1. Harvard Library Innovation Lab — OLAW & COLD ("COLD French Law")** · *primary architectural inspiration*
The lineage of the whole standard. From Harvard LIL's Caselaw/legal open-data work
we took the flat **"1 row = 1 article / มาตรา"** dataset shape, the **conservation
principle** (what goes in comes out — nothing silently dropped), and the practice of
shipping a **Known-Defects ledger** beside the data instead of hiding the mess. COLD
French Law proved this design on consolidated French civil law; Matra adapts it to
Thai statutory data, which is dirty in ways France's is not (glued timelines,
positional amendments, a broken `is_latest` flag). The RAG-citation pattern comes
from OLAW. We adapted the shape; we did not copy the corpus.
Cite: Cargnelutti & Cushman, 2024 (COLD French Law). Their data is CC-BY.
Repos: `harvard-lil/cold-french-law` (Hugging Face), `harvard-lil/olaw` (GitHub, MIT).

**2. Légifrance / LEGI (DILA, France)** · *consolidated-versions + codes model*
France's LEGI database treats a **code as a living consolidated text with a version
timeline** — not a static file, but a Work realised by many dated Expressions. That
model directly inspired Matra's **search-first, code-first navigation** and the
**version timeline** (our Work→Expressions wrapper, and "the version in force on
date X" as a query rather than a guess). We took the mental model of consolidation-
over-time; the implementation and the Thai structural handling are ours.
Source: Légifrance / base LEGI, Direction de l'information légale et administrative —
<https://www.legifrance.gouv.fr>

**3. Akoma Ntoso (OASIS LegalDocML standard)** · *FRBR model + hierarchical eId*
From Akoma Ntoso we grafted the **FRBR Work/Expression/Manifestation** model
(Work = law group, Expression = consolidated version, Manifestation = tree/flat
view) and **hierarchical `eId` identifiers** (structural ids using AKN element
names, with Latin legal-ordinal suffixes for ทวิ/ตรี/จัตวา…). We keep the
international vocabulary as an interop layer. But Akoma Ntoso does **not** natively
model Thai **positional** amendments (a heading that declares its own slot by number,
with no directive sentence) — an external standards assessment put its confidence at
**~10% without extension**. So Matra extends rather than pretends: the Merge Engine
plus the `akn:th:positional_insertion` vocabulary is the missing piece. We adopted
AKN where it fit and named exactly where it broke — see
[`akn_adoption_verdicts.md`](akn_adoption_verdicts.md) for the full adopt/hold ledger.
Standard: OASIS LegalDocML (Akoma Ntoso) —
<https://docs.oasis-open.org/legaldocml/akn-core/v1.0/akn-core-v1.0-part1-vocabulary.html>

---

## Data sources

**4. Open Law Data Thailand (OLDT)** · *upstream statute corpus + community*
The open Thai statute corpus Matra cleans, and the community Matra publishes back to.
OLDT is the gov-backed open-law effort (Senate / สลค. / สำนักงานคณะกรรมการกฤษฎีกา /
DGA-backed) that makes consolidated Thai statute text publicly available. Matra's
input records come from here; our cleaned outputs are meant to flow back to this
ecosystem, attribution intact.
Publisher: <https://huggingface.co/open-law-data-thailand> (datasets `ocs-krisdika`,
`soc-ratchakitcha`) · website <https://www.openlawdatathailand.org> · GitHub `DGA-Thailand`.

**5. สำนักงานคณะกรรมการกฤษฎีกา — Office of the Council of State (`ocs-krisdika`)** · *authoritative source text*
The original authoritative source of the consolidated statute text, reaching Matra
via OLDT. Every per-record `reference_url` in the dataset points at the official
`searchlaw.ocs.go.th` page, so every claim is one click from its source. Source text
and numbering are **never mutated** — upstream defects (they exist; see the dataset
card's Known Defects) are annotated in place, not corrected.
Data licence: **CC-BY 4.0**, attribution required.

**6. PyThaiNLP — `thailaw` dataset** · *Thai legal corpus tooling / ecosystem reference*
PyThaiNLP's `thailaw` dataset is a reference point in the Thai legal-NLP ecosystem;
we credit it as prior open work in Thai legal corpora and tooling that the field
(and anyone building on Matra) benefits from.
Dataset: <https://huggingface.co/datasets/pythainlp/thailaw-v1.0> — licence **CC0-1.0**
(public domain per Thai Copyright Act B.E. 2537 s.7). Cite: Phatthiyaphaibun, W. (2024),
*ThaiLaw: Thai Law Dataset*, Zenodo, doi:10.5281/zenodo.10701494.

---

## Case-law layer

**7. `phoneee/thai-legal-corpus` (Hugging Face)** · *the ฎีกา layer*
Extracted and cleaned Supreme Court decisions (คำพิพากษาศาลฎีกา) with citation links.
The sibling case-law lane uses this to **join case law to มาตรา** via `matra_cid`,
so a section can surface the ฎีกา that cite it. This is a separate lane from the
statute pipeline in this repo, but it shares the `matra_cid` join key, so the credit
belongs in the chain.
Licence: **CC-BY 4.0**. Join key: `matra_cid`.
Dataset: <https://huggingface.co/datasets/phoneee/thai-legal-corpus>
Underlying rulings: official <https://deka.supremecourt.or.th> (public domain per Thai
Copyright Act B.E. 2537 s.7(4)); citation metadata & cleaning by phoneee (CC-BY 4.0).

---

## Licence chain

| Artifact | Licence |
|---|---|
| Matra **code** (this repo) | **MIT** — © 2026 Somdet Pattaraamonjit |
| Matra **data** outputs | **CC-BY 4.0** |

How attribution flows:

```
สำนักงานคณะกรรมการกฤษฎีกา (ocs-krisdika, CC-BY 4.0)
        │   authoritative consolidated statute text
        ▼
Open Law Data Thailand (OLDT)          ← open Thai statute corpus + community
        │   published upstream records
        ▼
Matra pipeline (code MIT · data CC-BY 4.0)
        │   audit · unglue · Merge Engine · conservation QA · sampling gate
        ▼
downstream users  →  must preserve the CC-BY attribution chain:
                     Matra → Open Law Data Thailand → สำนักงานคณะกรรมการกฤษฎีกา
```

- **Data is CC-BY 4.0.** Reuse is welcome; the attribution chain above must travel
  with it. The chain is preserved downstream — attribution is not stripped at any hop.
- **Code is MIT.** Reuse the pipeline freely under MIT terms.
- **Case-law join** uses `phoneee/thai-legal-corpus` (CC-BY 4.0); that attribution
  travels with any case-law-joined output as well.
- Allowed source origins are pinned in code (`ocs-krisdika`, `soc-ratchakitcha`, plus
  official `searchlaw.ocs.go.th` reference pages). Case-law **aggregator** sites are
  permanently out of scope for the statute pipeline.

---

## Citation

If you use Matra, cite the repo and credit the full chain.

> **Matra (มาตรา)** — an open data standard and cleaning pipeline for Thai law at
> the section (มาตรา) level. Data © contributors, CC-BY 4.0, derived from
> Open Law Data Thailand ← สำนักงานคณะกรรมการกฤษฎีกา (Office of the Council of State).
> Code MIT © 2026 Somdet Pattaraamonjit.
> Lineage acknowledgements: Harvard LIL — COLD French Law + OLAW
> (Cargnelutti & Cushman, 2024); Légifrance/LEGI (DILA); Akoma Ntoso (OASIS LegalDocML).
> Case-law layer: `phoneee/thai-legal-corpus` (CC-BY 4.0), joined via `matra_cid`.

```bibtex
@misc{matra,
  title        = {Matra: An Open Data Standard and Cleaning Pipeline for Thai Law
                  at the Section (มาตรา) Level},
  author       = {Pattaraamonjit, Somdet},
  year         = {2026},
  note         = {Data CC-BY 4.0 (chain: Matra -> Open Law Data Thailand ->
                  Office of the Council of State / krisdika). Code MIT.
                  Lineage: Harvard LIL COLD French Law + OLAW
                  (Cargnelutti and Cushman, 2024); Legifrance/LEGI; Akoma Ntoso.}
}
```
