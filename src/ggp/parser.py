"""GDL S-expression parser.

Inputs are GDL-I text (Knowledge Interchange Format dialect used
by Stanford GGP). The parser produces Python data structures:

  - Atoms are strings ('white', 'role', 'queen', ...).
  - Variables are strings starting with '?' ('?x', '?player', ...).
  - Lists are Python tuples of mixed atoms and nested tuples.
  - Comments start with ';' and run to end-of-line.

A whole file parses into a list of top-level forms (each form is a
fact or a rule). Rules are forms whose first element is '<='.
"""


def strip_comments(text):
    """Remove ';' line comments. Whitespace + line structure
    preserved so error messages remain accurate."""
    out = []
    for line in text.splitlines(keepends=True):
        # Newline at end (if any) must survive.
        comment_idx = line.find(';')
        if comment_idx >= 0:
            stripped = line[:comment_idx]
            # Preserve the trailing newline if it was on the line.
            if line.endswith('\n'):
                stripped += '\n'
            out.append(stripped)
        else:
            out.append(line)
    return ''.join(out)


def tokenize(text):
    """Tokenize stripped GDL text into '(', ')', and atom strings.
    Atoms are runs of non-whitespace non-paren characters."""
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch in '()':
            tokens.append(ch)
            i += 1
            continue
        j = i
        while j < n and not text[j].isspace() and text[j] not in '()':
            j += 1
        tokens.append(text[i:j])
        i = j
    return tokens


def parse(text):
    """Parse GDL text into a list of top-level forms. Raises
    ValueError on unbalanced parens / unexpected close / etc.
    """
    tokens = tokenize(strip_comments(text))
    pos = [0]

    def parse_one():
        if pos[0] >= len(tokens):
            raise ValueError('unexpected EOF')
        tok = tokens[pos[0]]
        if tok == '(':
            pos[0] += 1
            items = []
            while pos[0] < len(tokens) and tokens[pos[0]] != ')':
                items.append(parse_one())
            if pos[0] >= len(tokens):
                raise ValueError('unbalanced paren — missing close')
            pos[0] += 1  # skip )
            return tuple(items)
        if tok == ')':
            raise ValueError('unexpected )')
        pos[0] += 1
        return tok

    forms = []
    while pos[0] < len(tokens):
        forms.append(parse_one())
    return forms


def is_variable(atom):
    """Return True if `atom` is a GDL variable (starts with '?').

    Empty strings are NOT variables.
    """
    return isinstance(atom, str) and len(atom) > 0 and atom[0] == '?'
