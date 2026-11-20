# Research: literature reviews

Literature reviews that inform the LGREF research programme. They are
point-in-time documents: the text is kept as written, and this page records
what has changed in the project since.

## Novelty of GDL rule grouping (written 2026-11-18)

- [`novelty-of-gdl-rule-grouping.md`](novelty-of-gdl-rule-grouping.md): the
  report. Does any prior work automatically group a GDL description's
  statements into overlapping gameplay rules and then measure each rule by
  ablation? It found none, and it lists which parts of the method do have
  precedents.
- [`novelty-of-gdl-rule-grouping/`](novelty-of-gdl-rule-grouping/): the four
  supporting notes it was written from:
  - prior work on analysing GDL, Ludii and VGDL descriptions;
  - studies that evaluate game rules by ablation or variation;
  - methods for clustering software and logic programs;
  - benchmarks and metrics for overlapping clusters.

  Each note marks which citations were verified against a source and which
  were not. The report's last section lists the unverified ones, which must
  be checked before anything is cited.

### What has changed since it was written

The report's **literature findings** are unaffected. Its **figures about
LGREF**, and several of its **recommendations**, predate work merged on
2026-11-19:

| The report says | Now |
|---|---|
| Name-token margin: tic-tac-toe 0.711 vs 0.675 ARI | Unchanged. |
| Held-out game: 0.378 vs 0.316 (corridor) | 0.387 vs 0.316 at the production resolution. Corridor is now one of **four** test games, scoring 0.34–0.55. LGREF beats the name-token baseline on all four (`docs/lgref-validation.md`). |
| Nim: 0.734 vs 0.525 | 0.838 vs 0.525 at the production resolution. Nim is now a validation game. |
| Three labelled games; three games defensible as a feasibility result | **Eight** labelled games, split into dev, validation and test, with labels and splits pre-registered before scoring (#315). |
| The resolution is tuned on the evaluation games; choose tuned settings leave-one-game-out and report a sweep | Settings are tuned on dev only, decided once on validation, and never chosen on test (#315). A resolution sweep is reported for every game. |
| Scrambled-names robustness test (Kuhlmann & Stone) is "the cheapest decisive win" | **Done.** Rotating action arguments, renaming every symbol, and opaque renaming (every name replaced by a code) all give identical rules on every game including Royal Chess (#314, #320). |
| Report co-activation as a negative result | Extended: co-activation and a new proof co-use signal were run through the held-out protocol with pre-registered settings. Neither was adopted (#321). |
| Name the overlap metric (Omega, fuzzy Rand, BCubed); prefer AMI; use a permutation null | Not done. |
| Wider baselines: Leiden, link communities or OSLOM, trivial covers, edge-type ablation | Not done. |
| 30 or more seeds; a second, independent labeller; a Ludii-aligned second reference | Not done. |

New results the report could not know about:
- Statements shared between rules are almost never kept in two predicted
  rules.
- LGREF loses to the name-token baseline on drop-three and Monty Hall.

Both are recorded in `docs/lgref-validation.md`.
