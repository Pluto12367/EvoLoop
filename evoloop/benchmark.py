from dataclasses import asdict
import hashlib
import json
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
