"""GDL-III knowledge: `knows(R, P)` and `knows(P)` over play sequences.

Issue #280. Semantics are Thielscher's (IJCAI 2017, Definitions 2-3),
implemented literally rather than approximated:

  INDISTINGUISHABILITY. Two legal play sequences of the same length are
  indistinguishable for role r when, at every step, r made the same
  move and received the same set of `sees` percepts. Nothing else
  reaches a player: not the other roles' moves, not the state.

  KNOWLEDGE. `knows(r, p)` holds after sequence d when p holds after
  EVERY sequence r cannot tell apart from d. `knows(p)`, common
  knowledge, quantifies over the reflexive-transitive closure of all
  roles' relations together.

  INDUCTION. Legality, update and percepts may themselves depend on
  knowledge (Muddy Children: you may say yes only if you know you are
  muddy). So every query is made AT a history, and a `knows` inside it
  is answered for that history. A sequence of length n is built from
  sequences of length n-1, whose knowledge is already settled.

  P IS REIFIED. In `knows(ann, isMuddy(bob))` the argument is an atom,
  usually a defined predicate, evaluated in the state each candidate
  sequence leads to. Nesting goes through an auxiliary predicate, as in
  the paper: `kb(P) :- knows(bob, P)` then `knows(ann, kb(...))`.

  VARIABLES. `knows(C, isMuddy(C))` with C unbound asks for every
  instance that is known. Knowledge is veridical (a sequence is
  indistinguishable from itself), so the candidates are exactly the
  instances true in the actual position, and each is then checked.

WHAT IT COSTS. Every legal play sequence of the current length is
enumerated, which is exponential in game length. That is the semantics,
not an implementation choice: knowledge is a property of the whole set.
It is affordable on the epistemic puzzles GDL-III was designed for, and
it is never paid by a GDL-I or GDL-II game, which never constructs one
of these.

A sequence that reaches a terminal position is not extended: no play
continues past the end of a game, so no player can be uncertain between
the actual play and one that did.
"""

import contextlib
import itertools

from .kb import canonical
from .parser import is_variable
from .resolver import Resolver, _cycle_key, _substitute, _unify


def _does(joint):
    return [('does', role, move) for role, move in joint]


class CircularKnowledge(ValueError):
    """`knows` was asked to decide something that depends on itself.

    GDL-III requires an ordering on the predicates used under `knows`
    such that none depends on its own knowledge. A description without
    one has no meaning, so this is reported instead of looping.
    """


class EpistemicResolver(Resolver):
    """A `Resolver` that answers `knows` goals for one history."""

    def __init__(self, kb, model, history):
        super().__init__(kb)
        self.model = model
        self.history = history

    def _query(self, goal, subst=None, depth=0, in_progress=None):
        if subst is None:
            subst = {}
        if in_progress is None:
            in_progress = set()
        ground = _substitute(goal, subst)
        if isinstance(ground, tuple) and len(ground) in (2, 3) \
                and ground[0] == 'knows':
            yield from self._knows(ground, subst, depth, in_progress)
            return
        yield from super()._query(goal, subst, depth, in_progress)

    def _knows(self, goal, subst, depth, in_progress):
        # The same knowledge question re-entered at the same history is
        # circular. The plain resolver's cycle guard would cut it
        # silently and return an arbitrary answer, so it is caught here.
        key = ('asking', self.history, _cycle_key(goal))
        with self.model.deciding(key, goal):
            yield from self._knows_unguarded(goal, subst, depth,
                                             in_progress)

    def _knows_unguarded(self, goal, subst, depth, in_progress):
        if len(goal) == 3:
            who, atom = goal[1], canonical(goal[2])
            roles = (list(self.model.roles) if is_variable(who)
                     else [who])
        else:
            who, atom = None, canonical(goal[1])
            roles = [None]
        decided = set()
        # A FRESH cycle set: the atom is asked as a new question about
        # this history. Inheriting the caller's set would let the plain
        # guard cut `p :- ~knows(a, p)` silently instead of refusing it.
        for found in self._query(atom, subst, depth + 1, set()):
            instance = _substitute(atom, found)
            for role in roles:
                if (role, instance) in decided:
                    continue
                decided.add((role, instance))
                if role is None:
                    known = self.model.common(self.history, instance)
                else:
                    known = self.model.knows(self.history, role, instance)
                if not known:
                    continue
                result = (found if role is None
                          else _unify(who, role, found))
                if result is not None:
                    yield result


class KnowledgeModel(object):
    """Everything about a GDL-III game that depends on histories.

    The caches are functions of the RULES alone -- the state a history
    leads to, its legal moves, its percepts -- so one model is shared by
    every copy of a game, and `deepcopy` returns it unchanged. A search
    that copies the game at every node then pays for each sequence once.
    """

    def __init__(self, game, initial_state):
        # Only the game's RULES are used (`_state_kb` with an explicit
        # state), which no copy of the game changes.
        self._game = game
        self.roles = list(game.roles)
        self._states = {(): frozenset(initial_state)}
        self._legal = {}
        self._percepts = {}
        self._holds = {}
        self._terminal = {}
        self._sequences = {0: [()]}
        self._views = {}
        self._groups = {}
        self._components = {}
        self._deciding = set()

    def __deepcopy__(self, memo):
        return self

    # ---- one history -------------------------------------------------

    def resolver(self, history, extra_facts=None):
        kb = self._game._state_kb(extra_facts, self.state(history))
        return EpistemicResolver(kb, self, history)

    def state(self, history):
        if history not in self._states:
            prefix, joint = history[:-1], history[-1]
            resolver = self.resolver(prefix, _does(joint))
            self._states[history] = frozenset(
                b['?fact'] for b in resolver.query(('next', '?fact')))
        return self._states[history]

    def legal(self, history, role):
        key = (history, role)
        if key not in self._legal:
            resolver = self.resolver(history)
            self._legal[key] = sorted(
                {b['?move'] for b in resolver.query(
                    ('legal', role, '?move'))}, key=repr)
        return self._legal[key]

    def terminal(self, history):
        if history not in self._terminal:
            resolver = self.resolver(history)
            self._terminal[history] = any(
                True for _ in resolver.query('terminal'))
        return self._terminal[history]

    def percepts(self, history, joint, role):
        key = (history, joint, role)
        if key not in self._percepts:
            resolver = self.resolver(history, _does(joint))
            self._percepts[key] = frozenset(
                b['?p'] for b in resolver.query(('sees', role, '?p')))
        return self._percepts[key]

    def holds(self, history, atom):
        key = (history, atom)
        if key not in self._holds:
            resolver = self.resolver(history)
            self._holds[key] = any(True for _ in resolver.query(atom))
        return self._holds[key]

    def view(self, history, role):
        """What `role` has observed: its own move and percepts per step."""
        key = (history, role)
        if key not in self._views:
            self._views[key] = tuple(
                (dict(joint).get(role),
                 self.percepts(history[:i], joint, role))
                for i, joint in enumerate(history))
        return self._views[key]

    # ---- all histories of one length ---------------------------------

    def sequences(self, length):
        """Every legal play sequence of `length` joint moves."""
        built = max(self._sequences)
        while built < length:
            extended = []
            for history in self._sequences[built]:
                if self.terminal(history):
                    continue
                options = [self.legal(history, role) for role in self.roles]
                if not all(options):
                    continue
                for moves in itertools.product(*options):
                    extended.append(history + (tuple(zip(self.roles,
                                                         moves)),))
            built += 1
            self._sequences[built] = extended
        return self._sequences[length]

    def _group(self, length, role):
        key = (length, role)
        if key not in self._groups:
            groups = {}
            for history in self.sequences(length):
                groups.setdefault(self.view(history, role),
                                  []).append(history)
            self._groups[key] = groups
        return self._groups[key]

    def _component(self, length):
        """history -> id of its class under the union of all relations."""
        if length not in self._components:
            parent = {h: h for h in self.sequences(length)}

            def find(h):
                while parent[h] != h:
                    parent[h] = parent[parent[h]]
                    h = parent[h]
                return h

            for role in self.roles:
                for members in self._group(length, role).values():
                    root = find(members[0])
                    for other in members[1:]:
                        parent[find(other)] = root
            self._components[length] = {h: find(h) for h in parent}
        return self._components[length]

    # ---- knowledge ---------------------------------------------------

    @contextlib.contextmanager
    def deciding(self, key, atom):
        if key in self._deciding:
            raise CircularKnowledge(
                'knowledge of {!r} depends on itself; GDL-III requires '
                'an acyclic ordering of the predicates under knows'
                .format(atom))
        self._deciding.add(key)
        try:
            yield
        finally:
            self._deciding.discard(key)

    def _decide(self, key, candidates, atom):
        with self.deciding(key, atom):
            return all(self.holds(other, atom) for other in candidates)

    def knows(self, history, role, atom):
        candidates = self._group(len(history), role).get(
            self.view(history, role), [history])
        return self._decide(('knows', history, role, atom),
                            candidates, atom)

    def common(self, history, atom):
        component = self._component(len(history))
        if history not in component:
            candidates = [history]
        else:
            root = component[history]
            candidates = [h for h, r in component.items() if r == root]
        return self._decide(('common', history, atom), candidates, atom)
