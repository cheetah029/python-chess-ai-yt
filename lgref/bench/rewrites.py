"""Behaviour-preserving rewrites of a GDL description (Experiment 4).

Each rewrite returns the new forms and a PROVENANCE map: for every new
statement, the set of original statement positions it came from. When a
rewrite changes the statement count (a helper extracted, a helper
inlined, a definition duplicated), groupings of the two descriptions are
compared through this map, never by position.

  scramble     every non-keyword, non-numeric symbol renamed to an
               opaque hash (`lgref.identify.robustness.rename_symbols`)
  reorder      the statements in a seeded random order
  extract      in every rule with three or more ordinary positive body
               literals, the last two become a new helper predicate
  inline       every helper defined by exactly one non-recursive rule,
               and never called under negation, is unfolded into its
               callers and its definition removed
  duplicate    every helper called from two or more places gets an
               identical copy, and every second call site uses the copy
  permute      every helper's arguments rotated by one, in its
               definitions and at every call

A HELPER is a predicate the description defines that is not a GDL
keyword and never appears inside `true`, `next` or `init`: renaming or
restructuring it cannot change a state.

`verify` checks a rewrite preserves behaviour: the same roles, the same
initial state, the same percepts (GDL-II `sees`), and the same legal
moves,
successors, endings and payoffs in every state given (exhaustively on
the small games, on the Paper A state set on the larger ones). Under
`scramble` the states are renamed with the same map before comparing.
"""

import random

from lgref.identify.clauses import is_variable
from lgref.identify.robustness import KEYWORDS, rename_symbols

REWRITES = ('scramble', 'reorder', 'extract', 'inline', 'duplicate',
            'permute')

_ORDINARY_EXCLUDED = frozenset({'not', 'does', 'distinct', 'or', 'and'})


def _is_rule(form):
    return isinstance(form, tuple) and form and form[0] == '<='


def _head(form):
    return form[1] if _is_rule(form) else form


def _body(form):
    return list(form[2:]) if _is_rule(form) else []


def _name(term):
    if isinstance(term, tuple) and term:
        return term[0]
    return term if isinstance(term, str) else None


def _variables(term, out=None):
    out = set() if out is None else out
    if is_variable(term):
        out.add(term)
    elif isinstance(term, tuple):
        for child in term:
            _variables(child, out)
    return out


def _state_names(forms):
    """Predicates that name state: inside true, next or init."""
    out = set()

    def walk(term):
        if isinstance(term, tuple) and term:
            if term[0] in ('true', 'next', 'init') and len(term) == 2:
                name = _name(term[1])
                if name:
                    out.add(name)
            for child in term:
                walk(child)

    for form in forms:
        walk(form)
    return out


def helpers(forms):
    """Defined predicates that are neither keywords nor state."""
    state = _state_names(forms)
    defined = {_name(_head(f)) for f in forms}
    return sorted(n for n in defined if n and n not in KEYWORDS
                  and n not in state and n not in ('role',))


def _identity(forms):
    return {i: {i} for i in range(len(forms))}


# ---- the rewrites ------------------------------------------------------

def scramble(forms, seed=0):
    return rename_symbols(forms, 'opaque'), _identity(forms)


def reorder(forms, seed=0):
    order = list(range(len(forms)))
    random.Random(seed).shuffle(order)  # nosec B311: a rewrite, not security
    return ([forms[i] for i in order],
            {new: {old} for new, old in enumerate(order)})


def _ordinary(goal, helper_names):
    """A positive literal safe to move into a helper: a call to a
    relation or a `true` read, not `does`, `distinct` or a negation."""
    name = _name(goal)
    return (isinstance(goal, tuple) and name not in _ORDINARY_EXCLUDED
            and name is not None)


def extract(forms, seed=0):
    names = set(helpers(forms))
    taken = {_name(_head(f)) for f in forms}
    out, provenance, counter = [], {}, 0
    for index, form in enumerate(forms):
        body = _body(form)
        picks = [i for i, g in enumerate(body) if _ordinary(g, names)]
        if not _is_rule(form) or len(picks) < 3:
            provenance[len(out)] = {index}
            out.append(form)
            continue
        chosen = picks[-2:]
        moved = [body[i] for i in chosen]
        rest = [g for i, g in enumerate(body) if i not in chosen]
        elsewhere = _variables(_head(form))
        for goal in rest:
            _variables(goal, elsewhere)
        exported = sorted(_variables(tuple(moved)) & elsewhere)
        while True:
            name = 'aux{}'.format(counter)
            counter += 1
            if name not in taken:
                break
        call = (name,) + tuple(exported) if exported else name
        provenance[len(out)] = {index}
        out.append(('<=', _head(form)) + tuple(rest + [call]))
        provenance[len(out)] = {index}
        out.append(('<=', call) + tuple(moved))
    return out, provenance


def _substitute(term, mapping):
    if is_variable(term):
        return mapping.get(term, term)
    if isinstance(term, tuple):
        return tuple(_substitute(child, mapping) for child in term)
    return term


def _unify(a, b, mapping):
    """Extend `mapping` so that a and b are equal, or return None."""
    a, b = _walk(a, mapping), _walk(b, mapping)
    if a == b:
        return mapping
    if is_variable(a):
        mapping = dict(mapping)
        mapping[a] = b
        return mapping
    if is_variable(b):
        mapping = dict(mapping)
        mapping[b] = a
        return mapping
    if (isinstance(a, tuple) and isinstance(b, tuple)
            and len(a) == len(b)):
        for x, y in zip(a, b):
            mapping = _unify(x, y, mapping)
            if mapping is None:
                return None
        return mapping
    return None


def _walk(term, mapping):
    while is_variable(term) and term in mapping:
        term = mapping[term]
    return term


def _resolve(term, mapping):
    term = _walk(term, mapping)
    if isinstance(term, tuple):
        return tuple(_resolve(child, mapping) for child in term)
    return term


def _negated_names(forms):
    out = set()

    def walk(term, negated):
        if isinstance(term, tuple) and term:
            if term[0] == 'not':
                for child in term[1:]:
                    walk(child, True)
                return
            if negated:
                name = _name(term)
                if name:
                    out.add(name)
            for child in term[1:]:
                walk(child, negated)
        elif negated and isinstance(term, str):
            out.add(term)

    for form in forms:
        for goal in _body(form):
            walk(goal, False)
    return out


def inline(forms, seed=0):
    names = set(helpers(forms))
    negated = _negated_names(forms)
    definitions = {}
    for index, form in enumerate(forms):
        name = _name(_head(form))
        if name in names:
            definitions.setdefault(name, []).append(index)
    targets = {}
    for name, where in definitions.items():
        if len(where) != 1 or name in negated:
            continue
        form = forms[where[0]]
        if not _is_rule(form):
            continue
        if any(_name(g) == name for g in _body(form)):
            continue        # directly recursive
        targets[name] = where[0]
    # Inline one level only: a target whose body calls another target is
    # left alone, so the result never depends on the order of unfolding.
    targets = {n: i for n, i in targets.items()
               if not any(_name(g) in targets for g in _body(forms[i]))}
    out, provenance, counter = [], {}, [0]

    def fresh(form):
        mapping = {}
        for var in sorted(_variables(form)):
            counter[0] += 1
            mapping[var] = '{}_{}'.format(var, counter[0])
        return _substitute(form, mapping)

    for index, form in enumerate(forms):
        name = _name(_head(form))
        if name in targets and targets[name] == index:
            continue
        if not _is_rule(form):
            provenance[len(out)] = {index}
            out.append(form)
            continue
        sources = {index}
        mapping, body, ok = {}, [], True
        for goal in _body(form):
            target = targets.get(_name(goal))
            if target is None:
                body.append(goal)
                continue
            definition = fresh(forms[target])
            mapping = _unify(_head(definition), goal, mapping)
            if mapping is None:
                ok = False
                break
            body.extend(_body(definition))
            sources.add(target)
        if not ok:
            provenance[len(out)] = {index}
            out.append(form)
            continue
        new = ('<=', _resolve(_head(form), mapping)) + tuple(
            _resolve(g, mapping) for g in body)
        provenance[len(out)] = sources
        out.append(new)
    # A helper with no caller left was inlined everywhere; one still
    # called (from a form whose unification failed) must stay.
    called = set()
    for form in out:
        for goal in _body(form):
            _collect_names(goal, called)
    for name, index in sorted(targets.items(), key=lambda kv: kv[1]):
        if name in called:
            provenance[len(out)] = {index}
            out.append(forms[index])
    return out, provenance


def _collect_names(term, out):
    if isinstance(term, tuple) and term:
        if term[0] in ('not', 'or', 'and'):
            for child in term[1:]:
                _collect_names(child, out)
            return
        out.add(term[0])
    elif isinstance(term, str):
        out.add(term)


def duplicate(forms, seed=0):
    names = set(helpers(forms))
    taken = {_name(_head(f)) for f in forms}
    calls = {}
    for form in forms:
        for goal in _body(form):
            found = set()
            _collect_names(goal, found)
            for name in found & names:
                calls[name] = calls.get(name, 0) + 1
    copies = {}
    for name in sorted(n for n, c in calls.items() if c >= 2):
        copy = name + '_dup'
        while copy in taken:
            copy += '_'
        copies[name] = copy
    seen = {}

    def rename_call(term):
        if isinstance(term, tuple) and term:
            if term[0] in ('not', 'or', 'and'):
                return (term[0],) + tuple(rename_call(c) for c in term[1:])
            name = term[0]
        elif isinstance(term, str):
            name = term
        else:
            return term
        if name not in copies:
            return term
        seen[name] = seen.get(name, 0) + 1
        if seen[name] % 2 == 0:
            if isinstance(term, tuple):
                return (copies[name],) + term[1:]
            return copies[name]
        return term

    out, provenance = [], {}
    for index, form in enumerate(forms):
        if _is_rule(form):
            form = ('<=', _head(form)) + tuple(rename_call(g)
                                               for g in _body(form))
        provenance[len(out)] = {index}
        out.append(form)
    for index, form in enumerate(forms):
        name = _name(_head(form))
        if name in copies:
            head = _head(form)
            new_head = ((copies[name],) + head[1:]
                        if isinstance(head, tuple) else copies[name])
            # A recursive definition's own calls stay on the original.
            new = (('<=', new_head) + tuple(_body(form))
                   if _is_rule(form) else new_head)
            provenance[len(out)] = {index}
            out.append(new)
    return out, provenance


def permute(forms, seed=0):
    """Rotate each helper's arguments where it is used AS A PREDICATE:
    statement heads, and body goals at the top level or under `not` /
    `or` / `and`. A term nested as an ARGUMENT is never touched, so an
    action that happens to share a helper's name -- checkers' action
    `jump(X,Y,X2,Y2)` and helper `jump(P,X,Y,X2,Y2)` -- keeps its form
    inside `legal` and `does` (#386: rotating it changed the moves)."""
    names = {n for n in helpers(forms)}

    def literal(term):
        if isinstance(term, tuple) and term:
            if term[0] in ('not', 'or', 'and'):
                return (term[0],) + tuple(literal(t) for t in term[1:])
            if term[0] in names and len(term) > 2:
                args = list(term[1:])
                return (term[0],) + tuple(args[1:] + args[:1])
        return term

    out = []
    for form in forms:
        if _is_rule(form):
            out.append(('<=', literal(_head(form)))
                       + tuple(literal(g) for g in _body(form)))
        else:
            out.append(literal(form))
    return out, _identity(forms)


FUNCTIONS = {
    'scramble': scramble,
    'reorder': reorder,
    'extract': extract,
    'inline': inline,
    'duplicate': duplicate,
    'permute': permute,
}


def rewrite(name, forms, seed=0):
    """(new forms, provenance) for one named rewrite."""
    return FUNCTIONS[name](list(forms), seed=seed)


def state_map(name, forms):
    """How a rewrite renames state facts (identity except `scramble`)."""
    if name != 'scramble':
        return lambda state: state
    rename = rename_symbols

    def mapped(state):
        return frozenset(rename([fact])[0] for fact in state)

    return mapped


def to_text(forms):
    from ggp.infix import forms_to_infix_lines
    return '\n'.join(forms_to_infix_lines(forms)) + '\n'


def verify(name, text, states, seed=0):
    """Problems (strings) where the rewrite's behaviour differs from the
    original's on `states`. Empty means behaviour is preserved there."""
    from ggp.infix import parse_infix

    from lgref.bench import wellformed

    forms = parse_infix(text)
    new_forms, _prov = rewrite(name, forms, seed)
    mapping = state_map(name, forms)
    rename_move = (lambda m: m) if name != 'scramble' else (
        lambda m: rename_symbols([m])[0])
    original = wellformed.open_game(text)
    rewritten = wellformed.open_game(to_text(new_forms))
    roles = {r: rename_move(r) for r in original.roles}
    problems = []
    if sorted(roles.values()) != sorted(rewritten.roles):
        problems.append('roles differ')
        return problems
    if mapping(frozenset(original.state)) != frozenset(rewritten.state):
        problems.append('initial state differs')
    for state in states:
        wellformed.at(original, state)
        wellformed.at(rewritten, mapping(state))
        if original.is_terminal() != rewritten.is_terminal():
            problems.append('terminal differs')
            continue
        legal = {}
        for role in original.roles:
            mine = sorted(map(rename_move, original.legal_moves(role)),
                          key=repr)
            theirs = sorted(rewritten.legal_moves(roles[role]), key=repr)
            if mine != theirs:
                problems.append('legal moves of {} differ'.format(role))
            legal[role] = original.legal_moves(role)
        if original.is_terminal():
            for role in original.roles:
                a = wellformed.goal_values(original, role)
                b = wellformed.goal_values(rewritten, roles[role])
                if a != b:
                    problems.append('goal of {} differs'.format(role))
            continue
        import itertools
        for joint in itertools.product(*[legal[r] for r in original.roles]):
            moves = dict(zip(original.roles, joint))
            after = wellformed.successor(original, state, moves)
            renamed = {roles[r]: rename_move(m) for r, m in moves.items()}
            other = wellformed.successor(rewritten, mapping(state), renamed)
            if mapping(after) != other:
                problems.append('successor differs')
            # GDL-II: what each role is told must survive the rewrite
            # too (the validation pass found `verify` blind to `sees`).
            for role in original.roles:
                wellformed.at(original, state)
                wellformed.at(rewritten, mapping(state))
                told = frozenset(rename_move(p) for p in
                                 original.percepts(role, moves))
                if told != rewritten.percepts(roles[role], renamed):
                    problems.append('percepts of {} differ'.format(role))
    return problems
