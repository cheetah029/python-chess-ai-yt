"""GGP — General Game Player for the v2 chess variant.

Skeleton implementation targeting GDL-I rules from
docs/gdl/. The intended use is reasoner-validating the GDL
fragments against `src/engine.py`'s legal-move enumeration.

Module layout:
  - parser.py   : GDL text → nested Python tuples.
  - kb.py       : facts + rules indexed by predicate name.
  - resolver.py : backward-chaining query with negation-as-failure.
  - game.py     : (planned) wraps KB+resolver for legal /
                  next / terminal / goal queries.

This is the FIRST GGP component for Goal 4. It's intentionally
minimal — only enough resolution to validate step 1 (kings +
queens) end-to-end. Subsequent PRs extend the resolver to handle
the more advanced GDL constructs in steps 6-11 and add
state-progression machinery + MCTS / minimax search.
"""
