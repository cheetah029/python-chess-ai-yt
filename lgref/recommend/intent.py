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

Intent = collections.namedtuple(
    'Intent', 'rule functions statement mapped_by confidence unmapped')

#: A mapping the framework proposed and the designer has not confirmed.
FRAMEWORK = 'framework'


def _document(path=REFERENCE):
    if not os.path.exists(path):
        return {}
    import yaml

    with open(path) as handle:
        return yaml.safe_load(handle) or {}


def _intent(rule, body):
    return Intent(
        rule, tuple(body.get('functions') or ()),
        (body.get('statement') or '').strip(),
        body.get('mapped_by'), body.get('confidence', 'unknown'),
        tuple(entry.get('phrase', '')
              for entry in (body.get('unmapped') or [])))


def load_all(path=REFERENCE):
    """Every annotated rule, whether or not an ablation measures it.

    Most of them are not measured: the sweep plays five variants and
    the designer has described fourteen rules. What those nine say is
    still evidence about the ONTOLOGY even when it is not evidence
    about a rule, and keying the whole file by ablation variant threw
    them away.
    """
    return collections.OrderedDict(
        (rule, _intent(rule, body or {}))
        for rule, body in sorted((_document(path).get('rules') or {}).items()))


def load(path=REFERENCE):
    """{ablation_variant: [Intent]} for every rule that names a variant.

    A LIST per variant, because one ablation can remove several rules.
    `no_knight_redesign` takes out both the invulnerability and the
    jump capture, and keying one rule per variant silently dropped
    whichever came second -- which would have hidden half of what that
    ablation is answerable for.
    """
    out = collections.defaultdict(list)
    for rule, body in sorted((_document(path).get('rules') or {}).items()):
        body = body or {}
        if body.get('ablation_variant'):
            out[body['ablation_variant']].append(_intent(rule, body))
    return dict(out)


def declared(intents, variant):
    """Every intended function for a variant, or None if none are stated.

    None and () are different answers. None means nobody has said; an
    empty tuple would mean "this rule is for nothing", which no
    designer has claimed about any rule here.
    """
    entries = intents.get(variant) or []
    functions = tuple(sorted({f for entry in entries
                              for f in entry.functions}))
    return functions or None


def proposed_by_framework(intents, variant):
    """Was the mapping onto the ontology the framework's own work?

    It usually is: the designer wrote prose and somebody had to turn it
    into function names. A recommendation resting on that translation
    is resting on an interpretation, and the report says so rather than
    presenting it as the designer's word.
    """
    return any(entry.mapped_by == FRAMEWORK
               for entry in intents.get(variant) or [])


def unmapped_phrases(path=REFERENCE):
    """What the designer said that the ontology has no name for.

    Not a failure of the designer. Evidence about the ontology's
    COVERAGE, which is a claim about the vocabulary and not about any
    one rule -- so this reads every annotated rule, including the nine
    no ablation measures. Keying it by variant reported two gaps and
    hid three.
    """
    return collections.OrderedDict(
        (rule, entry.unmapped)
        for rule, entry in load_all(path).items() if entry.unmapped)
