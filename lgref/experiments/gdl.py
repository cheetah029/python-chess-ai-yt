"""Play a game given only its GDL, with features named by the GDL.

WHY THIS EXISTS, and it is the project's whole claim. The agent that
plays the case study reads a HAND-WRITTEN extractor: someone decided
that `Bishop`, `RoyalForm:Rook` and `FormAvailable:bishop` were the
quantities worth counting, and keyed them on that engine's own Python
attributes. The same is true of the m,n,k extractor. So "the framework
handles games it has not seen" was true of the LEARNER and the SEARCH
and not of the thing between them.

A reviewer put the acceptance test plainly: hand it a GDL it has never
seen, and it should be competent. That cannot be met by a module
somebody writes per game, so this one is written per DIALECT instead.

WHERE THE NAMES COME FROM. The GDL's own symbols. A state is a set of
ground fluents -- `at(white, 3)`, `control(first)`, `pile(5)` -- and
every feature here is named after the relation and arguments it was
read from. Nothing is invented and nothing is supplied.

THE THREE THINGS A FLUENT CONTRIBUTES, each derived rather than chosen:

  OWNERSHIP   a fluent whose arguments contain exactly one role name
              belongs to that role; anything else belongs to nobody.
              That is what lets `differentials` make the evaluation
              antisymmetric, which TD requires. `at(white, 3)` is
              white's; `pile(5)` is the game's.
  PRESENCE    the relation name, counted. "How many `at` fluents do I
              have" is a question worth asking before knowing what
              `at` means.
  MAGNITUDE   an argument that is a NUMBER is kept as a number, under
              `relation@index`. This is the one piece of structure
              that is read rather than enumerated, and it is what
              turns `at(white, 3)` into "white has advanced three"
              instead of eight unrelated indicator columns. A
              non-numeric argument becomes an indicator instead,
              because nothing orders it.

WHAT THIS CANNOT YET DO, stated because the gap matters. A game that
names its pieces with constants UNRELATED to its role names -- standard
tic-tac-toe, where the roles are `xplayer` and `oplayer` but the board
holds `x` and `o` -- gets no ownership from the rule above, so its
board becomes neutral and the evaluation loses its antisymmetry. Fixing
that means binding constants to roles through the GOAL rules, which is
a real inference and not a convention. It is the next step, not a
footnote.
"""


def _is_number(value):
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _flatten(term):
    """A fluent as `(relation, [arguments])`, arguments as strings.

    GDL terms arrive as nested tuples. Nesting is flattened in order,
    because a nested argument is still an argument -- `take(2)` carries
    its 2 whether or not the parser wrapped it.
    """
    if not isinstance(term, (tuple, list)) or not term:
        return str(term), []
    relation = str(term[0])
    arguments = []

    def walk(value):
        if isinstance(value, (tuple, list)):
            for item in value:
                walk(item)
        else:
            arguments.append(str(value))

    for item in term[1:]:
        walk(item)
    return relation, arguments


def features(game, roles=None):
    """`{(owner, name): value}` for a GDL state. The extractor protocol.

    A SHARED RESOURCE BELONGS TO THE PLAYER TO MOVE, which is the one
    judgement in here and it was forced by a measurement. `differentials`
    EXCLUDES neutral owners, and rightly: a piece belonging to nobody
    scored against the mover gives the same sign to both players, which
    is a constant dressed as a feature.

    But nim's whole state is `pile(5)`, which belongs to nobody -- so
    the first version of this extractor handed the learner one usable
    feature and the agent lost to a uniform mover 28-92. Attributing a
    shared quantity to the SIDE TO MOVE fixes both halves at once: it
    survives `differentials`, it stays antisymmetric (the same state
    read from the other side gives the negation), and the meaning is
    right -- a pile of five matters differently depending on whose turn
    it is.

    `game` is anything with a `state` of ground fluents and a `roles`
    list -- `GdlGame` below, or a bare `GGPGame`.
    """
    import collections

    known = set(str(role) for role in (roles if roles is not None
                                       else getattr(game, 'roles', ())))
    state = getattr(game, 'state', None)
    if state is None:
        return {}
    shared = getattr(game, 'current_player', None)
    if shared is None:
        shared = sorted(known)[0] if known else 'none'
    counts = collections.Counter()
    for term in state:
        relation, arguments = _flatten(term)
        owners = [item for item in arguments if item in known]
        owner = owners[0] if len(owners) == 1 else shared
        counts[(owner, relation)] += 1
        position = 0
        for item in arguments:
            if item in known:
                continue        # the role is the owner, not a value
            if _is_number(item):
                # BOTH READINGS, because the rules do not say which one
                # the game wants and the learner can be left to find
                # out. The magnitude orders positions -- a token on
                # square 5 is further along than one on square 3. The
                # indicator does not, and it is the only way to express
                # a quantity whose value is not monotone in its size:
                # nim is decided by the pile's PARITY, which no linear
                # weight on the pile's size can represent.
                counts[(owner, '{0}@{1}'.format(relation, position))] += \
                    float(item)
                counts[(owner, '{0}@{1}is{2}'.format(relation, position,
                                                     item))] += 1
            else:
                counts[(owner, '{0}@{1}={2}'.format(relation, position,
                                                    item))] += 1
            position += 1
    return dict(counts)


class GdlGame(object):
    """A `GGPGame` behind the protocol the learner and search expect.

    THE TRANSLATION IS THE WHOLE POINT. `GGPGame` speaks
    `legal_moves(role)` / `step({role: move})` / `goal(role)`, because
    GDL is simultaneous-move by construction: every role submits a move
    on every step and a turn-taking game is expressed by giving the
    waiting roles nothing but `noop`.

    The learner wants `current_player`, `get_all_legal_turns()` and
    `execute_turn(turn)`. The player TO MOVE is therefore derived, not
    declared: it is the role with a real choice, meaning more than one
    legal move or a single move that is not a no-op. When no role has a
    choice the first role is used, which keeps a degenerate state from
    hanging.

    `winner` reads the GDL's own `goal`: the role with the strictly
    highest goal value, or None when they tie -- which is a draw, and
    the learner needs to be able to tell a draw from a truncation.
    """

    #: The move a GDL game gives a role that is not to move. Not a
    #: convention this module invents -- it is what the test games and
    #: the case study's own description use, and a role whose only
    #: legal move is this one has no choice to make.
    IDLE = ('noop', 'wait')

    def __init__(self, ggp, max_turns=None):
        self.ggp = ggp
        self.roles = [str(role) for role in ggp.roles]
        self.max_turns = max_turns
        self.turn_number = 0

    # ---- protocol ----------------------------------------------------

    @property
    def state(self):
        return self.ggp.state

    @property
    def current_player(self):
        """The role to move, derived three ways in order of directness.

        AT A TERMINAL STATE THE FIRST RULE FAILS, and that was a real
        bug rather than a corner. When the game is over every role is
        left with nothing but an idle move, so the first rule fell
        through to `roles[0]` -- which is the right answer only half the
        time, and `search._leaf` scores a finished position as
        `winner == current_player`. So the agent read half of all
        terminal positions with the sign inverted. On nim, where every
        line ends within five plies, that is most of the tree: it
        scored 35% against a uniform mover while a correct reading of
        the same weights wins.

        The second rule is a TURN MARKER, found by shape rather than by
        name: a relation that holds of exactly one role and of no other
        argument. GDL games conventionally call it `control`, but
        nothing here depends on that spelling -- a game that calls it
        `turn` or `whose_move` is read the same way.
        """
        for role in self.roles:
            moves = self._moves(role)
            if len(moves) > 1:
                return role
            if len(moves) == 1 and not self._is_idle(moves[0]):
                return role
        marker = self._turn_marker()
        if marker is not None:
            return marker
        return self.roles[0] if self.roles else None

    def _turn_marker(self):
        """The role named by a unary fluent that holds of one role only."""
        known = set(self.roles)
        holders = {}
        for term in self.state:
            relation, arguments = _flatten(term)
            if len(arguments) != 1 or arguments[0] not in known:
                continue
            holders.setdefault(relation, set()).add(arguments[0])
        for _relation, roles in sorted(holders.items()):
            if len(roles) == 1:
                return sorted(roles)[0]
        return None

    def get_all_legal_turns(self):
        if self.is_game_over():
            return []
        mover = self.current_player
        if mover is None:
            return []
        return [(mover, move) for move in self._moves(mover)]

    def execute_turn(self, turn):
        """Apply one role's choice; every other role submits an idle move.

        A role with several real moves while another is moving would be
        a genuinely simultaneous game, which this wrapper does not
        claim to handle -- it takes that role's first legal move and the
        docstring says so rather than pretending.
        """
        mover, move = turn
        submitted = {}
        for role in self.roles:
            if role == mover:
                submitted[role] = move
                continue
            options = self._moves(role)
            idle = [option for option in options if self._is_idle(option)]
            submitted[role] = (idle or options or [None])[0]
        self.ggp.step(submitted)
        self.turn_number += 1

    def is_game_over(self):
        if self.max_turns is not None and self.turn_number >= self.max_turns:
            return True
        return bool(self.ggp.is_terminal())

    @property
    def winner(self):
        if not self.ggp.is_terminal():
            return None
        scores = {}
        for role in self.roles:
            try:
                scores[role] = self.ggp.goal(role)
            except Exception:
                scores[role] = None
        usable = dict((role, value) for role, value in scores.items()
                      if value is not None)
        if not usable:
            return None
        best = max(usable.values())
        leaders = [role for role, value in usable.items() if value == best]
        return leaders[0] if len(leaders) == 1 else None

    def copy(self):
        import copy as _copy

        clone = GdlGame.__new__(GdlGame)
        clone.ggp = _copy.deepcopy(self.ggp)
        clone.roles = list(self.roles)
        clone.max_turns = self.max_turns
        clone.turn_number = self.turn_number
        return clone

    # ---- helpers ------------------------------------------------------

    def _moves(self, role):
        try:
            return list(self.ggp.legal_moves(role))
        except Exception:
            return []

    def _is_idle(self, move):
        relation, _arguments = _flatten(move)
        return relation in self.IDLE


def load(path, max_turns=None):
    """A playable game from a GDL file, in either dialect."""
    import os
    import sys

    here = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    source = os.path.join(here, 'src')
    if source not in sys.path:
        sys.path.insert(0, source)
    from ggp.game import GGPGame

    return GdlGame(GGPGame.from_file(path), max_turns=max_turns)
