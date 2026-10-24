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


def infer_ownership(make_game, games=12, plies=60, seed=0):
    """Which constants belong to which role, learned by WATCHING PLAY.

    THE GAP THIS CLOSES, measured. A game whose board constants are
    unrelated to its role names -- tic-tac-toe, roles `xplayer` and
    `oplayer`, marks `x` and `o` -- gave every `cell` fluent to the side
    to move, which flips every ply, so the board was noise.
    Optimal-action rate at one ply against exact play: 60.9% for the
    GDL-derived names, and 60.9% for a FLAT evaluation over the same
    names -- the learning contributed exactly nothing. The hand-written
    m,n,k vocabulary scored 93.9% on the same game against its own flat
    control of 63.3%.

    NO PARSER. The rules bind the constant already --
    `next(cell(M,N,x)) :- does(xplayer, mark(M,N))` -- but reading that
    means analysing rule bodies, and a game can bind a constant without
    saying so in any single rule. So the game is PLAYED and the
    transitions are watched.

    THE RULE IS A PARTITION, NOT UNANIMITY, and the difference is the
    whole correctness of this function. "Only one role ever adds this
    constant" sounds right and is far too weak: nim starts at five with
    `first` to move, so a pile of FOUR is only ever produced by first --
    a true statement about the game that means nothing about ownership.
    Corridor is the same: white starts on square 0, so squares 1 and 2
    are only ever reached by white. Both bindings were stable at eight,
    forty and a hundred and fifty games, so they are structure rather
    than sample noise, and more data would never have removed them.

    What distinguishes a real binding is that the constant DISCRIMINATES
    BETWEEN ROLES at a fixed place in a fixed relation: every role that
    writes there uses its own constants and no other role's. `cell`
    position 2 is written `x` by one role and `o` by the other, which is
    a partition. `pile` position 0 is written `3` by both, which is not.
    Checked on all three test games, the rule binds tic-tac-toe's marks
    and nothing in nim or corridor -- which is the right answer in each
    case.

    No threshold anywhere: a partition either holds or it does not.

    Returns `{constant: role}`.
    """
    import collections
    import random as _random

    rng = _random.Random(seed)
    #: (relation, position) -> {constant: {roles that wrote it}}
    written = collections.defaultdict(lambda: collections.defaultdict(set))
    for _index in range(games):
        game = make_game()
        known = set(game.roles)
        before = set(game.state)
        for _ply in range(plies):
            if game.is_game_over():
                break
            turns = game.get_all_legal_turns()
            if not turns:
                break
            mover = game.current_player
            game.execute_turn(rng.choice(turns))
            after = set(game.state)
            for term in sorted(after - before, key=repr):
                relation, arguments = _flatten(term)
                position = 0
                for item in arguments:
                    if item in known:
                        continue
                    written[(relation, position)][item].add(mover)
                    position += 1
            before = after

    out = {}
    for _slot, constants in sorted(written.items(), key=lambda kv: str(kv[0])):
        owners = {}
        for item, roles in constants.items():
            if len(roles) != 1:
                owners = None           # written by several roles
                break
            owners[item] = sorted(roles)[0]
        if not owners or len(set(owners.values())) < 2:
            # Either some constant is shared, or every constant here
            # belongs to the same role -- which is the nim case, and
            # tells us about the opening rather than about ownership.
            continue
        out.update(owners)
    return out


#: Relations every GDL file has because the DIALECT defines them.
#: Everything else a file declares is a concept its author named, and
#: those are the ones worth counting.
GDL_KEYWORDS = frozenset((
    'role', 'init', 'next', 'legal', 'does', 'goal', 'terminal', 'true',
    'distinct', 'base', 'input', 'not', 'or', 'succ'))


def derived_relations(game, cap=4):
    """The relations the GAME defines, with the arity each is used at.

    OFF BY DEFAULT, because it was measured and it did not help: on
    tic-tac-toe the optimal-action rate went from 69.4% to 67.3% with
    these switched on. The machinery is kept because the reasoning that
    motivated it is still right and the gap it was aimed at is real --
    but the diagnosis was wrong, and that is worth recording precisely.

    WHAT I EXPECTED. The hand-written m,n,k extractor reaches 93.9%
    optimal at one ply against this one's 69.4%, and no linear model
    over per-cell counts can represent two-in-a-row-with-the-third-
    empty. A line is a conjunction across cells, so reading the game's
    own `line` relation should supply it.

    WHY THAT WAS WRONG. `line(x)` is only true once the game is already
    WON. It is a terminal indicator, not a measure of progress. What
    the hand-written extractor counts is `Line:j` -- lines holding
    exactly j of my marks and none of yours -- which is the PARTIAL
    SATISFACTION of the win condition, and the GDL never states it. Its
    own docstring says so: "`Line:k-1` is one move from winning, which
    no one told it; it falls out of reading the win condition."

    So the hand-written advantage is not a NAME the GDL lacks. It is a
    CONSTRUCTED concept: a relaxation of one of the game's own
    relations. Closing the gap generally means counting how many
    conjuncts of a derived relation hold, not whether it holds -- which
    is a real inference over rule bodies and the next piece of work,
    with `objective.extract` already identifying which relations are
    worth relaxing.

    Arity is PROBED rather than parsed, because a relation's arity is
    not recorded anywhere a caller can read; the first arity that
    resolves is the one the game uses. Cached on the game, since it
    cannot change.
    """
    cached = getattr(game, '_derived', None)
    if cached is not None:
        return cached
    ggp = getattr(game, 'ggp', game)
    kb = getattr(ggp, '_rules_kb', None)
    found = []
    if kb is not None and hasattr(kb, 'all_predicates'):
        from ggp.resolver import Resolver

        state = Resolver(ggp._state_kb())
        for name in sorted(kb.all_predicates()):
            if name in GDL_KEYWORDS:
                continue
            for arity in range(cap + 1):
                query = ((name,) + tuple('?a{0}'.format(i)
                                         for i in range(arity))
                         if arity else (name,))
                try:
                    if list(state.query(query)):
                        found.append((name, arity))
                        break
                except Exception:
                    break
    try:
        game._derived = found
    except AttributeError:
        pass
    return found


def _derived_counts(game, ownership, known, shared, counts, limit=400):
    """Count the game's own derived relations in this state."""
    ggp = getattr(game, 'ggp', game)
    if not hasattr(ggp, '_state_kb'):
        return
    from ggp.resolver import Resolver

    state = Resolver(ggp._state_kb())
    for name, arity in derived_relations(game):
        query = ((name,) + tuple('?a{0}'.format(i) for i in range(arity))
                 if arity else (name,))
        try:
            solutions = list(state.query(query))
        except Exception:
            continue
        if len(solutions) > limit:
            continue            # a relation this broad is not a concept
        for binding in solutions:
            values = [str(binding['?a{0}'.format(i)])
                      for i in range(arity)
                      if '?a{0}'.format(i) in binding]
            owners = [item for item in values if item in known]
            if len(owners) != 1:
                implied = set(ownership[item] for item in values
                              if item in ownership)
                owners = sorted(implied) if len(implied) == 1 else []
            owner = owners[0] if len(owners) == 1 else shared
            counts[(owner, name)] += 1
            for index, item in enumerate(values):
                if item in known or item in ownership:
                    continue
                counts[(owner, '{0}!{1}={2}'.format(name, index,
                                                    item))] += 1


def _state_literals(body):
    """The `true(...)` conjuncts of a rule body, as fluent tuples."""
    out = []
    for literal in body:
        if (isinstance(literal, (tuple, list)) and len(literal) == 2
                and str(literal[0]) == 'true'):
            out.append(literal[1])
    return out


def _variables(term):
    found = []

    def walk(value):
        if isinstance(value, (tuple, list)):
            for item in value:
                walk(item)
        elif isinstance(value, str) and value.startswith('?'):
            if value not in found:
                found.append(value)

    walk(term)
    return found


def _slots(fluent):
    """`(relation, position) -> value` for a fluent's flat arguments."""
    relation, arguments = _flatten(fluent)
    return [((relation, index), value)
            for index, value in enumerate(arguments)]


def _bind(fluent, binding):
    """A fluent with its variables replaced, or None if any is free."""
    def walk(value):
        if isinstance(value, (tuple, list)):
            built = []
            for item in value:
                replaced = walk(item)
                if replaced is None:
                    return None
                built.append(replaced)
            return tuple(built)
        if isinstance(value, str) and value.startswith('?'):
            return binding.get(value)
        return value

    return walk(fluent)


def relaxations(game, ownership=None, cap=4000):
    """How many CONJUNCTS of each rule hold, counted but not ranked.

    THE GAP THIS IS AIMED AT, measured. On tic-tac-toe the hand-written
    m,n,k extractor reaches 93.9% optimal at one ply against this
    module's 69.4%, and the difference is not a name: the GDL defines
    `line`, and `line(x)` is only true once the game is already WON.
    What the hand-written extractor counts is `Line:j` -- lines holding
    j of my marks -- which is the PARTIAL satisfaction of the win
    condition, and no rule states it.

    So the rule is relaxed: for `row(M,W) :- true(cell(M,1,W)) &
    true(cell(M,2,W)) & true(cell(M,3,W))`, each grounding of (M, W) is
    scored by how many of its three conjuncts hold, and the count is
    emitted as a feature.

    PARTIAL SATISFACTION IS NOT ASSUMED TO MEAN ANYTHING, and that
    constraint shaped the whole design. A game's declared outcome
    separates NONE from SOME -- `line(x)` holds or it does not -- and it
    says nothing whatever about two-of-three being better than
    one-of-three. Reading an ordering into it is the same error as
    deciding that two royals must beat one, which this project has
    already made and measured.

    So each level is its OWN feature: `row~1`, `row~2`, `row~3`, with no
    ordering between them, no sign, no combination into a single
    "progress" number -- a single number would BE the assumption. The
    learner is free to price `row~2` highly and `row~1` at zero, or to
    price both at zero, which is the honest answer on a game where
    partial satisfaction means nothing. Whether it means anything HERE
    is then a measurement, not a premise.

    Bounded by `cap` groundings per rule: a rule over a large domain
    would otherwise enumerate the board.
    """
    import collections
    import itertools

    ggp = getattr(game, 'ggp', game)
    kb = getattr(ggp, '_rules_kb', None)
    state = getattr(game, 'state', None)
    if kb is None or state is None or not hasattr(kb, 'rules_for'):
        return {}
    known = set(str(role) for role in getattr(game, 'roles', ()))
    ownership = ownership or {}
    shared = getattr(game, 'current_player', None) or (
        sorted(known)[0] if known else 'none')

    #: Which constants ever appear at each (relation, position), read
    #: off the state itself -- the domain is not declared anywhere a
    #: caller can read, and guessing it would be worse than reading it.
    domain = collections.defaultdict(set)
    present = set()
    for term in state:
        present.add(tuple(term) if isinstance(term, list) else term)
        for slot, item in _slots(term):
            domain[slot].add(item)

    #: WHICH POSITIONS ARE FUNCTIONAL, derived from the state rather
    #: than declared. A position p of relation R is functional when the
    #: other arguments determine it -- no two fluents of R agree
    #: everywhere except at p. `cell(row, col, mark)` is functional at
    #: the mark, because a square holds one thing.
    #:
    #: THIS IS WHAT MAKES A RELAXATION MEAN ANYTHING. Without it, "two
    #: of this row are mine" counts a row whose third square is already
    #: the opponent's -- a dead line, worth nothing, counted the same as
    #: a live one. With it, an unsatisfied conjunct can be told apart:
    #: nothing there yet, or somebody else's.
    keyed = collections.defaultdict(lambda: collections.defaultdict(set))
    for term in present:
        relation, arguments = _flatten(term)
        for index in range(len(arguments)):
            key = tuple(arguments[:index] + arguments[index + 1:])
            keyed[(relation, index)][key].add(arguments[index])
    functional = set(slot for slot, groups in keyed.items()
                     if all(len(values) == 1
                            for values in groups.values()))

    def blocked(bound, owner):
        """True when a RIVAL already occupies this slot.

        NOT MERELY "something else is there". Tic-tac-toe fills every
        square from the start -- `cell(1,2,b)` -- so "occupied by a
        different value" is true of every empty square, and the first
        version of this check marked every line dead including the ones
        nobody had touched.

        What distinguishes a real block is that the occupying value
        BELONGS TO ANOTHER ROLE, and that is exactly what
        `infer_ownership` learns by watching play. `b` is bound to
        nobody, so it blocks nothing; `o` is bound to oplayer, so it
        blocks xplayer. No list of blank markers anywhere -- the
        distinction falls out of the binding.
        """
        relation, arguments = _flatten(bound)
        for index in range(len(arguments)):
            slot = (relation, index)
            if slot not in functional:
                continue
            key = tuple(arguments[:index] + arguments[index + 1:])
            for holding in keyed[slot].get(key, ()):
                if holding == arguments[index]:
                    continue
                rival = ownership.get(holding)
                if rival is not None and rival != owner:
                    return True
        return False

    counts = collections.Counter()
    #: relation -> the conjunct counts its rules have, so every level
    #: can be given its zero below.
    levels = {}
    for name in sorted(kb.all_predicates()):
        if name in GDL_KEYWORDS:
            continue
        for rule in kb.rules_for(name) or ():
            try:
                head, body = rule[0], rule[1]
            except (IndexError, TypeError):
                continue
            literals = _state_literals(body)
            if len(literals) < 2:
                continue        # nothing to be partial ABOUT
            variables = _variables(head) + [
                v for literal in literals for v in _variables(literal)]
            ordered = []
            for item in variables:
                if item not in ordered:
                    ordered.append(item)
            if not ordered:
                continue
            choices = []
            for variable in ordered:
                values = None
                for literal in literals:
                    for slot, item in _slots(literal):
                        if item == variable:
                            values = (domain[slot] if values is None
                                      else values & domain[slot])
                if not values:
                    choices = []
                    break
                choices.append(sorted(values))
            if not choices:
                continue
            total = 1
            for values in choices:
                total *= len(values)
            if total > cap:
                continue
            for combination in itertools.product(*choices):
                binding = dict(zip(ordered, combination))
                values = [str(v) for v in combination]
                owners = [item for item in values if item in known]
                if len(owners) != 1:
                    implied = set(ownership[item] for item in values
                                  if item in ownership)
                    owners = sorted(implied) if len(implied) == 1 else []
                owner = owners[0] if len(owners) == 1 else shared
                held = dead = 0
                for literal in literals:
                    bound = _bind(literal, binding)
                    if bound is None:
                        continue
                    if bound in present:
                        held += 1
                    elif blocked(bound, owner):
                        dead += 1
                if not held:
                    continue    # nothing of this grounding is present
                # SEPARATE NAMES, NOT A JUDGEMENT. A blocked grounding
                # is counted under its own feature rather than dropped
                # or discounted: whether a dead line is worth less than
                # a live one is for the learner to find, not for this
                # function to decide. `~` is reachable, `/` is blocked.
                marker = '~' if not dead else '/'
                counts[(owner, '{0}{1}{2}'.format(name, marker,
                                                  held))] += 1
                levels.setdefault(name, set()).add(len(literals))

    # A RELATION DEFINED AS A DISJUNCTION INHERITS ITS DISJUNCTS'
    # COUNTS. `line(W) :- row(M,W)`, `line(W) :- column(N,W)`,
    # `line(W) :- diagonal(W)` -- the GDL is saying these are the same
    # concept, so "two of a line" is the sum of two-of-a-row,
    # two-of-a-column and two-of-a-diagonal. Splitting them leaves each
    # feature a third of the data, and the aggregation is READ from the
    # rules rather than chosen: a body that is a single non-state
    # literal is a renaming.
    aliases = {}
    for name in sorted(kb.all_predicates()):
        if name in GDL_KEYWORDS:
            continue
        for rule in kb.rules_for(name) or ():
            try:
                body = rule[1]
            except (IndexError, TypeError):
                continue
            if len(body) != 1:
                continue
            inner = body[0]
            if not isinstance(inner, (tuple, list)) or not inner:
                continue
            source = str(inner[0])
            if source in GDL_KEYWORDS or source == name:
                continue
            aliases.setdefault(name, set()).add(source)
    for name, sources in sorted(aliases.items()):
        inherited = set()
        for source in sources:
            for size in levels.get(source, ()):
                inherited.add(size)
            for (owner, key), amount in list(counts.items()):
                head, marker, _, level = key.partition('~')[0], None, \
                    None, None
                for marker in ('~', '/'):
                    if key.startswith(source + marker):
                        counts[(owner, name + marker
                                + key[len(source) + 1:])] += amount
        if inherited:
            levels.setdefault(name, set()).update(inherited)

    # AN ABSENT FEATURE IS NOT A ZERO, and the difference is a biased
    # fit rather than a cosmetic one. `differentials` omits a feature
    # nobody holds, so a weight for "two of this row are mine" would be
    # fitted only on positions where somebody already has two -- never
    # on the positions where the count is what distinguishes the sides.
    # `features.mnk` sets the same zeros for the same reason, and says
    # so: "Players with no mark yet still need their zero, or the
    # feature is absent rather than zero and the comparison silently
    # changes."
    for name, sizes in levels.items():
        for size in sizes:
            for level in range(1, size + 1):
                for marker in ('~', '/'):
                    for role in sorted(known) or [shared]:
                        counts.setdefault(
                            (role, '{0}{1}{2}'.format(name, marker,
                                                      level)), 0)
    return dict(counts)


def features(game, roles=None, ownership=None, derived=False,
             relaxed=True):
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
    ownership = ownership or {}
    counts = collections.Counter()
    # SORTED for the same reason the move list is: a set's order is not
    # stable across processes, and a Counter built in a different order
    # can differ in its floating-point sums.
    for term in sorted(state, key=repr):
        relation, arguments = _flatten(term)
        owners = [item for item in arguments if item in known]
        if len(owners) != 1:
            # NO ROLE NAMED DIRECTLY. A constant the game has bound to a
            # role stands in for one -- `cell(1,1,x)` is xplayer's,
            # because only xplayer ever adds an `x`. See
            # `infer_ownership`, which learns that by watching play
            # rather than by reading rule bodies.
            implied = set(ownership[item] for item in arguments
                          if item in ownership)
            owners = sorted(implied) if len(implied) == 1 else []
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
    if derived:
        _derived_counts(game, ownership, known, shared, counts)
    if relaxed:
        for key, amount in relaxations(game, ownership).items():
            counts[key] += amount
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
        self._move_cache = {}
        self._move_cache_key = None

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
        """SORTED, because a GDL state is a SET and a resolver walks it.

        Set iteration order depends on the hash seed, so the move list
        came out in a different order in every process -- which made
        every measurement on this path irreproducible between runs. Two
        otherwise identical comparisons sampled different positions (46
        against 53) and I spent a while reading the difference as an
        effect.
        """
        if self.is_game_over():
            return []
        mover = self.current_player
        if mover is None:
            return []
        return [(mover, move)
                for move in sorted(self._moves(mover), key=repr)]

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
        clone._move_cache = {}
        clone._move_cache_key = None
        return clone

    # ---- helpers ------------------------------------------------------

    def _moves(self, role):
        """This role's legal moves, CACHED PER STATE.

        Profiling one `get_all_legal_turns` on the case study's GDL
        showed `legal_moves` running THREE times for a single call --
        once per role inside `current_player`, then again for the
        mover. Half the ten seconds was `current_player` re-deriving
        what had just been computed.

        The key is the state itself, which is the set of ground
        fluents, so the cache cannot survive a move -- and it is
        rebuilt rather than invalidated, which removes any question of
        a stale entry.
        """
        key = frozenset(self.ggp.state)
        if self._move_cache_key != key:
            self._move_cache_key = key
            self._move_cache = {}
        if role in self._move_cache:
            return self._move_cache[role]
        try:
            moves = list(self.ggp.legal_moves(role))
        except Exception:
            moves = []
        self._move_cache[role] = moves
        return moves

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
