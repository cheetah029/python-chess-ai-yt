"""Does a discovered evaluation actually PLAY well? Checked against exact
play, on games small enough to solve.

WHY THIS IS THE MISSING PIECE. Every claim about a discovered evaluation
so far rested on how strongly its features correlated with winning --
Cohen's d, AUC, a z score. None of that is the quantity of interest. A
feature can be strongly predictive while the ARGMAX of the score it
builds is a bad move, because a correlation measured over whole games
says nothing about which of two sibling positions is better. The only
honest test of an evaluation is the quality of the policy it induces,
and on a solvable game that can be measured exactly rather than
estimated.

So this module answers "is the inference accurate?" with ground truth
instead of a significance level. It is also fast: a 4x4 board resolves
in seconds, where the same question on the case study needs hours and
still cannot be checked against truth.

GAME-INDEPENDENT BY CONSTRUCTION. It needs a game exposing the protocol
the rest of the project uses (`get_all_legal_turns`, `execute_turn`,
`is_game_over`, `winner`, `current_player`, `copy`) and an `optimal`
function returning the value-preserving moves. Nothing here knows what
any game contains.

THREE WAYS THIS MEASUREMENT WENT WRONG BEFORE IT WENT RIGHT, all caught
by the uniform control and all recorded because each produced a
confident, wrong, publishable-looking number:

  THE SOLVER RETURNS A PAIR.  `mnk.optimal_moves` returns
      `(best_set, value)`. Treating it as the set made `pick in best`
      true only when a move index happened to equal the exact value
      (-1, 0 or 1), pinning every policy at about 6% and making the
      learned evaluation look WORSE THAN RANDOM. The weighting
      experiments that followed all returned ~6% regardless of their
      weights, which is the signature of a broken comparison rather
      than a weak evaluation.

  TIES WERE BROKEN BY LIST ORDER.  `max()` returns the first maximum, so
      a score with many ties collapses to "lowest cell index" -- a fixed
      positional bias that a uniform baseline does not share. Ties are
      now broken uniformly at random.

  THE CONTROL IS NOT OPTIONAL.  A uniform random policy must score the
      chance baseline, by definition. When it did not -- 6.1% against a
      15.7% baseline -- that was proof the harness was broken, not that
      random play is bad. Any run whose control misses its baseline
      should be discarded, so `report` prints them side by side.
"""

import collections

Accuracy = collections.namedtuple('Accuracy', 'rate chance n label')


def optimal_action_rate(make_game, optimal, policy, trials=400, seed=0,
                        max_setup=6, label=''):
    """How often `policy` picks a value-preserving move.

    Positions are reached by random play, then filtered: a position
    where EVERY move is optimal measures nothing, because any policy
    scores 100% on it. `chance` is the share of optimal moves averaged
    over the positions actually scored, which is exactly what a uniform
    policy achieves -- so it doubles as the control's expected value.
    """
    import random

    rng = random.Random(seed)
    hit = total = 0
    chance = 0.0
    for _ in range(trials):
        game = make_game()
        for _ in range(rng.randint(0, max_setup)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        if game.is_game_over():
            continue
        turns = game.get_all_legal_turns()
        if len(turns) < 2:
            continue
        best, _value = optimal(game)
        if not best or len(best) == len(turns):
            continue                   # no decision to get right
        total += 1
        chance += len(best) / float(len(turns))
        if policy(game, rng) in best:
            hit += 1
    if not total:
        return Accuracy(rate=float('nan'), chance=float('nan'), n=0,
                        label=label)
    return Accuracy(rate=hit / float(total), chance=chance / float(total),
                    n=total, label=label)


def evaluator_policy(evaluate):
    """A policy that plays the argmax of `evaluate`, one ply.

    TERMINAL STATES USE THE TRUE OUTCOME, because a learned estimate of
    a decided position is strictly worse than the decision -- and
    because a feature set sampled from non-terminal states can be blind
    to winning outright. Measured: completing a line converts a
    `Line:k-1` feature into `Line:k`, which never appears in traces
    sampled before the final move, so the learned score of a winning
    move equalled that of a quiet one exactly.

    TIES BREAK UNIFORMLY, for the reason in the module docstring.
    """
    def policy(game, rng):
        turns = game.get_all_legal_turns()
        mover = game.current_player
        scores = []
        for turn in turns:
            nxt = game.copy()
            nxt.execute_turn(turn)
            if nxt.is_game_over():
                if nxt.winner == mover:
                    scores.append(float('inf'))
                elif nxt.winner is None:
                    scores.append(0.5)
                else:
                    scores.append(float('-inf'))
            else:
                scores.append(evaluate(nxt, mover))
            continue
        top = max(scores)
        tied = [turn for turn, score in zip(turns, scores)
                if score >= top - 1e-12]
        return rng.choice(tied)
    return policy


def uniform_policy(game, rng):
    """The control. It must score the chance baseline, or the harness is
    wrong -- which is how three separate harness defects were found."""
    return rng.choice(game.get_all_legal_turns())


def report(results):
    lines = [
        'OPTIMAL-ACTION RATE AGAINST EXACT PLAY',
        '',
        'The question is not whether a feature correlates with winning.',
        'It is whether the evaluation built from it CHOOSES well, which',
        'is measurable exactly on a solvable game and is the only test',
        'that bears on playing strength.',
        '',
        'The uniform control must land on the chance baseline. If it',
        'does not, the harness is broken and every other row in the',
        'table is meaningless -- which has happened three times.',
        '',
        '{:<42} {:>9} {:>9} {:>7} {:>7}'.format(
            'policy', 'optimal', 'chance', 'ratio', 'n'),
    ]
    for item in results:
        ratio = (item.rate / item.chance) if item.chance else float('nan')
        lines.append('{:<42} {:>8.1%} {:>9.1%} {:>7.2f} {:>7}'.format(
            item.label, item.rate, item.chance, ratio, item.n))
    return '\n'.join(lines)

def victim_at_destination(turn):
    """The square whose occupant this turn takes, or None.

    THE DEFAULT IS "THE SQUARE IT LANDS ON", AND THAT IS NOT ALWAYS
    RIGHT. In the case study a knight may capture by jumping OVER a
    piece: the turn carries `is_capture = False` and names its victim in
    `jump_choice`, because nothing is taken where it lands.

    So the blunder metric was blind to exactly the threats the search
    was blind to -- a piece that only a jump-capture could take did not
    count as threatened, and a rescue that walked into one counted as
    safe. The search was fixed by injecting `is_tactical`; this is the
    same fix for the measurement, and both have to be injected because
    which turns take what is a fact about a game.
    """
    if getattr(turn, 'is_capture', False):
        return getattr(turn, 'to_sq', None)
    return None


def _setup_plies(rng, max_setup):
    """How many random plies to reach a sampled position.

    CLAMPED, because `randint(4, 1)` raises. Every instrument here took
    a `max_setup` and passed it straight to `randint(4, ...)`, so any
    caller asking for a shallow sample -- a test wanting one ply, or a
    game that ends in three -- got `ValueError: empty range` instead of
    a measurement. Found by a test that asked for `max_setup=1`.
    """
    return rng.randint(min(4, max(1, max_setup)), max(1, max_setup))


def rescue_oracle(game, _rng=None, victim_square=None):
    """The move that leaves the FEWEST rescuable pieces capturable.

    WHY THE METRIC NEEDS THIS. `rescuable_losses` counts at-risk pieces,
    not positions, and a turn moves ONE piece -- so when three pieces
    are rescuable at once, two of them are counted as lost no matter
    what is played. The metric therefore has a FLOOR WELL ABOVE ZERO,
    and a rate of 46% means nothing until that floor is known. I quoted
    46% as a failure for several rounds without ever measuring what the
    best achievable number was.

    This policy minimises exactly the quantity the metric counts, by
    enumeration, so running the harness with it in place of the agent
    measures the floor. It is not a player and must never be used as
    one: it ignores the game, the outcome and every piece on the board
    that is not currently at risk.

    General: the only things it reads are the legal-turn list, whether a
    turn is a capture, and where it lands.
    """
    from lgref.experiments.fastcopy import clone_with_turns

    turns = game.get_all_legal_turns()
    if len(turns) < 2:
        return turns[0] if turns else None
    mover = game.current_player
    at_risk = _rescuable_squares(game, turns, mover, victim_square)
    if not at_risk:
        return turns[0]
    best, fewest = None, None
    for index, turn in enumerate(turns):
        sim, simulated = clone_with_turns(game, turns)
        sim.execute_turn(simulated[index])
        losses = 0
        for square in at_risk:
            if getattr(turn, 'from_sq', None) == square:
                continue
            if _capturable(sim, square, victim_square):
                losses += 1
        if fewest is None or losses < fewest:
            best, fewest = turn, losses
            if not losses:
                break
    return best if best is not None else turns[0]


def _capturable(game, square, victim_square=None):
    victim_square = victim_square or victim_at_destination
    for turn in game.get_all_legal_turns():
        if victim_square(turn) == square:
            return True
    return False


def _rescuable_squares(game, turns, mover, victim_square=None):
    """The mover's squares that an enemy turn can capture AND that the
    piece standing there could move out of to a square no enemy turn
    reaches. Shared by the metric and by its floor so the two cannot
    measure different sets."""
    from lgref.experiments.fastcopy import clone_with_turns

    victim_square = victim_square or victim_at_destination
    passed, _ = clone_with_turns(game, turns)
    passed.current_player = ('black' if mover == 'white' else 'white')
    threatened = set()
    for turn in passed.get_all_legal_turns():
        target = victim_square(turn)
        if target is not None:
            threatened.add(target)

    at_risk = []
    for square in sorted(threatened):
        for escape in [t for t in turns
                       if getattr(t, 'from_sq', None) == square]:
            sim, simulated = clone_with_turns(game, turns)
            sim.execute_turn(simulated[turns.index(escape)])
            if not _capturable(sim, getattr(escape, 'to_sq', None),
                               victim_square):
                at_risk.append(square)
                break
    return at_risk


def rescuable_losses(make_engine, policy, trials=60, seed=0,
                     max_setup=50, victim_square=None):
    """How often the agent leaves a piece to die that it could have saved.

    NO PIECE VALUES ANYWHERE, which is the point. A position counts only
    when all three hold, each read from the move generator:

      1. an enemy turn can capture one of the mover's pieces,
      2. that piece has a legal move to a square no enemy turn can
         reach, so it is RESCUABLE,
      3. after the move actually chosen, an enemy turn still captures
         it.

    Those are exactly the blunders a human reports -- "it left a knight
    hanging when it could have moved it" -- and they are invisible to a
    material count that weighs every piece the same. The harness this
    replaces did exactly that: `strong.material` counts pieces, so a
    knight traded for a pawn scored as zero material change and a run
    of measurements reported no hangs while a reviewer watched knights
    and bishops go.

    Returns `(rescuable, lost, positions)`.
    """
    import random as _random

    from lgref.experiments.fastcopy import clone_with_turns

    victim_square = victim_square or victim_at_destination

    def capturable(game, square):
        return _capturable(game, square, victim_square)

    rng = _random.Random(seed)
    rescuable = lost = positions = 0
    for _trial in range(trials):
        game = make_engine()
        for _ply in range(_setup_plies(rng, max_setup)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        if game.is_game_over():
            continue
        turns = game.get_all_legal_turns()
        if len(turns) < 2:
            continue
        mover = game.current_player

        # Which of the mover's squares can the OPPONENT capture, and
        # which of those could walk away? SHARED with `rescue_oracle`,
        # so the floor is measured on exactly the set the rate counts.
        at_risk = _rescuable_squares(game, turns, mover, victim_square)
        if not at_risk:
            continue
        positions += 1
        rescuable += len(at_risk)

        chosen = policy(game, rng)
        # MATCHED BY DESCRIPTION, not by identity: a policy that calls
        # `get_all_legal_turns()` itself gets fresh Turn objects, and
        # `list.index` then raises. Descriptions are the only stable
        # handle across two generations of the same position.
        from lgref.experiments.mcts import describe
        wanted = describe(chosen)
        index = next((i for i, t in enumerate(turns)
                      if describe(t) == wanted), None)
        if index is None:
            continue
        chosen = turns[index]
        sim, st = clone_with_turns(game, turns)
        sim.execute_turn(st[index])
        for square in at_risk:
            if getattr(chosen, 'from_sq', None) == square:
                continue            # it moved this one
            if capturable(sim, square):
                lost += 1
    return rescuable, lost, positions


def derived_piece_values(engine, samples=24, seed=0):
    """How much each piece identity is worth, DERIVED FROM THE RULES.

    THE METRIC THAT WAS MISSING, and its absence invalidated a long run
    of measurements. The harness used for "does the agent hang
    material" counted pieces and weighted them equally, so a knight and
    a pawn were worth the same -- and a knight traded for a pawn scored
    as ZERO material change. A reviewer kept reporting exactly that
    blunder while the harness reported no hangs at all.

    A hand-written piece table would fix the sensitivity and lose the
    generality, so the value is derived instead: a piece is worth the
    number of distinct turns it generates, averaged over sampled
    positions. That is read from the game's own move generator, needs
    no human input, and transfers to any game -- a piece that can do
    more is worth more, which is as much as the rules themselves say.

    It is a MEASUREMENT INSTRUMENT, never an input to learning. Nothing
    here is given to the learner; it exists so that a claim about
    material can be checked against something that can see the
    difference between a knight and a pawn.
    """
    import collections
    import random as _random

    from lgref.experiments.mcts import describe

    seen = collections.defaultdict(list)
    rng = _random.Random(seed)
    for _trial in range(samples):
        game = engine()
        for _ply in range(rng.randint(0, 40)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        if game.is_game_over():
            continue
        counts = collections.Counter()
        for turn in game.get_all_legal_turns():
            description = describe(turn)
            name = (description[1]
                    if isinstance(description, tuple) and len(description) > 1
                    else None)
            if name is not None:
                counts[name] += 1
        # Per PIECE, not per identity: two rooks generating forty turns
        # between them are worth twenty each.
        present = collections.Counter()
        board = getattr(game, 'board', None)
        if board is None:
            continue
        for row in board.squares:
            for square in row:
                piece = square.piece
                if piece is not None:
                    present[getattr(piece, 'name', None)] += 1
        for name, total in counts.items():
            if present.get(name):
                seen[name].append(total / float(present[name]))
    return dict((name, sum(values) / float(len(values)))
                for name, values in seen.items() if values)


def weighed_material(engine, perspective, values):
    """Material from `perspective`, weighted by `derived_piece_values`."""
    total = 0.0
    board = getattr(engine, 'board', None)
    if board is None:
        return total
    for row in board.squares:
        for square in row:
            piece = square.piece
            if piece is None:
                continue
            colour = getattr(piece, 'color', None)
            if colour not in ('white', 'black'):
                continue
            weight = values.get(getattr(piece, 'name', None), 1.0)
            total += weight if colour == perspective else -weight
    return total


def exchange_opinions(make_engine, evaluate, classify, trials=60,
                      seed=0, max_setup=50):
    """Ask the EVALUATION what it thinks a completed exchange was worth.

    WHY THIS EXISTS, and it is the sharpest lesson in this issue. The
    price of a trade was being computed as arithmetic on two weights:
    minus the piece, plus the pawn. That is only the price if those are
    the ONLY columns that move -- and they were not. Losing a bishop in
    the case study also flips a column that records which forms a queen
    may now take, because a form becomes available once a friendly piece
    of that type has been captured. That column carried the opposite
    sign and cancelled a third of the piece's value, so a trade reported
    as declined by -0.005 was in fact scored as a GAIN of +0.033 -- and
    a human watched the agent take it, twice, in two games.

    No arithmetic on a weight table is trustworthy for this, because
    knowing which columns move is knowing the game. So nothing is
    assumed: the capture and the recapture are EXECUTED on the engine,
    the evaluation is read before and after, and the difference is the
    opinion. If the evaluation improves across losing a piece and
    winning a pawn, the agent is not blundering -- it is obeying.

    `evaluate(state, perspective)` is the searcher's own leaf function.
    `classify(state, turn)` labels an exchange or returns None to skip
    it; that is where a caller's game vocabulary goes, and it is the
    only part that has any.

    Returns `{label: (seen, judged_a_gain)}`.
    """
    import collections
    import random as _random

    from lgref.experiments.fastcopy import clone_with_turns

    rng = _random.Random(seed)
    tally = collections.defaultdict(lambda: [0, 0])
    for _trial in range(trials):
        game = make_engine()
        for _ply in range(_setup_plies(rng, max_setup)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        if game.is_game_over():
            continue
        turns = game.get_all_legal_turns()
        if not turns:
            continue
        mover = game.current_player
        before = evaluate(game, mover)
        for index, turn in enumerate(turns):
            if not getattr(turn, 'is_capture', False):
                continue
            label = classify(game, turn)
            if label is None:
                continue
            square = getattr(turn, 'to_sq', None)
            if square is None:
                continue
            taken, simulated = clone_with_turns(game, turns)
            taken.execute_turn(simulated[index])
            if taken.is_game_over():
                continue
            # A TRADE, not a free capture: the exchange only counts when
            # the opponent can take the capturing piece back on the
            # square it just landed on.
            replies = taken.get_all_legal_turns()
            back = next((i for i, reply in enumerate(replies)
                         if getattr(reply, 'is_capture', False)
                         and getattr(reply, 'to_sq', None) == square),
                        None)
            if back is None:
                continue
            settled, answers = clone_with_turns(taken, replies)
            settled.execute_turn(answers[back])
            after = evaluate(settled, mover)
            entry = tally[label]
            entry[0] += 1
            if after > before:
                entry[1] += 1
    return dict((label, tuple(counts))
                for label, counts in tally.items())


def turn_leverage(make_engine, columns_of, weights, trials=40, seed=0,
                  max_setup=50, sample_turns=24):
    """Which column actually DECIDES a move, measured rather than argued.

    THE QUESTION THIS ANSWERS. An evaluation is a sum of priced columns,
    and a move is chosen by the DIFFERENCE between positions -- so the
    column that decides is not the one with the largest weight, it is
    the one whose contribution MOVES MOST when a turn is played. A piece
    count changes only when something is captured. A dense positional
    count changes on every move, by several units. If its price times
    that swing exceeds a piece's price, it outvotes material on every
    quiet move, and no amount of correct piece values will stop it.

    Measured on the case study, this is exactly what was happening: a
    coverage count moved by 14 units across one exchange at a price of
    0.0057 each, which is +0.080 -- against a bishop priced at 0.067.
    The agent gave up the bishop to buy the coverage and the trade was
    scored as a gain of +0.040. Two reviewers' games showed the same
    move, and the piece values looked fine in every weight table I read.

    `columns_of(state, perspective)` returns the priced columns as the
    evaluation sees them (already normalised, if it normalises).
    Returns `{name: (median_swing, largest_swing, turns_moved)}` where a
    swing is `|weight * (after - before)|` for one legal turn.

    General: legal turns, an injected column function, and a weight map.
    """
    import collections
    import random as _random

    from lgref.experiments.fastcopy import clone_with_turns

    rng = _random.Random(seed)
    swings = collections.defaultdict(list)
    for _trial in range(trials):
        game = make_engine()
        for _ply in range(_setup_plies(rng, max_setup)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        if game.is_game_over():
            continue
        turns = game.get_all_legal_turns()
        if not turns:
            continue
        mover = game.current_player
        before = columns_of(game, mover)
        chosen = (turns if len(turns) <= sample_turns
                  else rng.sample(turns, sample_turns))
        for turn in chosen:
            index = turns.index(turn)
            sim, simulated = clone_with_turns(game, turns)
            sim.execute_turn(simulated[index])
            after = columns_of(sim, mover)
            for name in set(before) | set(after):
                change = abs(weights.get(name, 0.0)
                             * (after.get(name, 0.0)
                                - before.get(name, 0.0)))
                swings[name].append(change)
    out = {}
    for name, values in swings.items():
        values.sort()
        # THE MEDIAN IS TAKEN OVER THE TURNS THAT MOVED IT, not over all
        # of them. Most columns are unchanged by most moves -- a piece
        # count changes only on a capture -- so a median over everything
        # is zero for every column and says nothing. The quantity that
        # matters is "when this column moves, how far", together with
        # how often it moves at all.
        moved = [value_ for value_ in values if value_ > 1e-9]
        middle = moved[len(moved) // 2] if moved else 0.0
        out[name] = (middle, values[-1] if values else 0.0, len(moved))
    return out


def removal_price(make_engine, columns_of, weights, remove, labels,
                  trials=24, seed=0, max_setup=50):
    """What the evaluation charges for losing ONE of something.

    WHY NOT JUST READ THE WEIGHT. Because a weight is not a price when
    columns are collinear, and in the case study they are: a queen may
    take the form of a piece type only once a friendly piece of that
    type has been captured, so "how many bishops I have" and "is bishop
    form available to me" are near-complements -- R-squared 0.98 on each
    other. The learner can only ever see their SUM, and how it splits
    that sum between two weights is decided by the optimiser's path.

    The consequence was a wrong number reported for months. The shipped
    weights list `Bishop` at +0.0669 against `Pawn` at +0.0616, which
    reads as "a bishop is worth 1.1 pawns" -- and a reviewer rightly
    said that cannot be right. It is not right: the other half of the
    pair adds +0.0379, so the evaluation actually charges +0.1048 for a
    bishop, or 1.7 pawns. Every guard and every probe that compared two
    weight names was comparing one arbitrary half against a whole.

    So nothing is read off the table. A piece is TAKEN OFF THE BOARD and
    the evaluation is asked again; the difference is the price, with
    every column that moves included whether or not anyone knew it
    would.

    `remove(game, label, rng)` takes one thing of kind `label` off the
    board and returns True, or False if there is none to take.
    `labels` is the kinds to price. Both are injected: finding a piece
    of a given type is the only part that knows the game.

    Returns `{label: (mean_price, samples)}`, the price being positive
    when losing the thing makes the position worse.
    """
    import random as _random

    from lgref.experiments.fastcopy import clone_with_turns

    rng = _random.Random(seed)
    totals = dict((label, [0.0, 0]) for label in labels)
    for _trial in range(trials):
        game = make_engine()
        for _ply in range(_setup_plies(rng, max_setup)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        if game.is_game_over():
            continue
        turns = game.get_all_legal_turns()
        if not turns:
            continue
        mover = game.current_player
        before = _total(weights, columns_of(game, mover))
        for label in labels:
            damaged, _ = clone_with_turns(game, turns)
            if not remove(damaged, label, rng):
                continue
            after = _total(weights, columns_of(damaged, mover))
            entry = totals[label]
            entry[0] += before - after
            entry[1] += 1
    return dict((label, (total / count if count else float('nan'), count))
                for label, (total, count) in totals.items())


def _total(weights, columns):
    """The linear total, BEFORE the logistic squashes it.

    Prices are compared to each other, and the logistic is monotone but
    not linear -- so reading two prices off probabilities makes their
    ratio depend on where the position happened to sit. The weights live
    in log-odds and that is where a price is comparable.
    """
    return sum(weights.get(name, 0.0) * amount
               for name, amount in columns.items())


def removal_columns(make_engine, columns_of, remove, labels, trials=24,
                    seed=0, max_setup=50):
    """Which COLUMNS move when one of something is taken off the board.

    The companion to `removal_price`, and what makes a price adjustable
    without anyone deciding which columns belong to which piece. A
    column that moves for exactly ONE label is that label's own; a
    column that moves for all of them -- a coverage count does -- is
    shared and must not be rescaled when one label's price is corrected.
    Both facts are read off this table instead of being asserted.

    Returns `{label: {column: mean_change}}`, the change measured as
    `after - before` on the columns as the evaluation sees them.
    """
    import collections
    import random as _random

    from lgref.experiments.fastcopy import clone_with_turns

    rng = _random.Random(seed)
    sums = dict((label, collections.defaultdict(float))
                for label in labels)
    counts = dict((label, 0) for label in labels)
    for _trial in range(trials):
        game = make_engine()
        for _ply in range(_setup_plies(rng, max_setup)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        if game.is_game_over():
            continue
        turns = game.get_all_legal_turns()
        if not turns:
            continue
        mover = game.current_player
        before = columns_of(game, mover)
        for label in labels:
            damaged, _ = clone_with_turns(game, turns)
            if not remove(damaged, label, rng):
                continue
            after = columns_of(damaged, mover)
            counts[label] += 1
            for name in set(before) | set(after):
                change = after.get(name, 0.0) - before.get(name, 0.0)
                if change:
                    sums[label][name] += change
    out = {}
    for label in labels:
        total = counts[label]
        out[label] = (dict((name, value_ / total)
                           for name, value_ in sums[label].items())
                      if total else {})
    return out


def exclusive_columns(table):
    """For each label, the columns that move for IT AND NOTHING ELSE.

    Those are the columns that carry that label's own price, so they are
    the ones to rescale when a price is corrected. Everything shared --
    coverage, mobility, anything positional -- is left out, because
    rescaling it would corrupt the other labels' prices along with it.
    """
    owners = {}
    for label, columns in table.items():
        for name in columns:
            owners.setdefault(name, set()).add(label)
    return dict((label, sorted(name for name in columns
                               if len(owners[name]) == 1))
                for label, columns in table.items())


def free_leverage(make_engine, columns_of, weights, is_tactical=None,
                  trials=40, seed=0, max_setup=50, sample_turns=24):
    """How far can a column move on a turn that CAPTURES NOTHING?

    WHY THIS IS THE DANGEROUS KIND OF LEVERAGE. `turn_leverage` asks how
    far a column moves on any turn; this asks how far it moves on a FREE
    one. A column the opponent can swing by more than a piece is worth,
    using a turn that costs them nothing, is not a durable property of a
    position -- it is a lever, and weighting it makes the agent spend
    real material to stop the opponent pulling it.

    Measured on the case study, this is what produced four of the
    blunders a reviewer reported. `RoyalForm:Rook` -- "my royal queen is
    in rook form" -- carries +0.1467, and the opponent can cancel the
    differential with a TRANSFORMATION, which is a non-spatial action
    that captures nothing. So the search saw a phantom threat worth 2.4
    pawns on every opponent turn, and chose to be captured instead:
    asked to choose between a line where it loses a pawn and one where
    the opponent transforms, it priced the pawn at -0.056 and the
    transformation at -0.088 and gave away the pawn. Zeroing that one
    family fixed the pawn gifts and made it recapture a bishop it had
    been declining to recapture.

    A piece count cannot be moved this way: taking a piece off the board
    requires a capture, which is by definition not free. That asymmetry
    is the whole point, and it is why this is worth measuring separately.

    Returns `{name: (median_swing, largest_swing, turns_counted)}` over
    non-tactical turns only.
    """
    import collections
    import random as _random

    from lgref.experiments.fastcopy import clone_with_turns
    from lgref.experiments.search import generic_is_tactical

    tactical = is_tactical or generic_is_tactical
    rng = _random.Random(seed)
    swings = collections.defaultdict(list)
    for _trial in range(trials):
        game = make_engine()
        for _ply in range(_setup_plies(rng, max_setup)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        if game.is_game_over():
            continue
        turns = game.get_all_legal_turns()
        free = [turn for turn in turns if not tactical(turn)]
        if not free:
            continue
        mover = game.current_player
        before = columns_of(game, mover)
        chosen = (free if len(free) <= sample_turns
                  else rng.sample(free, sample_turns))
        for turn in chosen:
            index = turns.index(turn)
            sim, simulated = clone_with_turns(game, turns)
            sim.execute_turn(simulated[index])
            after = columns_of(sim, mover)
            for name in set(before) | set(after):
                change = abs(weights.get(name, 0.0)
                             * (after.get(name, 0.0)
                                - before.get(name, 0.0)))
                if change:
                    swings[name].append(change)
    out = {}
    for name, values in swings.items():
        values.sort()
        out[name] = (values[len(values) // 2], values[-1], len(values))
    return out


def lever_columns(free, prices):
    """Columns a free turn can swing by more than the cheapest piece.

    THE CRITERION IS MEASURED, NOT CHOSEN. `prices` comes from
    `removal_price`, so the bar is "this column moves more, for free,
    than the least valuable thing on the board costs" -- in the case
    study's own units, derived from its own learned evaluation. Nothing
    here names a piece or picks a threshold.

    A column over that bar lets the opponent manufacture a threat
    without spending anything, and an agent that believes the threat
    will pay material to answer it.
    """
    floor = min((price for price, samples in prices.values()
                 if samples and price > 0.0), default=None)
    if floor is None:
        return []
    return sorted(name for name, (_median, largest, _n) in free.items()
                  if largest > floor)


def avoidable_losses(make_engine, policy, trials=60, seed=0,
                     max_setup=50, victim_square=None):
    """How often a QUIET move puts a piece where it can be taken.

    THE OTHER HALF OF THE BLUNDER, and the half that was not being
    measured. `rescuable_losses` asks whether the agent SAVED a piece
    that was already in danger. It says nothing about walking a piece
    INTO danger, because the piece was safe before the move and so never
    entered the at-risk set.

    That is most of what a reviewer actually reported: a pawn pushed onto
    a defended square, then another, then another. Measured on the
    shipped weights, the two instruments disagree completely -- ablating
    the family that caused those pushes moved `rescuable_losses` from
    49.4% to 50.0%, which is nothing, while winning its match 11-5. The
    rate was flat because it was measuring the wrong half.

    A position counts when all four hold, each read from the move
    generator and with NO PIECE VALUES anywhere:

      1. the chosen turn is QUIET -- it takes nothing. A trade may be
         good or bad and this instrument cannot tell, so it declines to
         guess;
      2. the piece it moves is NOT already capturable where it stands,
         so this is not the rescue case;
      3. after the move, an enemy turn can capture it at its
         destination;
      4. the same piece had another legal destination that an enemy turn
         could NOT capture -- so the loss was avoidable.

    Returns `(opportunities, avoidable, positions)`, where an
    opportunity is a position in which the mover had at least one quiet
    move for a currently-safe piece.
    """
    import random as _random

    from lgref.experiments.fastcopy import clone_with_turns
    from lgref.experiments.mcts import describe
    from lgref.experiments.search import generic_is_tactical

    victim_square = victim_square or victim_at_destination
    rng = _random.Random(seed)
    opportunities = avoidable = positions = 0
    for _trial in range(trials):
        game = make_engine()
        for _ply in range(_setup_plies(rng, max_setup)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        if game.is_game_over():
            continue
        turns = game.get_all_legal_turns()
        if len(turns) < 2:
            continue
        mover = game.current_player

        def safe_after(index, square):
            sim, simulated = clone_with_turns(game, turns)
            sim.execute_turn(simulated[index])
            return not _capturable(sim, square, victim_square)

        # Which of the mover's squares can the opponent already take?
        # A piece standing on one of those is the RESCUE case and is
        # excluded here, so the two instruments do not double-count.
        at_risk = set()
        passed, _ = clone_with_turns(game, turns)
        passed.current_player = ('black' if mover == 'white' else 'white')
        for turn in passed.get_all_legal_turns():
            target = victim_square(turn)
            if target is not None:
                at_risk.add(target)

        quiet = [index for index, turn in enumerate(turns)
                 if not generic_is_tactical(turn)
                 and getattr(turn, 'from_sq', None) is not None
                 and getattr(turn, 'to_sq', None) is not None
                 and getattr(turn, 'from_sq') not in at_risk]
        if not quiet:
            continue
        positions += 1

        chosen = policy(game, rng)
        wanted = describe(chosen)
        index = next((i for i, turn in enumerate(turns)
                      if describe(turn) == wanted), None)
        if index is None or index not in quiet:
            # IT DID SOMETHING ELSE -- captured, or moved a piece that
            # was already in danger. Neither is this instrument's
            # question, so the position is not counted at all. Counting
            # it in the denominator was the first version's bug, and it
            # diluted random play's rate to 2.7%: a uniform mover picks
            # a capture or a rescue most of the time, and each of those
            # looked like a quiet move that went somewhere safe.
            continue
        # THE DENOMINATOR IS CONDITIONAL: of the quiet moves it actually
        # made with a safe piece, how many put the piece where it could
        # be taken although somewhere safe was available.
        opportunities += 1
        start = getattr(turns[index], 'from_sq', None)
        landing = getattr(turns[index], 'to_sq', None)
        if safe_after(index, landing):
            continue
        # IT COULD HAVE GONE SOMEWHERE SAFE, which is what makes the
        # loss avoidable rather than forced.
        for other in quiet:
            if other == index:
                continue
            if getattr(turns[other], 'from_sq', None) != start:
                continue
            if safe_after(other, getattr(turns[other], 'to_sq', None)):
                avoidable += 1
                break
    return opportunities, avoidable, positions


def solve(game, memo=None, depth=0, cap=60):
    """Exact value of a position for the player to move, by enumeration.

    WHY A SOLVER BELONGS IN THE INSTRUMENTS. A deep search reads
    terminal states directly, so on a small game it plays well with an
    evaluation of ALL ZEROS -- measured at 82.5% against a uniform mover
    on nim and 98.6% on tic-tac-toe. That makes "the agent beats random"
    nearly silent about whether anything was LEARNED, and I reported it
    as though it were not.

    The quantity that is not silent is the OPTIMAL-ACTION RATE: how
    often the evaluation, consulted directly, picks a move that exact
    play also picks. The search cannot flatter it, because the search is
    not involved.

    General over the protocol -- `get_all_legal_turns`, `execute_turn`,
    `copy`, `is_game_over`, `winner`, `current_player` -- and memoised
    on the state the game itself reports. Returns a value in {0, 0.5, 1}
    from the mover's side. Only usable where the tree is small enough to
    enumerate, which is the point: that is where truth is available.
    """
    memo = {} if memo is None else memo
    if game.is_game_over() or depth >= cap:
        winner = getattr(game, 'winner', None)
        if winner is None:
            return 0.5
        return 1.0 if winner == game.current_player else 0.0
    turns = game.get_all_legal_turns()
    if not turns:
        return 0.0          # no legal turn is a loss for the mover
    key = _position_key(game)
    if key is not None and key in memo:
        return memo[key]
    best = 0.0
    for turn in turns:
        child = game.copy()
        child.execute_turn(turn)
        value = solve(child, memo, depth + 1, cap)
        # The child reports from ITS mover's side; flip when it changed.
        if getattr(child, 'current_player', None) != game.current_player:
            value = 1.0 - value
        if value > best:
            best = value
            if best >= 1.0:
                break
    if key is not None:
        memo[key] = best
    return best


def optimal_turns(game, memo=None, cap=60):
    """Every turn that achieves the position's exact value."""
    turns = game.get_all_legal_turns()
    if not turns:
        return []
    memo = {} if memo is None else memo
    scored = []
    for turn in turns:
        child = game.copy()
        child.execute_turn(turn)
        value = solve(child, memo, 1, cap)
        if getattr(child, 'current_player', None) != game.current_player:
            value = 1.0 - value
        scored.append((value, turn))
    best = max(value for value, _turn in scored)
    return [turn for value, turn in scored if value >= best - 1e-9]


def _position_key(game):
    """A hashable state, from whatever the game exposes.

    Prefers the game's own hash; falls back to its fluent set. Returns
    None when neither is available, which disables memoisation rather
    than risking a wrong cache hit.
    """
    board = getattr(game, 'board', None)
    if board is not None and hasattr(board, 'get_state_hash'):
        try:
            return ('hash', board.get_state_hash(game.current_player))
        except Exception:
            return None
    state = getattr(game, 'state', None)
    if state is None:
        return None
    try:
        return (frozenset(state), game.current_player)
    except TypeError:
        return None


def optimal_rate(make_game, policy, trials=40, seed=0, max_setup=12,
                 cap=60):
    """How often `policy` picks a move exact play also picks.

    THE INSTRUMENT THE SEARCH CANNOT FLATTER. Positions are reached by
    random play, then both the policy and the solver are asked, and the
    CHANCE baseline -- the share of legal turns that happen to be
    optimal -- is returned beside the rate, because a position where
    every move is optimal is not evidence of anything.
    """
    import random as _random

    from lgref.experiments.mcts import describe

    rng = _random.Random(seed)
    hits = asked = 0
    chance = 0.0
    for _trial in range(trials):
        game = make_game()
        for _ply in range(_setup_plies(rng, max_setup)):
            turns = game.get_all_legal_turns()
            if not turns or game.is_game_over():
                break
            game.execute_turn(rng.choice(turns))
        if game.is_game_over():
            continue
        turns = game.get_all_legal_turns()
        if len(turns) < 2:
            continue
        best = optimal_turns(game, cap=cap)
        if not best or len(best) == len(turns):
            continue        # nothing to get wrong
        asked += 1
        chance += len(best) / float(len(turns))
        wanted = describe(policy(game, rng))
        if any(describe(turn) == wanted for turn in best):
            hits += 1
    return (hits / float(asked) if asked else float('nan'),
            chance / asked if asked else float('nan'), asked)
