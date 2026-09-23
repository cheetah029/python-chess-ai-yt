"""Config loading — one file plus a seed reproduces any run.

Project rule: no hardcoded paths, no notebook-only logic. Every
experiment is described by a YAML file in lgref/config/, and the
(config, seed) pair is what the manifest records and the config hash
covers.

Configs support single-level `extends` so the sweep's shared settings
live in one place and a variant file states only what differs. Deeper
inheritance chains are refused deliberately: three-level config
inheritance makes "what did this run actually use?" a research question,
which is the opposite of the point.

The resolved mapping -- not the file text -- is what gets hashed, so
comments and key order cannot change a run's identity.
"""

import os

from lgref.core.deps import require
yaml = require('yaml', 'reading experiment configs', 'PyYAML')


CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'config')


class ConfigError(ValueError):
    pass


def _deep_merge(base, override):
    """Recursive dict merge; `override` wins at every leaf."""
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path, _depth=0):
    """Load a YAML config, resolving one level of `extends`."""
    if not os.path.isabs(path) and not os.path.exists(path):
        candidate = os.path.join(CONFIG_DIR, path)
        if os.path.exists(candidate):
            path = candidate
    if not os.path.exists(path):
        raise ConfigError(f'config not found: {path}')

    with open(path) as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ConfigError(f'config must be a mapping: {path}')

    parent = data.pop('extends', None)
    if parent is not None:
        if _depth >= 1:
            raise ConfigError(
                f'{path}: `extends` may not be chained more than one '
                f'level -- deeper inheritance makes a run config '
                f'unreadable at a glance')
        base_path = parent
        if not os.path.isabs(base_path):
            local = os.path.join(os.path.dirname(path), parent)
            base_path = local if os.path.exists(local) else parent
        data = _deep_merge(load_config(base_path, _depth + 1), data)

    data['_config_path'] = os.path.relpath(path, os.getcwd())
    return data


def require(config, *keys):
    """Fetch required keys, failing with all missing names at once."""
    missing = [k for k in keys if k not in config]
    if missing:
        raise ConfigError(
            f'config {config.get("_config_path", "?")} is missing '
            f'required key(s): {", ".join(missing)}')
    return tuple(config[k] for k in keys)
