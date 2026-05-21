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

### Goal 1 — Finish the >6-piece symmetric position analysis
Determine whether dense symmetric >6-non-king positions (e.g., K+RQ+PQ+B+B vs same) are stall-prone or forceable, to confirm the tiny endgame rule's ≤6-non-king scope is SUFFICIENT.
- Leading conclusion: LIKELY sufficient, via the FORCED-TRADE-DOWN argument (forks force mutual trades → piece count drops by 2 → reaches ≤6 → rule activates).
- The crux/open question: are forks FORCEABLE in dense symmetric positions, or can a defender keep all pieces mutually un-forkable while mirroring?
- Fork mechanisms: short-range (knight / queen-as-knight) + long-range (rook / queen-as-rook). User's mechanism: a transformed promoted-queen forking RQ + PQ/bishop.
- Full details + exact pick-up point: project_tiny_endgame_status.md ("Symmetry-breaking forced-capture analysis", "Fork-forceability").

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
Resolved recently: repetition-rule invuln cycle (c7e0ffd), tiny endgame redesign (1c7cdec), bishop double-manip reactive capture (9d60689), boulder capture-return (60a2e4d). Still to confirm before training: (a) Goal 1's >6 stall question (does the ≤6 rule suffice?), (b) a deliberate sweep for any other minor rule ambiguities (the kind that keep surfacing — manipulation/reactive-capture timing, self-capture semantics, boulder edge cases, knight invuln edge cases). Treat RULEBOOK_v2.md as authoritative; keep docs/key-rule-differences.md + docs/potential-rule-changes.md in sync.
