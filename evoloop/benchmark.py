from dataclasses import asdict
import hashlib
import json
from importlib.resources import files
from .models import Problem, TestCase


class Benchmark:
    def __init__(self, id: str, development: list[Problem], holdout: list[Problem]):
        tasks = [*development, *holdout]
        if not id or not development or not holdout or any(not p.tests for p in tasks):
            raise ValueError('Benchmark requires nonempty named splits and tests')
        if len({p.id for p in tasks}) != len(tasks):
            raise ValueError('Problem IDs must be unique across splits')
        self.id = id
        self._snapshot = json.dumps({'development': [asdict(p) for p in development],
                                     'holdout': [asdict(p) for p in holdout]}, sort_keys=True, allow_nan=False)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self._snapshot.encode()).hexdigest()

    def split_hash(self, name: str) -> str:
        data = json.loads(self._snapshot)[name]
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def _tasks(self, split: str) -> list[Problem]:
        return [Problem(p['id'], p['description'], p['function_name'],
                        [TestCase(t['args'], t['expected']) for t in p['tests']])
                for p in json.loads(self._snapshot)[split]]

    @property
    def development(self) -> list[Problem]:
        return self._tasks('development')

    @property
    def holdout(self) -> list[Problem]:
        return self._tasks('holdout')


def demo_benchmark() -> Benchmark:
    return Benchmark('synthetic-python-v1', [
        Problem('absolute', 'Return absolute values of a list of integers, preserving order.', 'absolute_values',
                [TestCase([[-2, 0, 3]], [2, 0, 3]), TestCase([[]], [])]),
        Problem('unique', 'Remove duplicate integers preserving their first occurrence order.', 'unique_values',
                [TestCase([[2, 1, 2]], [2, 1]), TestCase([[]], [])]),
    ], [
        Problem('squares', 'Return the sum of squares of all integers in a list, including an empty list.', 'sum_squares',
                [TestCase([[-2, 3]], 13), TestCase([[]], 0)]),
        Problem('evens', 'Return even integers in original order, including negative integers.', 'even_values',
                [TestCase([[-2, 1, 0, 4]], [-2, 0, 4]), TestCase([[]], [])]),
    ])


def load_benchmark(name: str) -> Benchmark:
    """Load a versioned, packaged suite; callers cannot supply file paths."""
    if name == 'demo':
        return demo_benchmark()
    if name != 'core':
        raise ValueError('Unknown benchmark')
    data = json.loads(files('evoloop').joinpath('data/core_v1.json').read_text(encoding='utf-8'))
    return _parse_core(data)


def _parse_core(data: object) -> Benchmark:
    if (not isinstance(data, dict) or type(data.get('schema_version')) is not int
            or data['schema_version'] != 1 or data.get('id') != 'python-core-v1'):
        raise ValueError('Unsupported core benchmark schema')
    splits: list[list[Problem]] = []
    for split in ('development', 'holdout'):
        entries = data.get(split)
        if not isinstance(entries, list) or not entries:
            raise ValueError('Invalid benchmark split')
        problems = []
        for item in entries:
            if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not item[k].strip()
                    for k in ('id', 'description', 'function_name', 'category', 'difficulty')):
                raise ValueError('Invalid problem metadata')
            if item['difficulty'] not in ('easy', 'medium', 'hard'):
                raise ValueError('Invalid difficulty')
            cases = item.get('tests')
            if not isinstance(cases, list) or not cases:
                raise ValueError('A problem needs tests')
            if any(not isinstance(t, dict) or set(t) != {'args', 'expected'} or not isinstance(t['args'], list)
                   for t in cases):
                raise ValueError('Invalid test case')
            problems.append(Problem(item['id'], item['description'], item['function_name'],
                                    [TestCase(t['args'], t['expected']) for t in cases]))
        splits.append(problems)
    return Benchmark(data['id'], *splits)


def benchmark_catalog() -> list[dict[str, str | int]]:
    return [{'name': name, 'id': suite.id, 'development': len(suite.development),
             'holdout': len(suite.holdout), 'sha256': suite.fingerprint}
            for name in ('demo', 'core') for suite in (load_benchmark(name),)]
