"""Turn any method's grouping into interventions, the same way for all.

One intervention per group. Two procedures:

  ownership     the production procedure (#313). The groups are made
                into `CandidateRule`s and split by
                `lgref.identify.cluster.assign_ownership`: statements the
                group OWNS are deleted, its GUARDS are relaxed at their
                call sites, and statements something outside the group
                needs are kept. The split is structural -- head kinds,
                body literals, variable binding -- and reads no name and
                no label, so applying it to a baseline's groups gives the
                baseline the same intervention builder LGREF has.
  delete_group  delete every statement of the group, shared members
                included; relax nothing. The crude procedure, reported
                beside the first so the ownership split's contribution
                is visible.

An intervention that removes and relaxes nothing is EMPTY. It is
attempted (it is one of the method's groups) but it is not a valid
intervention, because it does not intervene: counting it valid would
let a method raise its valid rate by proposing groups nothing can be
removed from.
"""

from lgref.identify.cluster import CandidateRule, assign_ownership
from lgref.identify.graph import ClauseGraph
from lgref.identify.intervention import ablate_forms, removed_by_ablation

PROCEDURES = ('ownership', 'delete_group')


class Intervention(object):
    __slots__ = ('group', 'removed', 'relaxed', 'text', 'procedure')

    def __init__(self, group, removed, relaxed, text, procedure):
        self.group = group
        self.removed = frozenset(removed)
        self.relaxed = dict(relaxed)
        self.text = text
        self.procedure = procedure

    @property
    def empty(self):
        return not self.removed and not self.relaxed

    def __repr__(self):
        return '<Intervention g{} -{} ~{}>'.format(
            self.group, len(self.removed),
            sum(len(v) for v in self.relaxed.values()))


def to_text(forms):
    from ggp.infix import forms_to_infix_lines
    return '\n'.join(forms_to_infix_lines(forms)) + '\n'


def build(nodes, grouping, procedure='ownership'):
    """[Intervention], one per group of `grouping`, in group order."""
    if procedure not in PROCEDURES:
        raise ValueError('procedure must be one of {}'.format(PROCEDURES))
    out = []
    if procedure == 'delete_group':
        for index, group in enumerate(grouping.groups):
            forms = ablate_forms(nodes, set(group))
            out.append(Intervention(index, group, {}, to_text(forms),
                                    procedure))
        return out
    graph = ClauseGraph(nodes)
    rules = []
    for index, (group, core) in enumerate(zip(grouping.groups,
                                              grouping.core)):
        rules.append(CandidateRule('G{:03d}'.format(index), core,
                                   set(group) - set(core), graph))
    assign_ownership(rules, graph)
    for index, rule in enumerate(rules):
        removed, relaxed = removed_by_ablation(rule)
        forms = ablate_forms(nodes, removed, relaxed)
        out.append(Intervention(index, removed, relaxed, to_text(forms),
                                procedure))
    return out
