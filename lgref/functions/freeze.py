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

from lgref.functions.infer import infer, predictions
from lgref.functions.ontology import ONTOLOGY

SCHEMA_VERSION = 1


def build(nodes, rules, gdl_path, resolution, seed, code=None):
    """The frozen record, as a plain dict."""
    labels = infer(nodes, rules)

    per_rule = collections.OrderedDict()
    for rule_id, rule_labels in labels.items():
        per_rule[rule_id] = {
            'n_clauses': len(
                [r for r in rules if r.rule_id == rule_id][0].clause_ids),
            'labels': predictions(rule_labels),
        }

    claimed = {name for entry in per_rule.values()
               for name in (l['function'] for l in entry['labels'])}
    unattributed = [f.name for f in ONTOLOGY if f.name not in claimed]

    body = {
        'schema_version': SCHEMA_VERSION,
        'description': os.path.basename(gdl_path),
        'n_clauses': len(nodes),
        'n_rules_labelled': len(per_rule),
        'resolution': round(float(resolution), 4),
        'seed': seed,
        'ontology': [f._asdict() for f in ONTOLOGY],
        'rules': per_rule,
        # Stated rather than silently absent: a function no cluster owns
        # is a claim about the DESCRIPTION -- that the job is done by
        # shared machinery rather than by any one rule -- and Phase 4
        # should be able to see it was noticed.
        'unattributed_functions': unattributed,
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
