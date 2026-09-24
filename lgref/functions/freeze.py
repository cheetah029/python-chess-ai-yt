"""Write Phase 2's predictions down before Phase 3 can see them.

Pre-registration, and the reason the phase is worth running. Phase 3
measures what ablating each rule does. Labels assigned after seeing
those numbers would fit whatever they were; labels written first can be
WRONG, and only then are they evidence.

The artefact therefore records enough to prove it came first: a content
hash over the predictions, the description's own hash, the resolution
and seed that produced the clusters, and the commit. A later claim to
have predicted something can be checked rather than taken on trust.

Nothing here reads the designer's held-out labels in `lgref/reference/`.
`lgref/tests/test_label_isolation.py` fails the build on any import or
string literal that reaches them, because the realistic leak is a
path-based read rather than an import.
"""

import collections
import hashlib
import json
import os
import time

from lgref.functions import characteristics as chars
from lgref.functions.strategic_ontology import BY_NAME, NOT_YET_OPERATIONAL
from lgref.functions.structural import predict_all

SCHEMA_VERSION = 1


def build(nodes, rules, gdl_path, resolution, seed, code=None, skip=()):
    """The frozen record, as a plain dict.

    Predictions are over the project's strategic-function ontology --
    40 functions across eight categories -- with design characteristics
    recorded SEPARATELY, because a characteristic describes how a rule
    is built and a function describes what it does to the decision
    system. An earlier version froze a narrower operational ontology of
    mine that could not express most of the specified functions.
    """
    predictions = predict_all(nodes, rules, skip=skip)
    roles = {c for n in nodes if n.head_predicate == 'role'
             for c in (n.raw[1:] if isinstance(n.raw, tuple) else ())
             if isinstance(c, str)}
    context = {'roles': roles}
    by_id = {r.rule_id: r for r in rules}

    per_rule = collections.OrderedDict()
    for rule_id, got in predictions.items():
        rule = by_id[rule_id]
        own = [n for n in rule.nodes() if n.node_id in rule.clause_ids]
        per_rule[rule_id] = {
            'n_clauses': len(rule.clause_ids),
            'functions': [{
                'function': p.function,
                'category': BY_NAME[p.function].category,
                'confidence': p.confidence,
                'basis': p.basis,
                'evidence_required': BY_NAME[p.function].evidence,
                'metrics': list(BY_NAME[p.function].metrics),
                'falsifiable': p.falsifiable,
            } for p in got],
            'characteristics': dict(chars.detect(own, context)),
        }

    claimed = {f['function'] for entry in per_rule.values()
               for f in entry['functions']}
    body = {
        'schema_version': SCHEMA_VERSION,
        'description': os.path.basename(gdl_path),
        'n_clauses': len(nodes),
        'n_rules_labelled': len(per_rule),
        'resolution': round(float(resolution), 4),
        'seed': seed,
        'ontology_size': len(BY_NAME),
        'rules': per_rule,
        # A function nothing predicts is a claim about the DESCRIPTION,
        # or a gap in the detectors. Either way it belongs in the record
        # rather than being absent from it.
        'unattributed_functions': sorted(set(BY_NAME) - claimed),
        # Predicted but not yet checkable. Phase 4 must not score these
        # as though they could have been falsified.
        'not_yet_operational': sorted(
            f for f in claimed if f in NOT_YET_OPERATIONAL),
    }
    payload = json.dumps(body, sort_keys=True, separators=(',', ':'))
    body['content_sha256'] = hashlib.sha256(payload.encode()).hexdigest()
    body['frozen_at'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    if code:
        body['code'] = code
    return body


def write(record, out_dir, filename='phase2_predictions.json'):
    """Write the record, REFUSING to overwrite an existing one.

    A pre-registration that can be quietly rewritten is not one. If the
    predictions need to change, the old file stays and the new one goes
    beside it under its own name.
    """
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, filename)
    if os.path.exists(path):
        raise FileExistsError(
            '{} already exists. Pre-registered predictions are not '
            'overwritten -- write the new set under a different name so '
            'both remain auditable.'.format(path))
    with open(path, 'w') as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
    return path


def verify(path):
    """Recompute the hash and report whether the file has been edited."""
    with open(path) as handle:
        record = json.load(handle)
    stored = record.pop('content_sha256', None)
    record.pop('frozen_at', None)
    record.pop('code', None)
    payload = json.dumps(record, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(payload.encode()).hexdigest() == stored
