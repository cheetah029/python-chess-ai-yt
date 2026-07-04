"""Prefix-KIF ↔ infix-HRF conversion for GDL.

Classic GDL (GGP-Base, games.ggp.org) is written in KIF prefix
notation. Stanford's current GGP infrastructure (ggp.stanford.edu,
Epilog) uses the infix HRF (human-readable format) syntax. This
module converts between the two:

  EMIT  (prefix forms -> infix text):
    - variables  ?ff            -> FF          (uppercase)
    - compound   (f a ?b)       -> f(a,B)
    - 0-ary      (flag)         -> flag
    - rule       (<= h b1 b2)   -> h :- b1 & b2
    - negation   (not X)        -> ~X
    - (or A B) in a rule body   -> EXPANDED: one emitted rule per
      branch (cartesian product when several ors appear). HRF game
      descriptions conventionally avoid a disjunction operator.
    - (= ?x c) in a rule body   -> resolved by substituting ?x:=c
      throughout the rule and dropping the conjunct.
    Both transformations are semantics-preserving in Datalog.

  READ  (infix text -> prefix forms):
    parse_infix() produces the SAME internal representation the
    KB/Resolver already consume (variables as '?'-lowercase,
    rules as ('<=', head, *body), negation as ('not', X)), so
    GGPGame can load either dialect.

One statement per line; '%' starts a line comment.
"""

from .parser import parse, is_variable


# ===========================================================================
# EMIT: prefix forms -> infix text
# ===========================================================================

def term_to_infix(term):
    """Render one term (atom / variable / compound) as infix text."""
    if isinstance(term, str):
        if is_variable(term):
            return term[1:].upper()
        return term
    if isinstance(term, tuple):
        if len(term) == 0:
            raise ValueError('empty tuple term')
        if len(term) == 1:
            # 0-ary predicate like ('boulder_first_move',) -> bare atom.
            return term_to_infix(term[0])
        head = term[0]
        if not isinstance(head, str) or is_variable(head):
            raise ValueError(f'compound head must be a constant: {term!r}')
        args = ','.join(term_to_infix(a) for a in term[1:])
        return f'{head}({args})'
    raise ValueError(f'unrenderable term: {term!r}')


def _literal_to_infix(lit):
    """Render a body literal — handles the `not` wrapper."""
    if isinstance(lit, tuple) and lit and lit[0] == 'not':
        if len(lit) != 2:
            raise ValueError(f'not takes exactly one argument: {lit!r}')
        return '~' + term_to_infix(lit[1])
    return term_to_infix(lit)


def _substitute(term, subst):
    """Apply a {var: value} substitution recursively."""
    if isinstance(term, str):
        return subst.get(term, term)
    if isinstance(term, tuple):
        return tuple(_substitute(c, subst) for c in term)
    return term


def _expand_rule(head, body):
    """Expand or-branches and resolve =-conjuncts.

    Returns a list of (head, body) pairs containing neither `or`
    nor `=` conjuncts. Raises if or/= appear nested inside other
    literals (we only handle them at the top level of a body,
    which is the only place our GDL fragments use them).
    """
    # Walk conjuncts left to right; recurse on the first special one.
    for i, conjunct in enumerate(body):
        if isinstance(conjunct, tuple) and conjunct:
            op = conjunct[0]
            if op == 'or':
                expanded = []
                for branch in conjunct[1:]:
                    new_body = list(body[:i]) + [branch] + list(body[i + 1:])
                    expanded.extend(_expand_rule(head, new_body))
                return expanded
            if op == '=':
                if len(conjunct) != 3:
                    raise ValueError(f'= takes two arguments: {conjunct!r}')
                a, b = conjunct[1], conjunct[2]
                rest = list(body[:i]) + list(body[i + 1:])
                if is_variable(a) and not is_variable(b):
                    subst = {a: b}
                elif is_variable(b) and not is_variable(a):
                    subst = {b: a}
                elif is_variable(a) and is_variable(b):
                    subst = {a: b}
                else:
                    # Both constants: keep the rule iff they're equal.
                    if a == b:
                        return _expand_rule(head, rest)
                    return []
                new_head = _substitute(head, subst)
                new_rest = [_substitute(c, subst) for c in rest]
                return _expand_rule(new_head, new_rest)
            if op == 'not':
                # Guard: no or/= nested under not in our fragments.
                inner = conjunct[1]
                if isinstance(inner, tuple) and inner and \
                        inner[0] in ('or', '='):
                    raise ValueError(
                        f'or/= nested under not is unsupported: '
                        f'{conjunct!r}')
    return [(head, list(body))]


def forms_to_infix_lines(forms):
    """Convert parsed prefix forms into a list of infix statement
    lines (no comments; one statement per line)."""
    lines = []
    for form in forms:
        if isinstance(form, tuple) and form and form[0] == '<=':
            head = form[1]
            body = list(form[2:])
            for ex_head, ex_body in _expand_rule(head, body):
                head_txt = term_to_infix(ex_head)
                if not ex_body:
                    lines.append(head_txt)
                    continue
                body_txt = ' & '.join(
                    _literal_to_infix(c) for c in ex_body)
                lines.append(f'{head_txt} :- {body_txt}')
        else:
            lines.append(term_to_infix(form))
    return lines


def convert_text(prefix_text, header_comment=None):
    """Convert a full prefix-GDL text to infix-HRF text."""
    forms = parse(prefix_text)
    lines = []
    if header_comment:
        for c_line in header_comment.splitlines():
            lines.append(f'% {c_line}')
        lines.append('')
    lines.extend(forms_to_infix_lines(forms))
    return '\n'.join(lines) + '\n'


# ===========================================================================
# READ: infix text -> prefix forms
# ===========================================================================

def _split_top(text, sep):
    """Split `text` on single-char separator `sep` at paren depth 0."""
    parts = []
    depth = 0
    cur = []
    for ch in text:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append(''.join(cur))
    return parts


def _parse_infix_term(text):
    """Parse one infix term: atom, Variable, or name(arg,...)."""
    text = text.strip()
    if not text:
        raise ValueError('empty term')
    paren = text.find('(')
    if paren == -1:
        # Atom or variable.
        if text[0].isupper():
            return '?' + text.lower()
        return text
    if not text.endswith(')'):
        raise ValueError(f'malformed compound: {text!r}')
    name = text[:paren].strip()
    if not name or name[0].isupper():
        raise ValueError(f'compound head must be a constant: {text!r}')
    inner = text[paren + 1:-1]
    args = [_parse_infix_term(a) for a in _split_top(inner, ',')]
    return tuple([name] + args)


def _parse_infix_literal(text):
    text = text.strip()
    if text.startswith('~'):
        return ('not', _parse_infix_term(text[1:]))
    return _parse_infix_term(text)


def parse_infix(text):
    """Parse infix-HRF GDL text into the internal prefix-form
    representation (list of forms). One statement per line; '%'
    starts a comment."""
    forms = []
    for raw_line in text.splitlines():
        line = raw_line.split('%')[0].strip()
        if not line:
            continue
        if ':-' in line:
            head_txt, body_txt = line.split(':-', 1)
            head = _parse_infix_term(head_txt)
            conjuncts = [
                _parse_infix_literal(c)
                for c in _split_top(body_txt, '&')]
            forms.append(tuple(['<=', head] + conjuncts))
        else:
            forms.append(_parse_infix_term(line))
    return forms
