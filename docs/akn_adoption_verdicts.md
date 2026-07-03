# AKN Adoption Verdicts — Lindy Gate run 2026-07-02
Source: external LLM assessment of a Thai AKN/ELI application profile (frontier-scout capture, 2026-07-03; internal archive).
Gate: `~/.aice/lindy_gate.py` (fragility / behavior-Δ / restatement) — 8 items judged, appended to `~/.aice/lindy_gate.jsonl`.
Tally: **HARDEN 3 · HOLD 5 · DISCARD 0** (asymmetric — filter discriminating).

## The 5 first-read quality flags — resolutions

| # | Flag | Resolution |
|---|---|---|
| 1 | Steal #2 over-claims stakes ("pipeline drops sections, fails 220/220") | **Confirmed FALSE** — `docs/table_typeid_hunt_2026-07-03.md`: typeIds 5/11/12 = 0 rows in 14,087 sections; source never digitized tables; quarantine already conserves. Pattern HOLDs on merit (dormant), not on the assessment's stated stake. |
| 2 | `matra_cid` on container nodes | **Rejected for v0.** matra_cid is per-มาตรา by schema-frozen definition. Container addressing = hierarchical `eId` (adopted below). |
| 3 | Thai script in URIs | **Deferred with URI scheme (HOLD → v1).** Internal `matra_cid` keeps Thai `law_group_code` verbatim — it is an identifier, not a URI. Percent-encoding vs transliteration decided at publish-layer v1. |
| 4 | Gazette volume/part ref for the example amending act was unverified | **Not used anywhere.** publication block HOLDs; README/docs must not cite any gazette number until verified vs soc-ratchakitcha. |
| 5 | Falsification #3 unrunnable (application_scope empty) | **Parked with status engine 7′** — valid test, wrong data slice today. |

## Verdicts

| Item | Decision | One-line reason |
|---|---|---|
| **eId/wId separation** | **HARDEN → Task 6′** | Machine-safe ASCII ids; `number_arabic` has Thai suffixes/spaces ("335 ทวิ"), `node_id` is per-build positional — neither bindable; adding wId post-publish = breaking change. |
| **ELI `is_realized_by` wrapper** | **HARDEN → Task 5′** | Trivial JSON from data we already compute; unlocks "version in force on date X" programmatically. |
| **AKN-can't-do-positional (10% self-confidence)** | **HARDEN → README** | External confirmation of the moat; cross-checked vs our merge_grammar evidence (0 directives in -63, 282 in corpus). |
| e-LAWS attachment pattern (5/11/12) | HOLD | Dormant: zero table rows exist to convert. **Wake trigger: first real typeId 5/11/12 row observed in any gate run.** Goes in dataset card as design-intent note. |
| AKN-NC URI scheme | HOLD → v1 | No URI consumer in 5′-6′; two unresolved decisions (flags 3, 4). |
| container_cid | HOLD | Rhymes with hierarchical eId; no consumer. |
| publication gazette block | HOLD → 7′ | Evidence-or-unknown law: every value needs soc-ratchakitcha verification; consumer is status engine. |
| `akn:th:positional_insertion` vocabulary | HOLD (prose only) | Merge ledger already exists (`checks.merge`); use AKN name in README/dataset-card prose as interop vocabulary, don't rename code fields. |

## Design decisions binding Tasks 5′-6′

1. **`matra_cid` = `f"{law_group_code}:{number_arabic}"` VERBATIM** — schema-frozen. Spaces/Thai suffix allowed (`ป0006-1D-0003:335 ทวิ`). Stability = group+number survive amendment; never normalize inside cid.
2. **`eId`** = ASCII structural id using AKN element names: matra→`art`, phak→`part`, laksana→`title`, muad→`chapter`, suan→`subchapter`, kho→`clause`, bot→`transitional`. Containers hierarchically qualified (`part_2__title_1_1`) because ลักษณะ numbering restarts per ภาค. Number normalization: `/`→`_`; suffix words = FULL Latin legal-ordinal set matching what `structure.py` recognizes in the wild — ทวิ→`bis`, ตรี→`ter`, จัตวา→`quater`, เบญจ→`quinquies`, ฉ→`sexies`, สัตต→`septies`, อัฏฐ→`octies`, นว→`novies`, ทศ→`decies` (amended per review 6′ Minor #2 — original 3-suffix list was under-informed by the external profile); remaining spaces→`_`; residual non-`[A-Za-z0-9_]` sanitized + QA-flagged.
3. **eId collisions** (digit defect 6466038 puts two `title_1` under `part_2`): deterministic disambiguation suffix + flag on node — defect stays annotated-not-mutated, uniqueness restored mechanically.
4. **`wId`** = eId at first assignment (v0: `wId == eId`). Semantic contract documented: wId frozen across renumbering, eId recomputed per expression. Divergence trigger = first real renumbering event in corpus.
5. **Schema delta (additive)**: `structure.items.properties` += optional `eId`, `wId` (`["string","null"]`). `flat_profile` columns stay frozen (eId/wId live in tree JSON v0).
6. **ELI wrapper artifact**: `out/<group>/work_expressions.json` — `{work: law_group_code, expressions: [{timeline_code, is_latest_computed, …}], "eli:is_realized_by": [...]}` generated at export stage.
