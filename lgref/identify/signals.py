"""Does a signal from PLAY improve rule identification? (#321)

A reviewer's point: with co-activation weighted zero, grouping is purely
static, and the earlier null result (co-activation lowered ARI on
tic-tac-toe and nim) is one signal on two games. The validation protocol
(#315) also found the failure a dynamic signal is the obvious candidate
for: statements the reference shares between rules are almost never
kept in both.

This module runs two play signals through the same discipline as
`protocol.py`, with every setting below FIXED BEFORE ANY SCORE WAS SEEN
and pre-registered on issue #321:

  co_activation  statements whose bodies are satisfiable in the same
                 states (Jaccard >= 0.8): the existing signal
  co_use         statements used in the same proofs of derived outcomes
                 (containment >= 0.8): new, aimed at sharing

  candidates     each signal at weight 0.5, 1.0, 2.0; the default is
                 the static graph (both weights zero)
  traces         20 random games of at most 40 plies, seed 0
  resolution     the production rule (coverage, tolerance 0.03),
                 recalibrated on the graph WITH the signal's edges

  TUNE on dev (highest mean ARI; a tie keeps the default), DECIDE on
  validation (adopted only if strictly higher), REPORT test, plus the
  reference-shared statements kept shared, which is reported and never
  used for a choice.

Like `protocol.py`, this RECOMMENDS; it never sets a weight. The
production weights are constants in `cluster.py`.
"""

import functools
import os

from lgref.identify.clauses import load
from lgref.identify.cluster import (DEFAULT_WEIGHTS, calibrate_resolution,
                                    cluster)
from lgref.identify.coactivation import (collect_proof_traces,
                                         collect_traces)
from lgref.identify.graph import ClauseGraph
from lgref.identify.protocol import _assignment
from lgref.identify.testgames.ground_truth import SPLITS, expected_partition
from lgref.identify.validate import pairwise_scores

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.join(HERE, 'testgames')

DEFAULT = ('static', 0.0)
CANDIDATES = ([DEFAULT]
              + [('co_activation', w) for w in (0.5, 1.0, 2.0)]
              + [('co_use', w) for w in (0.5, 1.0, 2.0)])
N_GAMES = 20
MAX_PLIES = 40
TRACE_SEED = 0


def _path(game):
    return os.path.join(GAME_DIR, game + '.gdl')


@functools.lru_cache(maxsize=None)
def traces(game, kind):
    """The traces for one game and signal: the same for every weight,
    so every candidate is scored on the same observations."""
    nodes = load(_path(game))
    collect = collect_traces if kind == 'co_activation' \
        else collect_proof_traces
    return tuple(frozenset(s) for s in collect(
        _path(game), nodes, n_games=N_GAMES, max_plies=MAX_PLIES,
        seed=TRACE_SEED))


def graph_for(game, signal):
    """(nodes, graph, weights) for one game under one signal."""
    kind, weight = signal
    nodes = load(_path(game))
    graph = ClauseGraph(nodes)
    weights = dict(DEFAULT_WEIGHTS)
    if kind == 'co_activation':
        graph.add_co_activation(traces(game, kind))
        weights['co_activation'] = weight
    elif kind == 'co_use':
        graph.add_co_use(traces(game, kind))
        weights['co_use'] = weight
    elif kind != 'static':
        raise ValueError('unknown signal {!r}'.format(signal))
    return nodes, graph, weights


def score(game, signal, seed=0):
    nodes, graph, weights = graph_for(game, signal)
    resolution = calibrate_resolution(graph, weights=weights, seed=seed)
    rules, _dropped = cluster(graph, weights=weights,
                              resolution=resolution, seed=seed)
    expected = expected_partition(game, nodes)
    predicted = _assignment(rules)
    scores = pairwise_scores(predicted, expected,
                             [n.node_id for n in nodes])
    shared = [c for c, names in expected.items() if len(names) > 1]
    scores.update(
        game=game, signal=signal, n_groups=len(rules),
        n_edges=graph.edge_count(signal[0]) if signal[0] != 'static'
        else 0,
        n_shared=len(shared),
        shared_kept=sum(1 for c in shared if len(predicted.get(c, ())) > 1))
    return scores


def mean_ari(games, signal, seed=0):
    return sum(score(g, signal, seed)['ari'] for g in games) / len(games)


def select(dev_games=None, candidates=CANDIDATES, seed=0):
    dev_games = tuple(dev_games or SPLITS['dev'])
    table = [(s, mean_ari(dev_games, s, seed)) for s in candidates]
    best = max(v for _s, v in table)
    tied = [s for s, v in table if abs(v - best) < 1e-9]
    return (DEFAULT if DEFAULT in tied else tied[0]), table


def decide(chosen, validation_games=None, seed=0):
    validation_games = tuple(validation_games or SPLITS['validation'])
    ours = mean_ari(validation_games, chosen, seed)
    base = mean_ari(validation_games, DEFAULT, seed)
    adopted = chosen if (chosen != DEFAULT and ours > base) else DEFAULT
    return adopted, ours, base


def run(seed=0):
    chosen, table = select(seed=seed)
    adopted, ours, base = decide(chosen, seed=seed)
    rows = []
    for split in ('dev', 'validation', 'test'):
        for game in SPLITS[split]:
            rows.append((split, game,
                         {s: score(game, s, seed) for s in CANDIDATES}))
    return {'table': table, 'chosen': chosen, 'adopted': adopted,
            'validation': (ours, base), 'rows': rows}


def format_report(result):
    lines = ['TUNING on dev {} -- mean ARI'.format(list(SPLITS['dev']))]
    for signal, value in result['table']:
        lines.append('  {:<14} {:<4} {:.3f}'.format(
            signal[0], signal[1], value))
    ours, base = result['validation']
    lines.append('chosen on dev: {}'.format(result['chosen']))
    lines.append('validation: chosen {:.3f} vs default {:.3f} -> adopted '
                 '{}'.format(ours, base, result['adopted']))
    lines.append('')
    head = '{:<11} {:<14}'.format('split', 'game') + ''.join(
        ' {:>12}'.format('{}{}'.format(
            {'static': 'static', 'co_activation': 'act',
             'co_use': 'use'}[k], '' if k == 'static' else w))
        for k, w in CANDIDATES)
    lines.append('ARI (labelled-shared statements kept in two or more '
                 'rules / all)')
    lines.append(head)
    for split, game, scores in result['rows']:
        lines.append('{:<11} {:<14}'.format(split, game) + ''.join(
            ' {:>5.3f} {:>2}/{:<2}'.format(
                scores[s]['ari'], scores[s]['shared_kept'],
                scores[s]['n_shared']) for s in CANDIDATES))
    return '\n'.join(lines)


if __name__ == '__main__':
    print(format_report(run()))
