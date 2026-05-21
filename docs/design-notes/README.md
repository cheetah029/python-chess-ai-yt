# Design Notes (mirror of agent memory)

These files are a **mirror** of the AI agent's persistent memory, which
normally lives outside the repo at
`~/.claude/projects/-Users-ag-Code-python-chess-ai-yt/memory/` and is
auto-loaded at the start of each agent session. They are copied here so
the design reasoning, analysis history, open questions, and roadmap are
**version-controlled and visible in the editor** alongside the code.

## What's here

- **MEMORY.md** — the index of all the topic notes below.
- **project_roadmap.md** — the 4 project goals: (1) finish the >6-piece
  symmetric stall analysis, (2) human-vs-AI game mode, (3) train the AI on
  the new rules (finalize rules first), (4) ambitious GDL/GGP research
  (aimed at ISEF, ROBO category).
- **project_chess_variant_overview.md** — one-page summary of the variant.
- **project_tiny_endgame_status.md** — the adopted tiny-endgame rule
  (≤6 non-king + cancel-queens balance), full design history, the
  operational stall test, the >6 symmetry-breaking / fork-forceability
  analysis, and the exact next-step pick-up point.
- **project_tiny_endgame_analysis_methodology.md** — the operational
  stall-vs-forceable test and analysis methodology.
- **project_piece_strategic_dynamics.md** — bishop active-pin / global
  teleport, queen lock-down, queen-as-bishop escape, action stalling,
  manipulation/reactive-capture timing, the bishop double-manip nuance +
  bug root cause, and self-capture terminology.
- **project_helper_semantics.md**, **project_state_hash_design.md**,
  **project_v2_knight_redesign.md**, **project_tiny_endgame_fix.md** —
  topic-specific implementation notes.

## Source of truth

- **Rules:** `RULEBOOK_v2.md` is authoritative. `docs/key-rule-differences.md`
  and `docs/potential-rule-changes.md` are the rule cheat-sheet and design
  backlog. Code is in `src/`.
- **These design-notes:** a point-in-time SNAPSHOT of agent memory. They
  may drift from the live agent memory as the project evolves. When in
  doubt about current state, the latest commits + `RULEBOOK_v2.md` win.
  Re-run the mirror (copy the memory files here) to refresh.
