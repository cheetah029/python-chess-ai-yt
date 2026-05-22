---
name: project-roadmap-goals-python-chess-ai-yt
description: "High-level goals for the chess-variant project — analysis, human-vs-AI mode, AI training with new rules, and the ambitious GDL/GGP research direction (aimed at ISEF, ROBO category). Read for project direction / \"what are we building toward.\""
metadata: 
  node_type: memory
  type: project
  originSessionId: e3b1db7b-ec7f-4a43-9b69-568c3971b17d
---

# Project roadmap (captured 2026-05-20)

The project is a custom chess VARIANT (see project_chess_variant_overview.md, RULEBOOK_v2.md). Beyond rule design, it is aimed at RESEARCH — notably a future ISEF entry, potentially in the **ROBO (Robotics and Intelligent Machines)** category.

## Current main goals (in order)

### Goal 1 — Finalize the ruleset (incl. the >6 symmetric stall question)
Goal 1 has two parts: (1) confirm the tiny endgame rule's ≤6-non-king scope is sufficient, and (2) the broader ruleset-finalization sweep (rare clarifications/edge cases) so rules don't churn mid-training (Goal 3).
- **STATUS (2026-05-20): part (1) CLOSED — the ≤6 non-king scope is ACCEPTED as SUFFICIENT** (user decision). The rule will NOT be expanded beyond ≤6 non-king. Lean: forceable — the mirror does NOT save the defender (royals fall one at a time; any trade to ≤6 activates the rule), symmetry is breakable (capture-across-center is often available), and the last-royal asymmetry favors the side to move. Documented residual: whether the side-to-move is advantaged in a symmetric rule-active position is a geometry-dependent zugzwang question, not provable by hand (engine impractical); worst case a rare dense-symmetric position is stall-prone but still terminates (slowly) under the repetition rule, and no clean expansion predicate exists. See project_tiny_endgame_status.md "DECISION (2026-05-20)". Re-open only if a concrete stall-prone >6 position is demonstrated.
- **Goal 1 part (2) — DONE (2026-05-22):** the ruleset-finalization sweep is COMPLETE. Swept pawn-capture, manipulation restrictions, boulder, knight-invuln, reactive-capture timing, repetition state, promotion, win-condition/royal-capture. Genuine clarifications were RARE (as expected): boulder counts as a legal turn for the No-Legal-Moves loss (PR #54, +test PR #56); repetition state includes the boulder's cooldown + no-return memory (PR #57). Plus stale-TODO/comment hygiene (PR #54/#55/#56). **GOAL 1 FULLY DONE; rules finalized for training.**

### Goal 2 — New game mode: human vs AI player
Add a game mode where a human plays against an AI opponent. The codebase already has AI infrastructure (engine.py, network.py, players.py, trainer.py, selfplay.py, encoding.py). The current mainloops (main.py = v2 active, main_v0/v1 = frozen snapshots) are human-vs-human. Need to wire an AI player into the turn loop so one side is human-controlled (mouse) and the other is AI-controlled (engine).

### Goal 3 — Train an AI with the NEW updated game rules
The AI has NOT been trained with the current (post-redesign) rules — notably the redesigned tiny endgame rule (≤6 non-king + cancel-queens balance, commit 1c7cdec), the v2 knight invulnerability + jump-capture, the repetition-rule invuln fix, the bishop double-manip fix, and the boulder capture-return rule.
- **IMPORTANT PRECONDITION:** finalize the game rules FIRST (look for any remaining minor clarifications/tweaks) before training, to avoid expensive re-training after rule changes. Rule churn = wasted training.
- Training infra: trainer.py, selfplay.py, collect_variant_data.py, collect_finetuned_data.py, analyze_variants.py. Default engine manipulation_mode='freeze'.

### Goal 4 (ambitious, research) — GDL + GGP
- **GDL (Game Description Language):** formalize the written game rules into a logical/declarative GDL representation. Converts RULEBOOK_v2.md prose into machine-readable formal logic.
- **GGP (General Game Player):** build/use a general game player that takes the GDL as input. A GGP can adapt to rule modifications WITHOUT full re-training each time — a huge advantage given how often this variant's rules change.
- This variant could serve as a **benchmark for GGPs** (it's a novel, non-trivial game with unusual mechanics: reactive captures, manipulation, transformation, boulder, tiny-endgame rule).
- This is the heavy-research direction, aligned with ISEF / ROBO ambitions.

## Sequencing note
Goals 1 → (finalize rules) → 3 (train) is the dependency chain: don't train (Goal 3) until rules are finalized (which Goal 1 + a rules-finalization pass support). Goal 2 (human-vs-AI mode) can proceed in parallel since it doesn't depend on rule finalization (it uses whatever rules + whatever trained/untrained AI exists). Goal 4 (GDL/GGP) is the long-horizon research payoff.

## Rules-finalization checklist (before Goal 3 training)
Resolved recently: repetition-rule invuln cycle (c7e0ffd), tiny endgame redesign (1c7cdec), bishop double-manip reactive capture (9d60689), boulder capture-return (60a2e4d). **(a) Goal 1's >6 stall question — RESOLVED 2026-05-20: ≤6 scope accepted as sufficient (see Goal 1 STATUS above).** **(b) Ruleset sweep — DONE 2026-05-22.** Swept manipulation/reactive-capture timing, repetition state, boulder, knight-invuln, promotion, win-condition/royal-capture. Clarifications were rare (as expected): boulder counts as a legal turn for the No-Legal-Moves loss (PR #54, +test PR #56); repetition state includes the boulder's cooldown + no-return memory (PR #57); plus stale-TODO/comment hygiene (PR #54/#55/#56). RULEBOOK_v2.md authoritative; docs/key-rule-differences.md kept in sync. **CHECKLIST COMPLETE — rules finalized for Goal 3 training.**
