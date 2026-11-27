"""Reference variants and behavioural probes for the Paper A benchmark.

WHAT THESE ARE. A REFERENCE VARIANT is a prespecified change to a game,
written as exact text edits to its description: "disable diagonal
captures in Breakthrough". A PROBE is an executable statement of what
that change must and must not do: a state, optionally a joint move
played from it, and the expected legal moves, ending, payoff or facts.

    a  with an enemy pawn on the diagonal destination, the capture is
       illegal                                        (role: changed)
    b  with that destination empty, the diagonal move is still legal
                                                      (role: unchanged)

Every probe must hold in the reference variant. A `changed` probe must
FAIL in the unmodified game -- otherwise it does not test the change --
and an `unchanged` probe must hold there too, so it guards against
collateral damage. `check_references` enforces all three, and the tests
run it, so a probe that stops discriminating fails the build.

WHO WROTE THEM. The variants and probes are written by Claude, the same
author as the identification method, from the rules each game states.
That is a circularity the user must review: an author who knows how the
method groups statements could, even without meaning to, choose changes
it handles well. They are kept here, in `lgref/bench/variants/`, outside
`lgref/identify/`, and nothing in the method reads them.

HOW A CANDIDATE IS SCORED. `run_probes(text, change)` evaluates one
change's probes against ANY description -- the reference variant, the
unmodified game, or an intervention a grouping method generated -- and
reports each probe as passed or failed with the reason. A description
that does not load fails every probe, with that reason.
"""

import os

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
VARIANT_DIR = os.path.join(HERE, 'variants')

ROLES = ('changed', 'unchanged')


class Change(object):
    __slots__ = ('game', 'id', 'summary', 'edits', 'probes', 'kind')

    def __init__(self, game, spec):
        self.game = game
        self.id = spec['id']
        self.summary = spec['summary']
        self.kind = spec.get('kind', 'targeted')
        self.edits = spec.get('edits', [])
        self.probes = spec['probes']

    def __repr__(self):
        return '<Change {}:{}>'.format(self.game, self.id)


def load_variants(game):
    """(metadata, [Change]) for one game, from its YAML file."""
    path = os.path.join(VARIANT_DIR, game + '.yaml')
    with open(path) as handle:
        data = yaml.safe_load(handle)
    if data.get('game') != game:
        raise ValueError('{} declares game {!r}'.format(path,
                                                        data.get('game')))
    return data, [Change(game, spec) for spec in data['changes']]


def games_with_variants():
    return sorted(name[:-5] for name in os.listdir(VARIANT_DIR)
                  if name.endswith('.yaml'))


def apply_edits(text, edits):
    """The description with each edit applied.

    Each edit's `replace` text (or `remove`, which replaces with nothing)
    must occur EXACTLY ONCE, so an edit can never silently miss after the
    game is edited, nor hit two places.
    """
    for edit in edits:
        if 'remove' in edit:
            old, new = edit['remove'], ''
        else:
            old, new = edit['replace'], edit['with']
        count = text.count(old)
        if count != 1:
            raise ValueError('edit expects {!r} exactly once, found {}'
                             .format(old, count))
        text = text.replace(old, new)
    return text


def variant_text(base_text, change):
    return apply_edits(base_text, change.edits)


# ---- terms -------------------------------------------------------------

def _term(text):
    """One ground term written in infix, as the game engine holds it."""
    from ggp.infix import parse_infix
    forms = parse_infix(str(text))
    if len(forms) != 1:
        raise ValueError('expected one term, got {!r}'.format(text))
    term = forms[0]
    if isinstance(term, tuple) and len(term) == 1:
        return term[0]
    return term


def _terms(text):
    """Space-separated ground terms (no term contains a space)."""
    return [_term(t) for t in str(text).split()]


def _state(facts):
    return set(_terms(facts))


def _role_and(text):
    """'white move(2,2,3,3)' -> ('white', 'move(2,2,3,3)')."""
    role, _, rest = str(text).partition(' ')
    return role, rest.strip()


# ---- evaluation --------------------------------------------------------

def _open(text):
    from ggp.game import GGPGame
    return GGPGame(text)


def _goal_values(game, role):
    from lgref.bench.wellformed import goal_values
    return goal_values(game, role)


def _check(game, expectation):
    """(ok, reason) for one expectation in the game's current state."""
    if 'legal' in expectation:
        role, move = _role_and(expectation['legal'])
        want = bool(expectation.get('is', True))
        got = _term(move) in game.legal_moves(role)
        return got == want, 'legal({}, {}) is {}'.format(role, move, got)
    if 'terminal' in expectation:
        want = bool(expectation['terminal'])
        got = game.is_terminal()
        return got == want, 'terminal is {}'.format(got)
    if 'goal' in expectation:
        role, value = _role_and(expectation['goal'])
        got = _goal_values(game, role)
        return got == {int(value)}, 'goal({}) is {}'.format(role,
                                                            sorted(got))
    if 'holds' in expectation:
        want = bool(expectation.get('is', True))
        got = _term(expectation['holds']) in game.state
        return got == want, '{} holds: {}'.format(expectation['holds'], got)
    if 'moves' in expectation:
        role = expectation['moves']
        want = sorted(_terms(expectation['are']), key=repr)
        got = sorted(game.legal_moves(role), key=repr)
        return got == want, 'legal moves of {}: {}'.format(role, got)
    raise ValueError('unknown expectation {!r}'.format(expectation))


def run_probe(game, probe):
    """(passed, reason) for one probe on an opened game."""
    game.state = _state(probe['state'])
    play = probe.get('play')
    if play:
        moves = dict((role, _term(move)) for role, _, move in
                     (item.partition('=') for item in str(play).split()))
        for role, move in sorted(moves.items()):
            if move not in game.legal_moves(role):
                return False, 'cannot play {}: not legal for {}'.format(
                    move, role)
        game.step(moves)
    for expectation in probe['expect']:
        ok, reason = _check(game, expectation)
        if not ok:
            return False, reason
    return True, 'ok'


def run_probes(text, change):
    """{probe id: (passed, reason)} for every probe of `change`."""
    try:
        game = _open(text)
    except Exception as exc:                       # noqa: BLE001
        reason = 'does not load: {}: {}'.format(type(exc).__name__, exc)
        return {p['id']: (False, reason) for p in change.probes}
    out = {}
    for probe in change.probes:
        try:
            out[probe['id']] = run_probe(game, probe)
        except Exception as exc:                   # noqa: BLE001
            out[probe['id']] = (False, 'error: {}: {}'.format(
                type(exc).__name__, exc))
    return out


def check_references(game_name, base_text=None):
    """Problems with one game's reference variants, as strings.

      - an edit that does not apply exactly once
      - a probe that fails in its own reference variant
      - a `changed` probe that PASSES in the unmodified game
      - an `unchanged` probe that fails in the unmodified game
      - a change with no `changed` probe, unless it is declared a
        `no_effect` change (its correct effect is none at all)
    """
    from lgref.bench.catalog import game_path

    if base_text is None:
        with open(game_path(game_name)) as handle:
            base_text = handle.read()
    _meta, changes = load_variants(game_name)
    problems = []
    seen = set()
    for change in changes:
        if change.id in seen:
            problems.append('{}: duplicate change id'.format(change.id))
        seen.add(change.id)
        roles = [p.get('role') for p in change.probes]
        for probe, role in zip(change.probes, roles):
            if role not in ROLES:
                problems.append('{}/{}: role {!r} is not one of {}'.format(
                    change.id, probe['id'], role, ROLES))
        if change.kind == 'no_effect':
            if 'changed' in roles:
                problems.append('{}: a no_effect change cannot have a changed '
                                'probe'.format(change.id))
        elif 'changed' not in roles:
            problems.append('{}: no changed probe, so nothing tests the '
                            'change'.format(change.id))
        try:
            text = variant_text(base_text, change)
        except ValueError as exc:
            problems.append('{}: {}'.format(change.id, exc))
            continue
        on_variant = run_probes(text, change)
        on_base = run_probes(base_text, change)
        for probe in change.probes:
            pid = probe['id']
            ok, reason = on_variant[pid]
            if not ok:
                problems.append('{}/{}: fails in the reference variant: {}'
                                .format(change.id, pid, reason))
            base_ok, base_reason = on_base[pid]
            if probe.get('role') == 'changed' and base_ok:
                problems.append('{}/{}: a changed probe that also holds in '
                                'the unmodified game tests nothing'.format(
                                    change.id, pid))
            if probe.get('role') == 'unchanged' and not base_ok:
                problems.append('{}/{}: an unchanged probe that fails in '
                                'the unmodified game: {}'.format(
                                    change.id, pid, base_reason))
    return problems
