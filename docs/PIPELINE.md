# Matra Pipeline v1 — Architecture

Status: DESIGN (2026-07-02 night) · Implements: schema v0.2 (`schemas/matra-0.2.json`) · Informed by: 8-defect audit, Sampling Gate 2026-07-02 (60 groups, 93.3% pass, typeIds 13/18/20 discovered), Harvard COLD/OLAW lineage, Open French Law RAG failure analysis.
> SUPERSEDED NUMBERS: the gate has since been extended corpus-wide — current baseline **382/382 groups PASS (100%), 0 exceptions**, decades 1870s–2020s, all previously-failing groups green. The design laws below stand unchanged.

## Stages

```
 STAGE 0   ACQUIRE      host-side fetcher (HF ocs-krisdika, month-file granularity)
                        manifest + sha256 + byte size per file · incremental · never scrape
     │                  non-open sources REJECTED at this door (allowlist in code)
 STAGE 1   AUDIT        per-file inventory BEFORE parsing: row count, schema drift,
                        sectionTypeId census · unknown typeId → QUARANTINE report,
     │                  never silent-drop, never crash (Berkson rule)
 STAGE 2   SPLIT        unglue 1 record → enacting_act / code / amendment_acts / remarks
     │                  (defect #3; boundary = typeId 1)
 STAGE 3   MERGE        ★ Merge Engine (defect #8, the missing organ): apply
                        "ให้เพิ่มความต่อไปนี้เป็น…" / "ให้ยกเลิกความใน…และให้ใช้ความต่อไปนี้แทน"
     │                  directives from amendment acts → TRUE consolidated tree
 STAGE 4   STRUCTURE    tree ภาค/ลักษณะ/หมวด/ส่วน/มาตรา + บทเฉพาะกาล (typeId 13)
     │                  วรรค join (repeated sectionNo) · spacing per OCS reference · TOC generated
 STAGE 5   ENRICH       timeline (is_latest_computed from suffix — source flag is broken)
                        per-matra status + effective_from/until (EVIDENCE-BASED or "unknown")
     │                  matra_cid = law_group:number_arabic · refs_out regex · deka_refs (phase 2)
 STAGE 6   VALIDATE     jsonschema vs matra-0.2 · conservation (rows & chars in = out, Δ=0)
     │                  spot-diff vs searchlaw.ocs.go.th reference_url · Thai-digit fidelity probe
 STAGE 7   PUBLISH      tree JSON (web) + flat JSONL (AI, 1 row = 1 มาตรา with breadcrumb)
                        + qa_report + Known Defects → HF dataset, append-only, versioned
 ─────────────────────────────────────────────────────────────────────────────
 REGRESSION GATE        Sampling Gate re-run (stratified, seed-pinned) on EVERY pipeline
 (cross-cutting)        change · pass-rate may never regress · new typeId → auto-quarantine
```

## Design laws (each traceable to a paid-for lesson)

1. **Quarantine, don't crash; log the invisible.** Unknown sectionTypeIds (13=บทเฉพาะกาล, 18, 20 found by sampling; 5/11/12 still unseen) route to a quarantine report that ships WITH the dataset. A pipeline that only logs winners lies. *(Sampling Gate + Berkson audit)*
2. **Conservation law.** Every transform proves rows-in = rows-out + chars-in = chars-out (charΔ 0). The 4 gate failures (worst 74% char loss) are the permanent golden regression cases. *(Gate run 2026-07-02)*
3. **Evidence or "unknown".** `status`/`effective_*` are never asserted without `status_evidence`. The #1 legal-RAG failure mode is temporal/material scope confusion — it is fixed HERE, at the data layer, not in prompts. *(Open French Law RAG, Harvard LIL 2025)*
4. **Pure functions, thin CLI.** Every stage is an importable function with explicit inputs (Finding #0: engine normalize() NameErrors on a CLI-only global — that class of bug is banned). CLI wraps; tests import.
5. **One truth, two views.** Tree (web display) and flat (ML/RAG) are both GENERATED from the same store; flat rows carry the full ancestor breadcrumb so hierarchy survives flattening. *(COLD French Law pattern + falsification #1)*
6. **Idempotent + provenance.** Re-running any stage on the same input is a no-op; every output carries source, reference_url, pipeline_version, ingested_at. Publish is append-only.

## What came from Harvard vs what is ours

| Layer | Origin |
|---|---|
| Standard SHAPE: per-section status, validity window, stable section ID, flat ML export, MT provenance flag | **COLD French Law** (adapted; France's LEGI arrives pre-cleaned by the state) |
| RAG pattern: LLM → search statement → confirmed search → cited answer; retrieval_unit citation contract | **OLAW** (MIT; Cargnelutti & Cushman 2024) — running locally against a local model |
| Scope-failure countermeasures (status+dates in data; 1-click verify via reference_url) | **Open French Law RAG** case study |
| **Stages 1-6: the cleaning engine** — audit, unglue, MERGE ENGINE, conservation QA, sampling gate | **Matra original.** Thai source data is dirty in ways France's is not; no upstream project ships this. This is the moat. |

## Mapping to plan tasks

Stage 2+4 = Task 3′ (vendor engine normalizer + fix import contract + TYPE_MAP {13,18,20}) · Stage 3 = Task 4′ Merge Engine (Friday) · Stage 5 = Tasks 5′-7′ · Stage 6 = Task 9-10 e2e · Stage 7 = Task 11 publish · Regression Gate = `~/.aice/legalrag/work/sampling_gate.py` (seed 42, extend past cap 60 → cover 1980-2025 next run).
