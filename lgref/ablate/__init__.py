"""Ablation operations: how a variant description is derived from the base.

Three modes, of which two are generated automatically:

  relax    drop a body conjunct; the game becomes more permissive
  remove   delete an entity and everything that dies with it
  replace  substitute an alternative definition -- DESIGNER-SUPPLIED

`replace` is not here and cannot be. It needs a written alternative (the
v2 knight replaced by the legacy knight, say), which is a design
hypothesis rather than something derivable from the description. LGREF
discovers relax and remove candidates; it evaluates replace variants a
designer proposes.
"""

from lgref.ablate.operations import (UnsafeRelaxation, relax,
                                     remove_constant, remove_clauses)

__all__ = ['relax', 'remove_constant', 'remove_clauses', 'UnsafeRelaxation']
