import json
from importlib.resources import files

import pytest

from evoloop.benchmark import benchmark_catalog, load_benchmark, demo_benchmark


def test_core_has_fixed_disjoint_splits_and_stable_hash():
    core = load_benchmark('core')
    assert core.id == 'python-core-v1'
    assert len(core.development) == 16
    assert len(core.holdout) == 8
    assert not {p.id for p in core.development} & {p.id for p in core.holdout}
    assert all(len(p.tests) >= 6 for p in core.development + core.holdout)
    assert core.fingerprint == load_benchmark('core').fingerprint
    assert core.fingerprint == 'e44f2a2ae219226c8126cdb398dad832462e33d6455efafa746e7f08d10de30d'
    core.development[0].tests.clear()
    assert load_benchmark('core').development[0].tests


def test_demo_remains_unchanged_and_unknown_benchmark_rejected():
    assert load_benchmark('demo').fingerprint == demo_benchmark().fingerprint
    with pytest.raises(ValueError):
        load_benchmark('../../arbitrary')


def test_catalog_omits_tests_and_reports_counts():
    catalog = {b['name']: b for b in benchmark_catalog()}
    assert catalog['core']['development'] == 16
    assert catalog['core']['holdout'] == 8
    assert 'tests' not in json.dumps(catalog)


def test_packaged_dataset_has_metadata_and_public_signatures():
    data = json.loads(files('evoloop').joinpath('data/core_v1.json').read_text(encoding='utf-8'))
    assert data['schema_version'] == 1
    assert data['source'] == 'original'
    tasks = data['development'] + data['holdout']
    assert len({p['category'] for p in tasks}) >= 6
    assert len({p['difficulty'] for p in tasks}) >= 2
    assert all(p['function_name'] + '(' in p['description'] for p in tasks)
from copy import deepcopy


@pytest.mark.parametrize('change', ['schema', 'empty-split', 'metadata', 'difficulty', 'empty-tests', 'arguments', 'missing-expected', 'overlap'])
def test_core_schema_rejects_malformed_data(change):
    from evoloop.benchmark import _parse_core
    data = json.loads(files('evoloop').joinpath('data/core_v1.json').read_text(encoding='utf-8'))
    if change == 'schema': data['schema_version'] = True
    elif change == 'empty-split': data['development'] = []
    elif change == 'metadata': data['development'][0]['description'] = ''
    elif change == 'difficulty': data['development'][0]['difficulty'] = 'unknown'
    elif change == 'empty-tests': data['development'][0]['tests'] = []
    elif change == 'arguments': data['development'][0]['tests'][0]['args'] = 'not a list'
    elif change == 'missing-expected': del data['development'][0]['tests'][0]['expected']
    else: data['holdout'][0]['id'] = data['development'][0]['id']
    with pytest.raises(ValueError): _parse_core(data)
