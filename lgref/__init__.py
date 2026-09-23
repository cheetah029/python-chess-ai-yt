"""LGREF — Logic-Based Game Rule Evaluation Framework.

Identifies gameplay RULES from the formal clauses of a GDL game
description, hypothesises their STRATEGIC FUNCTIONS, measures their
CONTRIBUTIONS by ablation, and turns the result into objective-
conditioned recommendations.

Vocabulary (see docs/lgref-experiments.md; fixed in issue #175):

    formal clause -> rule -> strategic function -> measured contribution

    formal clause       one statement in the formal representation
                        (a GDL fact or implication)
    rule                a gameplay provision implemented by one or more
                        formal clauses
    strategic function  the strategic role a rule may serve
    contribution        its measured effect under a stated comparison

A rule may be implemented by several clauses, and one clause may support
several rules. Rules are grouped by the behaviour their clauses jointly
implement, NOT by a shared strategic function.

Package layout:
    config/      YAML experiment configs (seeds explicit)
    core/        manifests, cost accounting, Parquet storage, releases
    identify/    Phase 1 — clause dependency graph, rule identification
    functions/   Phase 2 — function ontology, frozen predictions
    experiments/ Phase 3 — agents, matched training, metric collection
    analysis/    Phase 4 — effect sizes, variance decomposition, RCI
    recommend/   Phase 5 — objective-conditioned recommendations
    explain/     Phase 6 — evidence records -> constrained prose
    report/      Phase 7 — figures, tables, reproduction

    reference/   HELD-OUT seed ontology labels. Deliberately NOT a
                 package: it has no __init__.py, so it cannot be
                 imported. Evaluation code loads it by explicit path.
                 lgref/tests/test_label_isolation.py fails the build if
                 identify/ or functions/ references it.

This package imports the game rules from src/ (Board, GameEngine); it
never reimplements them. Per the project's trust order, RULEBOOK.md
is authoritative, then the playable implementation (main.py / board.py,
which GameEngine shares), then the GDL, then the GGP.
"""

import os as _os
import sys as _sys

# Make the framework runnable without the caller setting PYTHONPATH.
#
# LGREF imports the game rules from `src/` (Board, GameEngine, the GGP
# resolver and the infix GDL parser), which is a sibling directory
# rather than an installed package. Every entry point therefore needs
# both the repository root and `src/` on the path. Leaving that to the
# caller meant the framework only ran for someone who already knew to
# set PYTHONPATH -- which the tests never noticed, because pytest puts
# the repository root on the path itself.
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _path in (_ROOT, _os.path.join(_ROOT, 'src')):
    if _path not in _sys.path:
        _sys.path.insert(0, _path)

__version__ = '0.1.0'
