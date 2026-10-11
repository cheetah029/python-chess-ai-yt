"""Interventional tests: does a feature CAUSE the outcome, or accompany it?

WHY OBSERVATIONAL DISCOVERY WAS NOT ENOUGH, as a worked failure. Feature
discovery measured `Bishop` at d = -0.485 (z = 3.7, 240 games): holding
bishops predicts losing. A mechanism was offered for it -- transformation
into a form requires a friendly piece of that type to have been captured
earlier, so live bishops deny your own queen the bishop form, which is
the game's strongest defensive resource.

That explanation does not survive contact with the feature it explains:

  * The form unlock is a THRESHOLD at "at least one friendly bishop has
    been captured". `Bishop` is a LINEAR differential count. A linear
    count cannot express a threshold, so the two cannot be the same
    quantity. Concretely: going from one bishop to zero changes the
    count, but the form is already unlocked in BOTH cases, so the
    mechanism predicts no effect exactly where the feature predicts its
    usual one.
  * And bishops are not inert. Their reactive capture pins any enemy
    that must move off their diagonal, and their teleport applies that
    pin anywhere on the board in one turn.

THE REAL DEFECT IS CONFOUNDING, and it is structural rather than
statistical. In played games **bishop count and bishop-form availability
cannot vary independently**: a capture removes the piece and unlocks the
form in the same event. So no amount of observational data can separate
them, and `Bishop`'s coefficient is the SUM of a piece effect and a form
effect with no way to tell which carries it -- or whether they have
opposite signs and are partly cancelling.

WHAT THIS MODULE DOES ABOUT IT. The board and the capture record are
separately writable, so the two can be crossed deliberately even though
play never crosses them:

           form unavailable   form available
  2 bishops      A                  C
  1 bishop       D                  B

`A` and `B` are the only cells play produces. `C` holds material fixed
and unlocks the form; `D` holds the form fixed and removes the piece.
Then:

    FORM effect   = mean of (C - A) and (B - D)      bishops held fixed
    PIECE effect  = mean of (A - D) and (C - B)      form held fixed
    NATURAL       = (A - B)                          what play confounds
    INTERACTION   = (C - A) - (B - D)

Every cell is built from the SAME layout and played with the SAME agent
seeds, so position variance and playout variance cancel pairwise instead
of having to be averaged away.

WHAT IT STILL CANNOT DO. The outcome is a property of PLAY, so this
carries the agent that played it -- `docs/spec/objectivity.md` is
explicit that win rate cannot be freed of the agent the way a structural
metric can. An intervention removes CONFOUNDING, not agent dependence.
A result here is a causal claim about the agent used, and must be
re-measured under a stronger one before it is a claim about the game.
"""

import collections
import math
import random

Cell = collections.namedtuple('Cell', 'bishops form')

#: The four cells. `A` and `B` are the states ordinary play produces;
#: `C` and `D` are the ones it cannot, and are the entire point.
A = Cell(bishops=2, form=False)
B = Cell(bishops=1, form=True)
C = Cell(bishops=2, form=True)
D = Cell(bishops=1, form=False)
CELLS = (A, B, C, D)

Outcome = collections.namedtuple('Outcome', 'layout cell won censored plies')
Effect = collections.namedtuple('Effect', 'name mean sd se z n')


def _set_count(layout, side, count, kind='Bishop'):
    """`layout` with `side` holding exactly `count` of `kind`, or None.

    Only ever converts NON-ROYAL pieces, because removing a royal would
    decide the game by itself, and keeps every other piece and square
    untouched so the cells stay paired.
    """
    pieces = list(layout.pieces)
    mine = [i for i, p in enumerate(pieces)
            if p[0] == side and p[1] == kind]
    if len(mine) > count:
        for index in sorted(mine[count:], reverse=True):
            pieces.pop(index)
        return layout._replace(pieces=tuple(pieces))
    convertible = [i for i, p in enumerate(pieces)
                   if p[0] == side and not p[2] and p[1] != kind]
    needed = count - len(mine)
    if needed > len(convertible):
        return None
    for index in convertible[:needed]:
        colour, _name, royal, row, col = pieces[index]
        pieces[index] = (colour, kind, royal, row, col)
    return layout._replace(pieces=tuple(pieces))


def _drop_one(layout, side, kind='Bishop'):
    """The 2-piece layout minus exactly one of `kind`, so the 1-piece
    cells differ from the 2-piece cells by a single piece and nothing
    else."""
    pieces = list(layout.pieces)
    for index, piece in enumerate(pieces):
        if piece[0] == side and piece[1] == kind:
            pieces.pop(index)
            return layout._replace(pieces=tuple(pieces))
    return None


def build(make_engine, layout_two, cell, side, variant='full',
          max_turns=400, kind='Bishop'):
    """An engine holding `cell`'s version of the position.

    The capture record is written directly. That is not a fabricated
    state: a game in which a bishop was captured has exactly this
    record, and reaching a rule's precondition directly is what #237
    asks for. What it is NOT is reachable *together with* two live
    bishops -- which is precisely the cell play cannot produce and the
    reason this test exists.
    """
    from lgref.experiments.positions import apply_layout, usable

    layout = (layout_two if cell.bishops == 2
              else _drop_one(layout_two, side, kind))
    if layout is None:
        return None
    engine = make_engine(variant, max_turns=max_turns)
    apply_layout(engine, layout)
    engine.board.captured_pieces[side] = (
        [kind.lower()] if cell.form else [])
    if not usable(engine):
        return None
    return engine


def play(engine, side, agent='random', simulations=0, seed=0,
         max_turns=400):
    """Play `engine` out and report whether `side` won."""
    from lgref.experiments.random_play import build as build_agent

    white = build_agent(agent, random.Random(seed * 2 + 1), simulations)
    black = build_agent(agent, random.Random(seed * 2 + 2), simulations)
    plies = 0
    while not engine.is_game_over() and plies < max_turns:
        turns = engine.get_all_legal_turns()
        if not turns:
            break
        mover = white if engine.current_player == 'white' else black
        engine.execute_turn(mover.choose_turn(turns, engine))
        plies += 1
    winner = engine.winner
    return winner, plies


def run(make_engine, layouts=60, agent='random', simulations=0,
        variant='full', max_turns=400, seed=0, progress=None,
        kind='Bishop'):
    """The factorial. Returns the per-cell outcomes, paired by layout."""
    from lgref.experiments.positions import sample_layout

    rng = random.Random(seed)
    results = []
    attempts = 0
    produced = 0
    while produced < layouts and attempts < layouts * 20:
        attempts += 1
        base = sample_layout(rng, min_extra=4, max_extra=8)
        side = base.mover
        two = _set_count(base, side, 2, kind)
        if two is None:
            continue
        row = {}
        ok = True
        for cell in CELLS:
            engine = build(make_engine, two, cell, side, variant=variant,
                           max_turns=max_turns, kind=kind)
            if engine is None:
                ok = False
                break
            # COMMON RANDOM NUMBERS: the same playout seed in every
            # cell, so the four differ by the intervention and not by
            # which dice they were handed.
            winner, plies = play(engine, side, agent=agent,
                                 simulations=simulations,
                                 seed=seed * 1000 + produced,
                                 max_turns=max_turns)
            row[cell] = Outcome(layout=produced, cell=cell,
                                won=(1.0 if winner == side else 0.0),
                                censored=(winner is None), plies=plies)
        if not ok or len(row) != len(CELLS):
            continue
        produced += 1
        results.append(row)
        if progress is not None:
            progress(produced, layouts, row)
    return results


def _paired(values, name):
    """Mean, spread and z of a paired difference."""
    n = len(values)
    if n < 2:
        return Effect(name=name, mean=float('nan'), sd=float('nan'),
                      se=float('nan'), z=float('nan'), n=n)
    mean = sum(values) / float(n)
    var = sum((v - mean) ** 2 for v in values) / float(n - 1)
    sd = math.sqrt(var) if var > 0 else 0.0
    se = sd / math.sqrt(n) if sd else 0.0
    z = (abs(mean) / se) if se else (float('inf') if mean else 0.0)
    return Effect(name=name, mean=mean, sd=sd, se=se, z=z, n=n)


def effects(results, include_censored=False):
    """The decomposition. Censored games are EXCLUDED by default.

    A game with no winner is not evidence that `side` did not win -- that
    is #260, and counting it as a loss would bias every cell toward
    whichever intervention lengthens games.
    """
    def usable_row(row):
        if include_censored:
            return True
        return not any(row[cell].censored for cell in CELLS)

    rows = [row for row in results if usable_row(row)]
    won = {cell: [row[cell].won for row in rows] for cell in CELLS}

    form = [((row[C].won - row[A].won) + (row[B].won - row[D].won)) / 2.0
            for row in rows]
    piece = [((row[A].won - row[D].won) + (row[C].won - row[B].won)) / 2.0
             for row in rows]
    natural = [row[A].won - row[B].won for row in rows]
    interaction = [(row[C].won - row[A].won) - (row[B].won - row[D].won)
                   for row in rows]
    return {
        'rows': len(rows),
        'dropped': len(results) - len(rows),
        'rates': {cell: (sum(v) / float(len(v)) if v else float('nan'))
                  for cell, v in won.items()},
        'form': _paired(form, 'FORM unlock (bishops held fixed)'),
        'piece': _paired(piece, 'BISHOP piece (form held fixed)'),
        'natural': _paired(natural, 'NATURAL contrast (what play confounds)'),
        'interaction': _paired(interaction, 'INTERACTION'),
    }


def report(summary, agent, simulations, kind='Bishop'):
    low = kind.lower()
    label = {A: 'A  2 {}s, form off'.format(low),
             B: 'B  1 {},  form on'.format(low),
             C: 'C  2 {}s, form on '.format(low),
             D: 'D  1 {},  form off'.format(low)}
    lines = [
        'INTERVENTIONAL DECOMPOSITION: {}'.format(kind.upper()),
        '',
        'Observational discovery reported `Bishop` at d = -0.485 and a',
        'mechanism was offered: live bishops deny your own queen the',
        'bishop form. That cannot be what the feature measures -- the',
        'unlock is a threshold, the feature is a linear count, and the',
        'two disagree exactly at one bishop versus none.',
        '',
        'In played games the piece and the form CANNOT vary',
        'independently: one capture does both. So the two are crossed',
        'here by writing the capture record directly, which play cannot',
        'do. Cells A and B are what play produces; C and D are not.',
        '',
        'AGENT: {} ({} simulations). An intervention removes'.format(
            agent, simulations),
        'CONFOUNDING, not agent dependence -- the outcome is a property',
        'of play, so this is a causal claim about this agent.',
        '',
        'Win rate for the intervened side, {} paired layouts'.format(
            summary['rows']),
        '({} dropped for censoring):'.format(summary['dropped']),
    ]
    for cell in (A, D, C, B):
        lines.append('   {:<24} {:>7.3f}'.format(
            label[cell], summary['rates'][cell]))
    lines += ['', '{:<44} {:>8} {:>7} {:>6}'.format(
        'effect', 'mean', 'SE', 'z')]
    for key in ('piece', 'form', 'natural', 'interaction'):
        e = summary[key]
        lines.append('{:<44} {:>+8.3f} {:>7.3f} {:>6.1f}'.format(
            e.name, e.mean, e.se, e.z))
    lines += ['',
              'If PIECE is positive and larger in magnitude than FORM,',
              'the mechanism offered for `Bishop` is refuted: bishops',
              'are worth more than the form their loss unlocks, and the',
              'observational sign came from the confound rather than',
              'from the rule.']
    return '\n'.join(lines)
