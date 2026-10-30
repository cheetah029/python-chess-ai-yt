"""A compiled, bottom-up reasoner for GDL (issue #290).

WHY. `Resolver` answers each query top-down, from scratch, against a
knowledge base rebuilt for that query. Nothing is shared between the
sub-goals of one query or between the queries of one state, so the same
derived fact is proved again and again. On the Royal Chess opening that
costs about 1,400 ms per move, where the hand-written engine takes about
1 ms -- so a game supplied only as GDL, which is what a designer hands
the framework, ran a thousand times slower than the one game that has
its own engine.

WHAT THIS DOES INSTEAD. For a state, every derived relation is computed
ONCE, forward from the facts, stratum by stratum (stratified negation,
semi-naive iteration inside a recursive stratum). Each rule is compiled
when the description is loaded into a Python function of nested loops
over hash indexes, so evaluating it interprets nothing. Every query of
that state -- every role's legal moves, terminal, goals -- then reads
the same model. A joint move adds the `does` facts and recomputes only
the relations that depend on them (`next`, `sees`).

RULES THAT CANNOT RUN FORWARD are answered on demand: a rule with a
head variable no positive body literal binds, e.g. corridor's
`clear(P,S) :- true(at(Q,T)) & distinct(P,Q) & distinct(S,T)`, which is
only meaningful once a caller has chosen P and S, and anything defined
through one. Royal Chess's description is written top-down this way --
37 relations, `legal` among them. Each such rule is compiled once per
binding pattern it is called with (which arguments the caller has
bound), and its answers are memoised per state by those arguments, so
it is top-down evaluation with tabling, still without interpretation.

WHAT IT REFUSES. A description using `=` or nesting `knows` raises
`Unsupported` while compiling, and `GGPGame` then keeps the resolver.
So does any rule whose negation is not stratified.

SEMANTICS. The resolver evaluates a body left to right, and a `distinct`
or `not` it reaches with an unbound variable fails or tests for "no
instance". This engine places each such literal as soon as its
variables are bound, and applies the same rule to any left unbound at
the end. `tests/test_ggp_fast.py` checks the two engines give the same
legal moves, terminal, goals, next states and percepts on every test
game and on Royal Chess. The one place they differ is LEFT RECURSION:
the resolver's cycle guard cuts `reach(X, Y) :- reach(X, Z) & ...`
after one step, while this engine computes the least model, which is
what GDL defines. That is tested too.

MEASURED (Royal Chess, legal moves for both roles + terminal, one
state, steady state): ~13 ms, against ~1,400 ms for the resolver and
~1 ms for the hand-written engine.
"""

from .parser import is_variable

_EMPTY = frozenset()


class Unsupported(Exception):
    """The description uses something this engine does not compile."""


# ---- terms -----------------------------------------------------------------

def _vars(term, out):
    if is_variable(term):
        out.add(term)
    elif isinstance(term, tuple):
        for c in term:
            _vars(c, out)
    return out


def _pred(term):
    if isinstance(term, tuple):
        return term[0] if term else None
    return term


def _is_check(lit):
    return isinstance(lit, tuple) and bool(lit) and lit[0] in (
        'not', 'distinct')


def _dnf(body):
    """`or` and `and` expanded into alternative flat bodies."""
    alts = [[]]
    for lit in body:
        if isinstance(lit, tuple) and lit and lit[0] in ('or', 'and'):
            branches = ([[b] for b in lit[1:]] if lit[0] == 'or'
                        else [list(lit[1:])])
            alts = [alt + sub for alt in alts for branch in branches
                    for sub in _dnf(branch)]
        else:
            alts = [alt + [lit] for alt in alts]
    return alts


def _match(pattern, ground, env):
    """One-way match of `pattern` against `ground`; the extended env, or
    None. `env` is never mutated."""
    if is_variable(pattern):
        if pattern in env:
            return env if env[pattern] == ground else None
        new = dict(env)
        new[pattern] = ground
        return new
    if isinstance(pattern, tuple):
        if not isinstance(ground, tuple) or len(pattern) != len(ground):
            return None
        for p, g in zip(pattern, ground):
            env = _match(p, g, env)
            if env is None:
                return None
        return env
    return env if pattern == ground else None


def _subst(term, env):
    if is_variable(term):
        return env.get(term, term)
    if isinstance(term, tuple):
        return tuple(_subst(c, env) for c in term)
    return term


# ---- indexes ---------------------------------------------------------------
#
# A path names one atom of a fact: `(i,)` is argument i, `(i, j, n)` is
# element j of argument i when that argument is a tuple of length n. Only
# depth one and two are indexed; that covers `true(cell(F, R, C, T))`.

def _at(fact, path):
    if len(path) == 1:
        i = path[0]
        return fact[i] if type(fact) is tuple and len(fact) > i else _EMPTY
    i, j, n = path
    if type(fact) is not tuple or len(fact) <= i:
        return _EMPTY
    a = fact[i]
    if type(a) is not tuple or len(a) != n:
        return _EMPTY
    return a[j]


def _index_paths(pattern, bound):
    """The paths of `pattern` that are known when `bound` is: constants,
    and variables already bound."""
    out = []
    if not isinstance(pattern, tuple):
        return out
    for i in range(1, len(pattern)):
        a = pattern[i]
        if isinstance(a, tuple):
            for j, b in enumerate(a):
                if not isinstance(b, tuple) and (
                        not is_variable(b) or b in bound):
                    out.append(((i, j, len(a)), b))
        elif not is_variable(a) or a in bound:
            out.append(((i,), a))
    return out


class Model:
    """The relations true in one state (and, after a move, one joint
    move), with the indexes and demand answers built while reading it."""

    __slots__ = ('rel', 'index', 'memo', 'shared', 'fixed')

    def __init__(self, rel, index, shared=None, fixed=_EMPTY):
        self.rel = rel
        self.index = index
        self.memo = {}
        #: indexes of the relations no state changes, kept across states
        self.shared = shared
        self.fixed = fixed

    def table(self, pred, paths):
        key = (pred, paths)
        table = self.index.get(key)
        if table is None and pred in self.fixed:
            table = self.shared.get(key)
        if table is None:
            table = {}
            for f in self.rel.get(pred, _EMPTY):
                table.setdefault(tuple(_at(f, p) for p in paths),
                                 []).append(f)
            (self.shared if pred in self.fixed else self.index)[key] = table
        return table

    def drop(self, preds):
        for key in [k for k in self.index if k[0] in preds]:
            del self.index[key]


# ---- compiling one rule ----------------------------------------------------

class _Emitter:
    def __init__(self):
        self.lines = []
        self.depth = 1
        self.names = {}
        self.consts = {}

    def line(self, text):
        self.lines.append('    ' * self.depth + text)

    def var(self, v):
        if v not in self.names:
            self.names[v] = 'v%d' % len(self.names)
        return self.names[v]

    def const(self, c):
        if c not in self.consts:
            self.consts[c] = 'k%d' % len(self.consts)
        return self.consts[c]

    def expr(self, term, bound):
        """Python expression building `term`; unbound variables are
        left as their GDL names (an on-demand answer may keep one)."""
        if is_variable(term):
            return self.var(term) if term in bound else self.const(term)
        if isinstance(term, tuple):
            inner = ', '.join(self.expr(c, bound) for c in term)
            return '(' + inner + (',)' if len(term) == 1 else ')')
        return self.const(term)

    def match(self, source, term, bound, fail):
        """Emit the checks that `source` matches `term`, binding new
        variables. `fail` is the statement that rejects a candidate."""
        if is_variable(term):
            if term in bound:
                self.line('if %s != %s: %s' % (source, self.var(term), fail))
            else:
                self.line('%s = %s' % (self.var(term), source))
                bound.add(term)
            return
        if isinstance(term, tuple):
            self.line('if type(%s) is not tuple or len(%s) != %d: %s'
                      % (source, source, len(term), fail))
            for i, c in enumerate(term):
                if is_variable(c) or isinstance(c, tuple):
                    sub = '%s[%d]' % (source, i)
                    if isinstance(c, tuple):
                        tmp = 't%d' % len(self.lines)
                        self.line('%s = %s' % (tmp, sub))
                        sub = tmp
                    self.match(sub, c, bound, fail)
                else:
                    self.line('if %s[%d] != %s: %s'
                              % (source, i, self.const(c), fail))
            return
        self.line('if %s != %s: %s' % (source, self.const(term), fail))


def _order(body, demand, bound0=()):
    """Positive literals in written order; every check (`not`,
    `distinct`, an on-demand relation) as soon as its variables are
    bound; checks never bound go last. `bound0` are the variables a
    caller has bound already."""
    def is_deferred(lit):
        return _is_check(lit) or _pred(lit) in demand
    positives = [b for b in body if not is_deferred(b)]
    pending = [b for b in body if is_deferred(b)]
    ordered, bound = [], set(bound0)

    def flush():
        for c in list(pending):
            if _vars(c, set()) <= bound:
                ordered.append(c)
                pending.remove(c)
    flush()
    for p in positives:
        ordered.append(p)
        _vars(p, bound)
        flush()
    ordered.extend(pending)
    return ordered


def _call(em, lit, bound, k):
    """Emit a call of an on-demand relation: X.call answers it for the
    arguments that are ground here, and the rest are matched."""
    args = lit[1:]
    pos = tuple(i for i, a in enumerate(args) if _vars(a, set()) <= bound)
    vals = ''.join(em.expr(args[i], bound) + ', ' for i in pos)
    call = 'X.call(%s, %r, (%s))' % (em.const(_pred(lit)), pos, vals)
    if len(pos) == len(args):
        em.line('if %s:' % call)
        em.depth += 1
        return
    f = 'f%d' % k
    em.line('for %s in %s:' % (f, call))
    em.depth += 1
    em.match(f, lit, bound, 'continue')


def _compile(head, body, demand, delta_at=None, call_pos=None):
    """Source of a function `(M, X, D, out, a)` adding every head
    instance the body derives in model X (relations M) to `out`.

    With `delta_at` set, literal number `delta_at` reads the new facts
    `D` instead. With `call_pos` set, the rule answers an on-demand call
    whose arguments at those positions are given in `a`; its body is
    ordered for those bindings, and a head variable left unbound stays
    a variable in the answer, as the resolver leaves it."""
    em = _Emitter()
    bound = set()
    if call_pos is not None:
        for j, i in enumerate(call_pos):
            em.match('a[%d]' % j, head[1 + i], bound, 'return')
        body = _order(body, demand, bound)
    for k, lit in enumerate(body):
        op = lit[0] if isinstance(lit, tuple) and lit else lit
        if op == '=':
            raise Unsupported('`=` is not compiled')
        if op == 'knows':
            raise Unsupported('`knows` is answered by the epistemic model')
        if op == 'distinct':
            if _vars(lit, set()) <= bound:
                em.line('if %s != %s:' % (em.expr(lit[1], bound),
                                          em.expr(lit[2], bound)))
            else:
                em.line('if False:')   # the resolver fails it unbound
            em.depth += 1
            continue
        if op == 'not':
            inner = lit[1]
            q = _pred(inner)
            if q == 'knows' or (isinstance(inner, tuple) and inner
                                and inner[0] in ('=', 'or', 'and', 'not')):
                raise Unsupported('complex negation')
            if q in demand:
                args = inner[1:]
                pos = tuple(i for i, x in enumerate(args)
                            if _vars(x, set()) <= bound)
                vals = ''.join(em.expr(args[i], bound) + ', ' for i in pos)
                em.line('if not X.call(%s, %r, (%s)):'
                        % (em.const(q), pos, vals))
            elif not _vars(inner, set()) <= bound:
                em.line('if not X.exists(%s):' % em.expr(inner, bound))
            else:
                em.line('if %s not in M.get(%s, E):'
                        % (em.expr(inner, bound), em.const(q)))
            em.depth += 1
            continue
        q = _pred(lit)
        pq = em.const(q)
        if q in demand:
            _call(em, lit, bound, k)
            continue
        if _vars(lit, set()) <= bound:
            src = 'D' if k == delta_at else 'M.get(%s, E)' % pq
            em.line('if %s in %s:' % (em.expr(lit, bound), src))
            em.depth += 1
            continue
        f = 'f%d' % k
        paths = _index_paths(lit, bound)
        if k == delta_at:
            em.line('for %s in D:' % f)
        elif paths:
            key = ''.join(em.expr(v, bound) + ', ' for _, v in paths)
            em.line('for %s in X.table(%s, %r).get((%s), ()):'
                    % (f, pq, tuple(p for p, _ in paths), key))
        else:
            em.line('for %s in M.get(%s, E):' % (f, pq))
        em.depth += 1
        em.match(f, lit, bound, 'continue')
    if call_pos is None and not _vars(head, set()) <= bound:
        raise Unsupported('unsafe head reached the compiler: %r' % (head,))
    em.line('out.add(%s)' % em.expr(head, bound))
    consts = ''.join('    %s = %r\n' % (name, c)
                     for c, name in em.consts.items())
    return ('def _make(E):\n%s    def rule(M, X, D, out, a):\n%s\n'
            '    return rule\n'
            % (consts, '\n'.join('    ' + ln for ln in em.lines)))


def _build(source):
    # The source is generated here, never read: every GDL constant
    # enters it through repr() as a separate assignment, and variables
    # are renamed v0, v1, ..., so a description cannot inject code.
    namespace = {}
    exec(compile(source, '<gdl rule>', 'exec'), namespace)  # nosec B102
    return namespace['_make'](_EMPTY)


class _Bound:
    """What a compiled rule calls as X: one model, and the answers to
    on-demand relations for it, memoised by (relation, bound positions,
    values). A call that re-enters itself sees no answers, which is the
    resolver's cycle guard."""

    __slots__ = ('model', 'program', 'table', 'memo', 'fixed_memo')

    def __init__(self, model, program):
        self.model = model
        self.program = program
        self.table = model.table
        self.memo = model.memo
        self.fixed_memo = program._fixed_memo

    def call(self, pred, pos, vals):
        key = (pred, pos, vals)
        memo = (self.fixed_memo if not self.program.depends[pred]
                else self.memo)
        found = memo.get(key)
        if found is not None:
            return found
        memo[key] = ()
        out = set()
        rel = self.model.rel.get(pred)
        if rel:
            if pos:
                paths = tuple((i + 1,) for i in pos)
                out.update(self.table(pred, paths).get(vals, ()))
            else:
                out.update(rel)
        M = self.model.rel
        for rule in self.program.demand_fns(pred, pos):
            rule(M, self, _EMPTY, out, vals)
        found = memo[key] = tuple(out)
        return found

    def exists(self, pattern):
        return bool(self.answers(pattern))

    def answers(self, pattern):
        p = _pred(pattern)
        args = pattern[1:] if isinstance(pattern, tuple) else ()
        if p in self.program.demand:
            pos = tuple(i for i, x in enumerate(args) if not _vars(x, set()))
            source = self.call(p, pos, tuple(args[i] for i in pos))
        else:
            paths = _index_paths(pattern, set())
            if paths:
                source = self.table(p, tuple(q for q, _ in paths)).get(
                    tuple(v for _, v in paths), ())
            else:
                source = self.model.rel.get(p, _EMPTY)
        return [g for g in source if _match(pattern, g, {}) is not None]


def _components(nodes, edges):
    """Strongly connected components of `edges` (p -> what p reads),
    listed so that every component comes after those it reads. Returns
    (components as sets, {node: component number})."""
    index, low, stack, on = {}, {}, [], set()
    comps, comp = [], {}
    counter = [0]

    def visit(root):
        work = [(root, iter(sorted(edges.get(root, ()))))]
        index[root] = low[root] = counter[0]
        counter[0] += 1
        stack.append(root)
        on.add(root)
        while work:
            node, it = work[-1]
            advanced = False
            for nxt in it:
                if nxt not in index:
                    index[nxt] = low[nxt] = counter[0]
                    counter[0] += 1
                    stack.append(nxt)
                    on.add(nxt)
                    work.append((nxt, iter(sorted(edges.get(nxt, ())))))
                    advanced = True
                    break
                if nxt in on:
                    low[node] = min(low[node], index[nxt])
            if advanced:
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[node])
            if low[node] == index[node]:
                group = set()
                while True:
                    x = stack.pop()
                    on.discard(x)
                    group.add(x)
                    comp[x] = len(comps)
                    if x == node:
                        break
                comps.append(group)

    for n in sorted(nodes):
        if n not in index:
            visit(n)
    return comps, comp


# ---- the program -----------------------------------------------------------

class Program:
    """A GDL description compiled once.

    `rules` is an iterable of (head, body) and `facts` of ground facts,
    as `KnowledgeBase` holds them. `init` facts are kept out by the
    caller; the state supplies `true` and the move supplies `does`.
    """

    def __init__(self, rules, facts):
        raw = [(h, b) for h, body in rules for b in _dnf(body)]
        self.demand = self._find_demand(raw)
        self.demand_rules = {}
        for h, b in raw:
            if _pred(h) in self.demand:
                self.demand_rules.setdefault(_pred(h), []).append((h, b))
        self.heads = {_pred(h) for h, _ in raw}
        self._stratify(raw)
        self._strata = []
        for preds in self.strata:
            own = [(h, _order(b, self.demand)) for h, b in raw
                   if _pred(h) in preds and _pred(h) not in self.demand]
            compiled = []
            for h, b in own:
                full = _build(_compile(h, b, self.demand))
                deltas = [(k, _pred(lit),
                           _build(_compile(h, b, self.demand, delta_at=k)))
                          for k, lit in enumerate(b)
                          if not _is_check(lit) and _pred(lit) in preds
                          and _pred(lit) not in self.demand]
                compiled.append((_pred(h), full, deltas))
            self._strata.append((preds, compiled))
        self._demand_fns = {}
        self._fixed_memo = {}
        facts_by = {}
        for f in facts:
            facts_by.setdefault(_pred(f), set()).add(f)
        self._facts = facts_by
        self._static = None

    def demand_fns(self, pred, pos):
        """The rules of on-demand `pred`, compiled for a call with the
        arguments at `pos` bound; compiled on first use."""
        key = (pred, pos)
        fns = self._demand_fns.get(key)
        if fns is None:
            fns = [_build(_compile(h, b, self.demand, call_pos=pos))
                   for h, b in self.demand_rules.get(pred, ())]
            self._demand_fns[key] = fns
        return fns

    @staticmethod
    def _find_demand(raw):
        demand = set()
        changed = True
        while changed:
            changed = False
            for head, body in raw:
                p = _pred(head)
                if p in demand:
                    continue
                bound = set()
                for lit in body:
                    if not _is_check(lit) and _pred(lit) not in demand:
                        _vars(lit, bound)
                if not _vars(head, set()) <= bound:
                    demand.add(p)
                    changed = True
        return demand

    def _stratify(self, raw):
        deps = {p: set() for p in self.heads}
        reads = {p: set() for p in self.heads}
        for h, body in raw:
            p = _pred(h)
            for lit in body:
                neg = isinstance(lit, tuple) and lit and lit[0] == 'not'
                inner = lit[1] if neg else lit
                if isinstance(inner, tuple) and inner and inner[0] in (
                        'or', 'and', 'not'):
                    for sub in inner[1:]:
                        q = _pred(sub)
                        if q in self.heads:
                            deps[p].add((q, True))
                    continue
                q = _pred(inner)
                if q in ('true', 'does'):
                    reads[p].add(q)
                elif q in self.heads:
                    deps[p].add((q, neg))
        # what each relation depends on, transitively: 'true', 'does'
        self.depends = {p: set(reads[p]) for p in self.heads}
        changed = True
        while changed:
            changed = False
            for p in self.heads:
                for q, _ in deps[p]:
                    if not self.depends[q] <= self.depends[p]:
                        self.depends[p] |= self.depends[q]
                        changed = True
        # One stratum per strongly connected component, in dependency
        # order, so a relation is complete before anything reads it --
        # including through an on-demand relation, which reads the model
        # at call time. Negation inside a component is not stratified.
        order, comp = _components(self.heads, {
            p: {q for q, _ in deps[p]} for p in self.heads})
        for p in self.heads:
            for q, neg in deps[p]:
                if neg and comp[p] == comp[q]:
                    raise Unsupported('negation is not stratified')
        self.strata = order

    # ---- evaluation ------------------------------------------------------

    def _run(self, model, select):
        bound = _Bound(model, self)
        M = model.rel
        for preds, compiled in self._strata:
            chosen = [c for c in compiled if select(c[0])]
            if not chosen:
                continue
            mine = {c[0] for c in chosen}
            for p in mine:
                M[p] = set(M.get(p, _EMPTY))
            model.drop(mine)
            delta = {}
            for p, full, _ in chosen:
                out = set()
                full(M, bound, _EMPTY, out, None)
                out -= M[p]
                if out:
                    delta.setdefault(p, set()).update(out)
            for p, fs in delta.items():
                M[p] |= fs
            model.drop(mine)
            recursive = [c for c in chosen if c[2]]
            while delta and recursive:
                new = {}
                for p, _, deltas in recursive:
                    for k, q, rule in deltas:
                        if q in delta:
                            out = set()
                            rule(M, bound, delta[q], out, None)
                            out -= M[p]
                            if out:
                                new.setdefault(p, set()).update(out)
                for p, fs in new.items():
                    M[p] |= fs
                model.drop(mine)
                delta = new

    def static(self):
        """The relations no state can change, computed once."""
        if self._static is None:
            model = Model({p: set(fs) for p, fs in self._facts.items()}, {})
            self._run(model, lambda p: not self.depends[p])
            self._fixed = frozenset(
                p for p in model.rel
                if p not in self.heads or not self.depends[p]) - {
                    'true', 'does'} - self.demand
            self._static = model
        return self._static

    def state_model(self, state):
        """Everything derivable from `state` without a move."""
        static = self.static()
        rel = dict(static.rel)
        rel['true'] = {('true', f) for f in state}
        model = Model(rel, {}, static.index, self._fixed)
        self._run(model, lambda p: (self.depends[p]
                                    and 'does' not in self.depends[p]))
        return model

    def move_model(self, base, does):
        """`base` (a state model) after the `does` facts of a joint move:
        only the relations that read `does` are recomputed."""
        rel = dict(base.rel)
        rel['does'] = set(does)
        index = {k: v for k, v in base.index.items()
                 if k[0] != 'does' and 'does' not in self.depends.get(
                     k[0], ())}
        model = Model(rel, index, base.shared, base.fixed)
        model.memo.update(
            (k, v) for k, v in base.memo.items()
            if 'does' not in self.depends[k[0]])
        self._run(model, lambda p: 'does' in self.depends[p])
        return model

    def ask(self, model, pattern):
        """Ground instances of `pattern` true in `model`, without
        duplicates. May contain a variable where the description leaves
        an argument existential (step 10's repetition sketch)."""
        from .kb import canonical
        pattern = canonical(pattern)
        return list(dict.fromkeys(_Bound(model, self).answers(pattern)))


def compile_kb(kb):
    """A Program for a `KnowledgeBase`, leaving out `init` facts."""
    rules, facts = [], []
    for p in kb.all_predicates():
        rules.extend(kb.rules_for(p))
        facts.extend(f for f in kb.facts_for(p) if _pred(f) != 'init')
    return Program(rules, facts)
