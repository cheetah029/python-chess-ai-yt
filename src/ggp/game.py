"""GGPGame — state-machine wrapper around the KB + Resolver.

Exposes a clean Game-driving API:

    g = GGPGame.from_file('step1_kings_queens.gdl')
    print(g.roles)                            # ['black', 'white']
    print(g.legal_moves('white'))             # 10 legal moves
    g.step({'white': move, 'black': 'noop'})  # apply turn
    print(g.is_terminal())                    # False / True
    print(g.goal('white'))                    # 0..100

How it works internally:

1. The GDL file is parsed into a "rules KB" — all the (<= ...)
   rules + permanent facts (roles, file_adj, etc.).
2. The initial state is computed by querying (init ?fact) against
   the rules KB; the answers form the initial set of (true ...)
   facts. We store these as plain ?fact terms in `self.state`
   (a Python set).
3. legal_moves(player) builds a temporary KB that combines the
   rules KB with the current state's facts (each wrapped in
   `(true ...)`) and queries (legal <player> ?move).
4. step(moves) adds (does <player> <move>) facts to a temporary
   KB and queries (next ?fact) to derive the next state. The
   answer set replaces self.state. The does facts are not
   persisted.
5. is_terminal() / goal(player) work the same way — temporary
   KB + query.

Per-query KB construction is O(rule_count) and could be expensive
on the larger steps (6-11). For step 1 (kings + queens) it's
acceptably fast (a few seconds per legal-moves query). Future
optimization: cache the rule prefix once and only re-bind the
state facts.

GDL-II AND GDL-III (issue #280). The dialect is read from the
description (`ggp.dialect`). GDL-II's `sees` and `random` need nothing
from the state machine -- `random` is an ordinary role here and
`percepts(role, moves)` answers `sees` -- so a GDL-II game runs exactly
as a GDL-I one does. GDL-III's `knows` is the exception: it is defined
over play histories, so for a GDL-III description, and ONLY for one,
`step` records the joint moves in `self.history` and every query goes
through `epistemic.EpistemicResolver`. As with repetition, assigning
`game.state` directly does not rewrite `history`.

Also includes:
    RandomGGPPlayer(role, seed=None)  — picks a uniform-random
        legal move; seedable for reproducibility.
    play_game(game, players, max_steps=200)  — alternates
        legal-move + step + check-terminal until terminal or
        step cap. Returns {role: goal} dict.
"""

import hashlib as _hashlib
import os as _os
import random as _random

from .parser import parse, is_variable
from .kb import KnowledgeBase
from .resolver import Resolver
from . import dialect as _dialect
from . import fast as _fast


#: Compiled programs by a hash of their description. A compiled rule is
#: a Python closure, which cannot be pickled, and searches copy games by
#: pickling them (`lgref.experiments.fastcopy`). So a game pickles only
#: this key, and a copy in the same process re-attaches to the same
#: program -- and to its cache of models, which copies then share.
_PROGRAMS = {}


def _term_key(term):
    """A total order on GDL terms, so the fast reasoner's answers come
    out in the same order in every process (a set's order does not)."""
    if isinstance(term, tuple):
        return (1, tuple(_term_key(t) for t in term))
    return (0, str(term))


class GGPGame:
    """A Game driven by a GDL ruleset."""

    #: The models of the most recent states and joint moves, kept so
    #: every query of one state shares one evaluation.
    _MODEL_CACHE = 256

    def __init__(self, gdl_text, reasoner=None):
        """Build from a raw GDL text string. Use
        `GGPGame.from_file(path)` to load from a file.

        REASONER (issue #290). 'fast' (the default) compiles the
        description once with `ggp.fast` and computes each state's
        relations bottom-up, sharing them across every query of that
        state. 'resolver' is the original top-down resolver, kept as
        the reference the fast one is tested against. A GDL-III
        description, or one `ggp.fast` refuses (`=`, unstratified
        negation), uses the resolver whatever is asked; `self.reasoner`
        says which is in use. Legal moves come out SORTED under the
        fast reasoner and in derivation order under the resolver: the
        sets are tested equal, the orders are not. With no `reasoner`
        given, the environment variable GGP_REASONER decides, so a
        seeded result recorded before #290 can be re-run exactly:
        `GGP_REASONER=resolver python -m ...`.

        Dialect is AUTODETECTED: classic KIF prefix notation
        (rules written `(<= head body...)`) vs the modern
        Stanford/Epilog infix HRF notation (`head :- b1 & b2`).
        Both parse into the same internal representation."""
        self._rules_kb = KnowledgeBase()
        forms = self._parse_any_dialect(gdl_text)
        for form in forms:
            self._rules_kb.add_clause(form)
        self.dialect = _dialect.detect(forms)
        self.state = self._initial_state()
        self.roles = self._compute_roles()
        # GDL-III only (#280): the play so far, as joint moves, and the
        # model that answers `knows` against it. None otherwise, which
        # keeps GDL-I and GDL-II on the plain resolver.
        self.history = ()
        self._knowledge = None
        if self.dialect == _dialect.GDL_III:
            from .epistemic import KnowledgeModel
            self._knowledge = KnowledgeModel(self, self.state)
        # Host-side repetition rule (issue #160). Pure GDL-I cannot
        # express it (state hashing is inexpressible — step 10 is a
        # documented sketch), so the HOST enforces it: step() counts
        # each resulting state; with enforce_repetition=True,
        # legal_moves() filters moves whose successor state would
        # occur a THIRD time (a next-state query per move — leave it
        # off for search rollouts if too costly). The loss condition
        # ("every legal turn would third-repeat") is exposed via
        # all_moves_repetition_blocked(). NOTE: assigning game.state
        # directly desyncs the trajectory history — call
        # reset_repetition_history() after any direct injection.
        self.enforce_repetition = False
        self.reset_repetition_history()
        if reasoner is None:
            reasoner = _os.environ.get('GGP_REASONER', 'fast')
        if reasoner not in ('fast', 'resolver'):
            raise ValueError('reasoner must be fast or resolver')
        self.reasoner = 'resolver'
        self._program = None
        self._program_key = None
        if reasoner == 'fast' and self._knowledge is None:
            key = _hashlib.sha256(gdl_text.encode('utf-8')).hexdigest()
            try:
                self._program = self._attach(key)
                self._program_key = key
                self.reasoner = 'fast'
            except _fast.Unsupported:
                pass

    def _attach(self, key):
        program = _PROGRAMS.get(key)
        if program is None:
            program = _fast.compile_kb(self._rules_kb)
            program.models = {}
            _PROGRAMS[key] = program
        return program

    def __getstate__(self):
        state = dict(self.__dict__)
        state['_program'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        if self._program_key is not None:
            self._program = self._attach(self._program_key)

    @staticmethod
    def _parse_any_dialect(gdl_text):
        """Return parsed forms, autodetecting prefix-KIF vs
        infix-HRF. Heuristic: the prefix dialect wraps rules in
        `(<=`; the infix dialect uses `:-` necks and never
        contains `(<=`."""
        if '(<=' in gdl_text:
            return parse(gdl_text)
        if ':-' in gdl_text:
            from .infix import parse_infix
            return parse_infix(gdl_text)
        # Facts-only file — could be either dialect. Prefix parses
        # a superset here (parenthesised facts); try prefix first,
        # fall back to infix.
        try:
            return parse(gdl_text)
        except ValueError:
            from .infix import parse_infix
            return parse_infix(gdl_text)

    @classmethod
    def from_file(cls, path, reasoner=None):
        with open(path) as f:
            return cls(f.read(), reasoner=reasoner)

    # ---- the fast reasoner's models -------------------------------------

    def _model(self, state=None):
        models = self._program.models
        key = frozenset(self.state if state is None else state)
        model = models.get(key)
        if model is None:
            if len(models) >= self._MODEL_CACHE:
                models.clear()
            model = models[key] = self._program.state_model(key)
        return model

    def _move_model(self, moves, state=None):
        key = (frozenset(self.state if state is None else state),
               frozenset(moves.items()))
        models = self._program.models
        model = models.get(key)
        if model is None:
            base = self._model(key[0])
            model = models[key] = self._program.move_model(
                base, [('does', role, move) for role, move in moves.items()])
        return model

    def _ask(self, model, pattern):
        return self._program.ask(model, pattern)

    def _fast_next(self, moves):
        return {f[1] for f in self._ask(self._move_model(moves),
                                        ('next', '?fact'))}

    # ---- initial state computation -------------------------------------

    def _initial_state(self):
        """Query (init ?fact) against the rules KB to compute the
        initial set of state facts. Returns a set of fact terms."""
        r = Resolver(self._rules_kb)
        return {b['?fact'] for b in r.query(('init', '?fact'))}

    def _compute_roles(self):
        kb = self._state_kb()
        r = Resolver(kb)
        return sorted(b['?r'] for b in r.query(('role', '?r')))

    # ---- temporary KB building -----------------------------------------

    def _state_kb(self, extra_facts=None, state=None):
        """Build a transient KB that combines:
          - all permanent rules + permanent facts from the rules KB
            (excluding init facts — those were consumed to build
            the initial state)
          - the current state's facts (or `state`'s), each wrapped
            in (true ...)
          - any extra_facts the caller provides (typically does
            facts for next-state derivation)
        """
        kb = KnowledgeBase()
        # Copy rules + permanent facts (skip init).
        for pred in self._rules_kb.all_predicates():
            for head, body in self._rules_kb.rules_for(pred):
                kb._add_rule(head, body)
            for fact in self._rules_kb.facts_for(pred):
                if isinstance(fact, tuple) and fact and fact[0] == 'init':
                    continue
                kb._add_fact(fact)
        # Lift current state into (true ...) facts.
        for fact in (self.state if state is None else state):
            kb._add_fact(('true', fact))
        # Extras (e.g. does ...).
        if extra_facts:
            for f in extra_facts:
                kb._add_fact(f)
        return kb

    def _resolver(self, kb):
        """The plain resolver, or for GDL-III one that answers `knows`
        for the current history."""
        if self._knowledge is None:
            return Resolver(kb)
        from .epistemic import EpistemicResolver
        return EpistemicResolver(kb, self._knowledge, self.history)

    def _joint(self, moves):
        return tuple((role, moves.get(role)) for role in self.roles)

    # ---- public state-machine API --------------------------------------

    # Fact families excluded from the repetition key: the monotonic
    # turn counter (no state could ever repeat with it included) and
    # the rule-tracking counter families the rulebook itself excludes
    # from the board state (RULEBOOK.md Repetition Rule).
    _REPETITION_EXEMPT = ('turn_number', 'state_repetition_count',
                          'distance_count')

    def repetition_key(self, facts=None):
        """Hashable repetition identity of `facts` (default: the
        current state): the fact set minus the exempt counter
        families."""
        src = self.state if facts is None else facts
        return frozenset(
            f for f in src
            if not (isinstance(f, tuple) and f
                    and f[0] in self._REPETITION_EXEMPT))

    def reset_repetition_history(self):
        """Reseed the repetition history from the current state
        (count 1, mirroring the engine's record_state at game
        start). Call after assigning game.state directly."""
        self.repetition_history = {self.repetition_key(): 1}

    def peek_repetition_key(self, moves):
        """Repetition key of the state that `moves` would produce,
        WITHOUT mutating the game."""
        if self._program is not None:
            return self.repetition_key(self._fast_next(moves))
        does_facts = [('does', role, move)
                      for role, move in moves.items()]
        kb = self._state_kb(does_facts)
        r = self._resolver(kb)
        nxt = {b['?fact'] for b in r.query(('next', '?fact'))}
        return self.repetition_key(nxt)

    def _noop_complement(self, player, move):
        """The moves dict for `player` playing `move` while every
        other role noops (this ruleset is strictly alternating)."""
        moves = {role: 'noop' for role in self.roles}
        moves[player] = move
        return moves

    def _would_third_repeat(self, player, move):
        key = self.peek_repetition_key(self._noop_complement(player, move))
        return self.repetition_history.get(key, 0) >= 2

    def all_moves_repetition_blocked(self, player):
        """True iff `player` HAS legal moves but every one of them
        would cause a third repetition — the rulebook's repetition
        loss condition."""
        raw = self._raw_legal_moves(player)
        if not raw:
            return False
        return all(self._would_third_repeat(player, m) for m in raw
                   if m != 'noop')

    def _raw_legal_moves(self, player):
        if self._program is not None:
            return sorted((f[2] for f in self._ask(
                self._model(), ('legal', player, '?move'))), key=_term_key)
        kb = self._state_kb()
        r = self._resolver(kb)
        return [b['?move'] for b in r.query(('legal', player, '?move'))]

    def legal_moves(self, player):
        """Return a list of legal move terms for `player` in the
        current state. Empty list if the player is unknown or has
        no legal moves. With enforce_repetition=True, moves whose
        successor state would occur a third time are filtered
        (noop is never filtered — it belongs to the waiting
        player, whose "turn" is not a board action)."""
        moves = self._raw_legal_moves(player)
        if not self.enforce_repetition:
            return moves
        return [m for m in moves
                if m == 'noop' or not self._would_third_repeat(player, m)]

    def step(self, moves):
        """Advance the game by one turn. `moves` is a dict
        {role: move_term}. The next state is computed by
        querying (next ?fact) against a KB containing (does ...)
        facts for each player's move. The resulting state is
        recorded in the repetition history."""
        if self._program is not None:
            self.state = self._fast_next(moves)
        else:
            does_facts = [('does', role, move)
                          for role, move in moves.items()]
            kb = self._state_kb(does_facts)
            r = self._resolver(kb)
            self.state = {b['?fact']
                          for b in r.query(('next', '?fact'))}
        if self._knowledge is not None:
            self.history = self.history + (self._joint(moves),)
        key = self.repetition_key()
        self.repetition_history[key] = \
            self.repetition_history.get(key, 0) + 1

    def is_terminal(self):
        """True iff the current state satisfies `terminal`."""
        if self._program is not None:
            return bool(self._ask(self._model(), ('terminal',)))
        kb = self._state_kb()
        r = self._resolver(kb)
        return any(True for _ in r.query('terminal'))

    def goal(self, player):
        """Return the player's current goal value (0..100). Returns
        0 if no goal rule succeeds (per GDL convention, goal is
        only meaningful at terminal states)."""
        if self._program is not None:
            values = sorted((f[2] for f in self._ask(
                self._model(), ('goal', player, '?n'))), key=_term_key)
            for value in values:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    continue
            return 0
        kb = self._state_kb()
        r = self._resolver(kb)
        for b in r.query(('goal', player, '?n')):
            try:
                return int(b['?n'])
            except (ValueError, TypeError):
                continue
        return 0

    def percepts(self, player, moves):
        """What `player` is told if `moves` is played now: the set of P
        with `sees(player, P)` (GDL-II). Empty for a game without
        `sees`. Does not change the game."""
        if self._program is not None:
            return frozenset(f[2] for f in self._ask(
                self._move_model(moves), ('sees', player, '?p')))
        does_facts = [('does', role, move)
                      for role, move in moves.items()]
        r = self._resolver(self._state_kb(does_facts))
        return frozenset(b['?p'] for b in r.query(('sees', player, '?p')))

    def knows(self, player, atom):
        """Whether `player` knows ground `atom` now (GDL-III semantics;
        `player=None` asks for common knowledge). GDL-III games only,
        because only they keep the history knowledge is defined over."""
        from .kb import canonical
        model = self._knowledge
        if model is None:
            raise ValueError(
                'knows() needs a GDL-III description; this one is {}'
                .format(self.dialect))
        atom = canonical(atom)
        if player is None:
            return model.common(self.history, atom)
        return model.knows(self.history, player, atom)


# ---- Players -------------------------------------------------------------

class RandomGGPPlayer:
    """Picks a uniform-random legal move for its role. Seedable."""

    def __init__(self, role, seed=None):
        self.role = role
        self._rng = _random.Random(seed)

    def choose(self, game):
        moves = game.legal_moves(self.role)
        if not moves:
            return None
        return self._rng.choice(moves)


def play_game(game, players, max_steps=200):
    """Drive `game` with `players` (dict {role: player}) until
    terminal or `max_steps` elapse. Returns the final
    {role: goal_int} dict — 0s if not terminal at the end."""
    for _ in range(max_steps):
        if game.is_terminal():
            break
        moves = {}
        for role, p in players.items():
            choice = p.choose(game)
            if choice is None:
                # No legal moves for this role — game can't proceed.
                return {role: game.goal(role) for role in players}
            moves[role] = choice
        game.step(moves)
    return {role: game.goal(role) for role in players}
