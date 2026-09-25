"""The designer's INTENDED function for a rule, loaded by explicit path.

`lgref/reference/` is deliberately not a package and cannot be
imported. It holds development annotations written before any
measurement: what the designer thinks each rule is for.

WHY THIS IS NOT CIRCULAR. The annotations never reach rule
identification or function inference -- a test walks the AST of every
module under `identify/` and `functions/` and fails the build if one so
much as names the directory. They are read here, where the question is
the opposite of inference: not "what does this rule look like it does"
but "did it do what it was FOR". A prediction scored against labels it
was allowed to see would be worthless; a design judgement made without
knowing the design intent would be worse.

MOSTLY EMPTY, AND THAT IS THE HONEST STATE. The file is a template the
designer has not finished. One rule carries a stated function. Where
intent is blank, `revise` cannot be assessed at all, and this says so
rather than treating an unfilled placeholder as "no intended function"
-- which would turn every unlabelled rule into an apparent success.
"""

import collections
import os

REFERENCE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'reference', 'seed_labels.yaml')

Intent = collections.namedtuple('Intent', 'rule functions confidence note')


def load(path=REFERENCE):
    """{ablation_variant: Intent} for every rule that declares one."""
    if not os.path.exists(path):
        return {}
    import yaml

    with open(path) as handle:
        document = yaml.safe_load(handle) or {}
    out = {}
    for rule, body in (document.get('rules') or {}).items():
        body = body or {}
        variant = body.get('ablation_variant')
        if not variant:
            continue
        out[variant] = Intent(rule, tuple(body.get('functions') or ()),
                              body.get('confidence', 'unknown'),
                              body.get('note', ''))
    return out


def declared(intents, variant):
    """The intended functions for a variant, or None if none are stated.

    None and () are different answers. None means nobody has said;
    an empty tuple would mean "this rule is for nothing", which no
    designer has claimed about any rule here.
    """
    intent = intents.get(variant)
    if intent is None or not intent.functions:
        return None
    return intent.functions
