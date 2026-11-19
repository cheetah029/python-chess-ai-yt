"""Metamorphic checks: rewrite a game into an EQUIVALENT one and require
the same answer (#314).

Rule identification claims to read structure, not spelling. That claim
is testable without any ground truth: two descriptions of the same game
that differ only in how they are written must produce the same rules.
Each rewrite here changes the writing and nothing else:

  rotate_action_arguments  `move(knight, FF, FR, TF, TR)` becomes
                           `move(FF, FR, TF, TR, knight)`, everywhere the
                           action appears -- the reviewer's example of an
                           equivalent encoding the method must survive.
  rename_symbols           every predicate and constant the game defines
                           is renamed consistently. GDL keywords and
                           numbers (goal values) are left alone, since
                           they are fixed by the language.

`compare` runs the whole identification on both and reports what moved.
An invariance that does not hold is a FAILURE MODE to report, not a
test to loosen: the tests pin the ones that hold and the documentation
lists the ones that do not.
"""

import hashlib
import os
import tempfile

from lgref.identify.clauses import is_variable, load

#: Symbols the GDL specification fixes. Renaming them would change the
#: language, not the game.
KEYWORDS = frozenset({
    '<=', 'role', 'init', 'true', 'next', 'legal', 'does', 'goal',
    'terminal', 'distinct', 'not', 'or', 'and', 'base', 'input',
    'sees', 'random', 'knows',
})


def forms_of(path):
    """The raw forms of a description, in file order."""
    return [node.raw for node in load(path)]


def _action_names(forms):
    names = set()
    for form in forms:
        head = form[1] if (isinstance(form, tuple) and form
                           and form[0] == '<=') else form
        if isinstance(head, tuple) and len(head) > 2 and head[0] == 'legal':
            action = head[2]
            if isinstance(action, tuple) and action:
                names.add(action[0])
    return names


def rotate_action_arguments(forms, by=1):
    """Every action term with its arguments rotated left by `by`: the
    first argument moves to the end. Applied in `legal` heads and in
    `does` goals alike, so the game is unchanged."""
    names = _action_names(forms)

    def action(term):
        if (isinstance(term, tuple) and len(term) > 2
                and term[0] in names):
            args = list(term[1:])
            shift = by % len(args)
            return (term[0],) + tuple(args[shift:] + args[:shift])
        return term

    def walk(term):
        if not isinstance(term, tuple) or not term:
            return term
        if term[0] == 'legal' and len(term) == 3:
            return ('legal', walk(term[1]), action(term[2]))
        if term[0] == 'does' and len(term) == 3:
            return ('does', walk(term[1]), action(term[2]))
        return tuple(walk(child) for child in term)

    return [walk(form) for form in forms]


def _is_number(symbol):
    return symbol.lstrip('-').isdigit()


def rename_symbols(forms, scheme='opaque'):
    """Every non-keyword, non-numeric symbol renamed consistently.

    `prefix` keeps each name readable and its sort order (`occupied` ->
    `s_occupied`); `opaque` replaces it with a hash, which keeps nothing
    but identity. A method that reads only structure gives the same
    rules under both.
    """
    def new(symbol):
        if scheme == 'prefix':
            return 's_' + symbol
        digest = hashlib.sha256(symbol.encode('utf-8')).hexdigest()[:10]
        return 'x' + digest

    def walk(term):
        if isinstance(term, tuple):
            return tuple(walk(child) for child in term)
        if (isinstance(term, str) and not is_variable(term)
                and term not in KEYWORDS and not _is_number(term)):
            return new(term)
        return term

    return [walk(form) for form in forms]


def write(forms):
    """`forms` as an infix description in a temporary file; the caller
    removes it."""
    from ggp.infix import forms_to_infix_lines

    handle = tempfile.NamedTemporaryFile('w', suffix='.gdl', delete=False)
    try:
        for line in forms_to_infix_lines(forms):
            handle.write(line + '\n')
    finally:
        handle.close()
    return handle.name


def partition(path, resolution='auto', seed=0):
    """The rules identified in `path`, as sets of statement POSITIONS --
    positions rather than ids, because ids carry predicate names and a
    renaming changes them."""
    from lgref.identify.cluster import calibrate_resolution, cluster
    from lgref.identify.graph import ClauseGraph

    nodes = load(path)
    graph = ClauseGraph(nodes)
    if resolution == 'auto':
        resolution = calibrate_resolution(graph, seed=seed)
    rules, _dropped = cluster(graph, resolution=resolution, seed=seed)
    position = {node.node_id: index for index, node in enumerate(nodes)}
    return frozenset(
        frozenset(position[c] for c in rule.all_clause_ids)
        for rule in rules), resolution


def compare(path, rewrite, **kw):
    """Identify `path` and `rewrite(forms)`, and report the difference.

    Returns a dict: `same` (bool), the two resolutions, and the rules
    found by only one side.
    """
    original, res_a = partition(path, **kw)
    rewritten_path = write(rewrite(forms_of(path)))
    try:
        rewritten, res_b = partition(rewritten_path, **kw)
    finally:
        os.unlink(rewritten_path)
    return {
        'same': original == rewritten,
        'resolution': (res_a, res_b),
        'only_original': sorted(sorted(r) for r in original - rewritten),
        'only_rewritten': sorted(sorted(r) for r in rewritten - original),
    }
