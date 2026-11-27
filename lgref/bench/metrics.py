"""Grouping metrics for Paper A: extended BCubed with overlap, and the
uncertainty machinery every table uses.

EXTENDED BCUBED (Amigo, Gonzalo, Artiles & Verdejo, Information
Retrieval 12(4), 2009) is the primary grouping metric. Pair-counting
ARI is defined for hard partitions only, and the "overlapping ARI" the
project reported before is not a named measure; extended BCubed handles
overlap natively and satisfies the formal constraints Amigo et al. set
out. For statements e, e' with method groups C(.) and reference rules
L(.):

    P(e, e') = min(|C(e) & C(e')|, |L(e) & L(e')|) / |C(e) & C(e')|
    R(e, e') = min(|C(e) & C(e')|, |L(e) & L(e')|) / |L(e) & L(e')|

Precision is the mean over e of the mean of P(e, e') over the e' that
share a group with e (e itself included); recall likewise over the e'
sharing a reference rule with e. On hard partitions this is ordinary
BCubed, which the tests check.

REPRESENTATION, fixed in docs/paper-a/protocol.md before any score:

  - a statement in NO reference rule is not scored; how many there are
    is reported;
  - a statement the method leaves unclustered is its own singleton
    group, which costs recall and nothing else;
  - shared statements are multi-membership on either side, nothing more.

INTERVALS. The replication unit is the GAME. `bootstrap_interval`
resamples games, never statements, and `paired` reports per-game
differences between two methods.
"""

import random


def _complete(membership, scored):
    """Every scored statement mapped to a non-empty set of groups; an
    unclustered one gets a private singleton."""
    out = {}
    for item in scored:
        groups = membership.get(item) or ()
        out[item] = (frozenset(groups) if groups
                     else frozenset({('singleton', item)}))
    return out


def bcubed(predicted, reference, scored=None):
    """Extended BCubed precision, recall and F1.

    `predicted` and `reference` map statement ids to collections of group
    labels; labels are compared only within one side. `scored` defaults
    to the statements with at least one reference rule.
    """
    if scored is None:
        scored = sorted(item for item, rules in reference.items() if rules)
    scored = list(scored)
    if not scored:
        return {'precision': None, 'recall': None, 'f1': None,
                'n_scored': 0}
    c = _complete(predicted, scored)
    ref = {item: frozenset(reference.get(item) or ()) for item in scored}
    missing = [item for item in scored if not ref[item]]
    if missing:
        raise ValueError('scored statements with no reference rule: '
                         '{}'.format(missing[:5]))

    precision_terms, recall_terms = [], []
    for e in scored:
        p_sum = p_n = r_sum = r_n = 0
        for other in scored:
            common_c = len(c[e] & c[other])
            common_l = len(ref[e] & ref[other])
            if common_c:
                p_sum += min(common_c, common_l) / float(common_c)
                p_n += 1
            if common_l:
                r_sum += min(common_c, common_l) / float(common_l)
                r_n += 1
        precision_terms.append(p_sum / p_n)
        recall_terms.append(r_sum / r_n)
    precision = sum(precision_terms) / len(scored)
    recall = sum(recall_terms) / len(scored)
    f1 = (2 * precision * recall / (precision + recall)
          if precision + recall else 0.0)
    return {'precision': precision, 'recall': recall, 'f1': f1,
            'n_scored': len(scored)}


def coverage(predicted, scored):
    """Share of scored statements in some group of two or more."""
    sizes = {}
    for groups in predicted.values():
        for group in groups:
            sizes[group] = sizes.get(group, 0) + 1
    scored = list(scored)
    if not scored:
        return None
    covered = sum(1 for item in scored
                  if any(sizes.get(g, 0) >= 2
                         for g in predicted.get(item) or ()))
    return covered / float(len(scored))


def shared_recovery(predicted, reference):
    """Of the statements the reference puts in two or more rules, the
    share the method puts in two or more groups. None when the reference
    shares nothing -- not measured, not zero."""
    shared = [item for item, rules in reference.items() if len(rules) > 1]
    if not shared:
        return None
    kept = sum(1 for item in shared if len(predicted.get(item) or ()) > 1)
    return kept / float(len(shared))


def score_grouping(grouping, sheet, node_ids):
    """Every grouping metric for one method on one game.

    `grouping` is a `lgref.bench.methods.Grouping`; `sheet` an
    `lgref.bench.annotation.Sheet`, whose statement INDEX is the
    position in `node_ids` (both come from `load`, in file order).
    """
    from lgref.identify.validate import pairwise_scores

    by_index = sheet.membership()
    reference = {node_ids[index]: rules for index, rules in
                 by_index.items()}
    predicted = grouping.membership()
    scored = [n for n in node_ids if reference.get(n)]
    out = bcubed(predicted, reference, scored)
    out['coverage'] = coverage(predicted, scored)
    out['shared_recovery'] = shared_recovery(predicted, reference)
    out['n_unscored'] = len(node_ids) - len(scored)
    out['n_groups'] = len(grouping.groups)
    out['ari'] = pairwise_scores(predicted, reference, node_ids)['ari']
    return out


# ---- uncertainty --------------------------------------------------------

def bootstrap_interval(values, n_resamples=10000, seed=0, level=0.95):
    """(mean, low, high): a percentile bootstrap over the values given --
    one per GAME. None values (not measured) are dropped first, and the
    count kept is the caller's to report."""
    values = [v for v in values if v is not None]
    if not values:
        return None, None, None
    mean = sum(values) / float(len(values))
    if len(values) == 1:
        return mean, None, None
    rng = random.Random(seed)  # nosec B311: resampling, not security
    means = []
    for _ in range(n_resamples):
        sample = [values[rng.randrange(len(values))] for _v in values]
        means.append(sum(sample) / float(len(sample)))
    means.sort()
    tail = (1.0 - level) / 2.0
    low = means[int(tail * n_resamples)]
    high = means[min(n_resamples - 1, int((1.0 - tail) * n_resamples))]
    return mean, low, high


def paired(a, b):
    """Per-game differences a - b over the games both measured."""
    return {game: a[game] - b[game] for game in sorted(a)
            if game in b and a[game] is not None and b[game] is not None}


def seed_spread(values):
    """(mean, min, max) over seeds -- reported, never pooled with games."""
    values = [v for v in values if v is not None]
    if not values:
        return None, None, None
    return sum(values) / float(len(values)), min(values), max(values)
