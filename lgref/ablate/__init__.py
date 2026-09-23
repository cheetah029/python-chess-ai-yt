"""Ablation operations: how a variant description is derived from the base.

Three modes, of which two are generated automatically:

  relax    drop a body conjunct; the game becomes more permissive
  remove   delete an entity and everything that dies with it
  replace  substitute a different definition

`replace` matters more than it first looks. The deliverable is a
RETAIN / REVISE / REMOVE verdict per rule, and relax and remove can only
say whether a rule matters -- never whether THIS version of it is the
right one. `revise` is unreachable without it.

Most of it is automatable (`parameters.py`): a rule parameterised by a
numeric constant in its own clauses can be varied, turning a binary
ablation into a dose-response curve. What stays designer-supplied is a
genuinely novel mechanic -- the v2 knight replaced by the legacy knight
is a redesign, not a parameter change.
"""

from lgref.ablate.operations import (UnsafeRelaxation, relax,
                                     remove_constant, remove_clauses)
from lgref.ablate.parameters import counters, perturb, sweep

# `parameters` (the function) is deliberately NOT re-exported here. It
# would shadow `lgref.ablate.parameters` (the submodule) on this
# package, so `from lgref.ablate import parameters` would hand back a
# function and every `parameters.perturb(...)` would fail with
# `'function' object has no attribute`. Import the submodule by path:
#
#     from lgref.ablate import parameters as params   # the module
#     params.parameters(forms)                        # the function
__all__ = ['relax', 'remove_constant', 'remove_clauses', 'UnsafeRelaxation',
           'perturb', 'sweep', 'counters']
